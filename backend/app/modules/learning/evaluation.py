"""Answer evaluation.

* Objective types (mcq, true_false, output_prediction, code_tracing) are scored
  deterministically here, never by an LLM.
* Coding / debugging answers run against test cases in a restricted subprocess.
* Subjective answers are graded by Gemini against a structured rubric; the
  score is recomputed from per-criterion marks, so the model cannot invent a total.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Any

from pydantic import BaseModel, Field

from app.core.logging_config import get_logger
from app.modules.careerverse import gemini_service
from app.modules.learning.ai import Lenient as ai_Lenient

logger = get_logger(__name__)
OBJECTIVE = {"mcq", "true_false", "output_prediction", "code_tracing"}
CODING = {"coding", "debugging"}
SUBJECTIVE = {"short_answer", "scenario"}


def normalise(text: Any) -> str:
    s = str(text if text is not None else "").strip().lower()
    s = re.sub(r"^['\"`]+|['\"`]+$", "", s)
    return re.sub(r"\s+", " ", s)


def score_objective(qtype: str, answer_key: dict[str, Any], response: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """Return (fraction 0..1, feedback). Pure and deterministic."""
    if qtype == "mcq":
        correct = answer_key.get("index")
        given = response.get("choice")
        ok = given is not None and correct is not None and int(given) == int(correct)
        return (1.0 if ok else 0.0), {"correct_answer_index": correct}
    if qtype == "true_false":
        ok = response.get("value") is not None and bool(response.get("value")) == bool(answer_key.get("value"))
        return (1.0 if ok else 0.0), {"correct_value": bool(answer_key.get("value"))}
    if qtype in ("output_prediction", "code_tracing"):
        accepted = {normalise(answer_key.get("answer"))} | {normalise(a) for a in answer_key.get("alternatives", [])}
        ok = normalise(response.get("text")) in accepted and normalise(response.get("text")) != ""
        return (1.0 if ok else 0.0), {"correct_answer": answer_key.get("answer")}
    raise ValueError(f"not an objective type: {qtype}")


# ----------------------------------------------------------------------------- sandbox
_RUNNER = r'''
import sys, json, builtins
ALLOWED = {"math","collections","itertools","functools","heapq","re","json","string","bisect","statistics","typing","dataclasses","operator","copy","decimal","fractions"}
_pre = {m: __import__(m) for m in ALLOWED}
_real_import = builtins.__import__
def _imp(name, globals=None, locals=None, fromlist=(), level=0):
    if name.split(".")[0] not in ALLOWED:
        raise ImportError("import of '%s' is not allowed in the sandbox" % name)
    return _real_import(name, globals, locals, fromlist, level)
DENY = ("open","socket","subprocess","os.system","os.exec","os.spawn","os.fork","os.remove","os.rename","shutil","ctypes","urllib","http","ftplib","smtplib","pty","signal")
def _hook(event, args):
    if event == "exec" or event == "compile":
        return
    if any(event == d or event.startswith(d + ".") or event.startswith(d) for d in DENY):
        raise RuntimeError("operation '%s' is not allowed in the sandbox" % event)
payload = json.loads(sys.stdin.read())
safe = {k: getattr(builtins, k) for k in dir(builtins) if k not in ("open","exec","eval","compile","input","breakpoint","help","exit","quit","__import__","memoryview","globals","locals","vars")}
safe["__import__"] = _imp
ns = {"__builtins__": safe, "__name__": "__sandbox__"}
sys.addaudithook(_hook)
results = []
try:
    exec(compile(payload["code"], "<answer>", "exec"), ns)
    fn = ns.get(payload["entry"])
    if not callable(fn):
        raise NameError("function '%s' is not defined" % payload["entry"])
    for case in payload["cases"]:
        try:
            out = fn(*case.get("args", []))
            results.append({"ok": json.dumps(out, sort_keys=True, default=str) == json.dumps(case["expected"], sort_keys=True, default=str), "got": repr(out)[:200]})
        except Exception as e:
            results.append({"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:160])})
except BaseException as e:
    print(json.dumps({"fatal": "%s: %s" % (type(e).__name__, str(e)[:200])}))
    sys.exit(0)
print(json.dumps({"results": results}))
'''


def run_sandboxed(code: str, entry: str, cases: list[dict[str, Any]], timeout: float = 6.0) -> dict[str, Any]:
    """Run learner code against test cases in a separate, restricted Python process.

    Defence in depth: isolated interpreter (-I), empty environment and scratch
    working directory, import allow-list, stripped builtins, audit-hook deny list
    (files, sockets, subprocesses), hard timeout and output cap.
    NOTE: this is NOT a hostile-multi-tenant sandbox. For production exposure, run
    this inside a container/gVisor with CPU, memory and network limits.
    """
    if len(code) > 20_000:
        return {"fatal": "Code is too long."}
    payload = json.dumps({"code": code, "entry": entry, "cases": cases})
    with tempfile.TemporaryDirectory() as tmp:
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-c", _RUNNER], input=payload, capture_output=True, text=True, timeout=timeout,
                cwd=tmp, env={"PYTHONIOENCODING": "utf-8", "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")},
            )
        except subprocess.TimeoutExpired:
            return {"fatal": f"Time limit exceeded ({timeout:.0f}s). Check for infinite loops."}
    out = (proc.stdout or "").strip().splitlines()
    if not out:
        return {"fatal": (proc.stderr or "No output")[-300:]}
    try:
        return json.loads(out[-1][:20_000])
    except json.JSONDecodeError:
        return {"fatal": "The program printed unexpected output."}


def score_coding(answer_key: dict[str, Any], test_cases: list[dict[str, Any]], code: str) -> tuple[float, dict[str, Any]]:
    entry = answer_key.get("entry_function", "solution")
    run = run_sandboxed(code or "", entry, test_cases)
    if "fatal" in run:
        return 0.0, {"error": run["fatal"], "passed": 0, "total": len(test_cases)}
    results = run["results"]
    passed = sum(1 for r in results if r.get("ok"))
    return (passed / len(test_cases) if test_cases else 0.0), {"passed": passed, "total": len(test_cases), "cases": results}


# ----------------------------------------------------------------------------- subjective
class CriterionMark(BaseModel):
    criterion: str
    marks: float = Field(ge=0)
    comment: str = ""


class RubricResult(ai_Lenient):
    marks: list[CriterionMark]
    overall_feedback: str = ""


def score_subjective(prompt: str, rubric: list[dict[str, Any]], answer: str) -> tuple[float, dict[str, Any], str]:
    """Grade against the rubric with Gemini. Returns (fraction, feedback, evaluator)."""
    if not (answer or "").strip():
        return 0.0, {"overall_feedback": "No answer submitted.", "marks": []}, "deterministic"
    max_total = sum(float(c.get("marks", 1)) for c in rubric) or 1.0
    if not gemini_service.is_enabled():
        return 0.0, {"overall_feedback": "AI grading is unavailable right now. Your answer was saved; retry grading later.", "marks": [], "ungraded": True}, "unavailable"
    ask = (
        "You are a strict but fair examiner. Grade the student's answer ONLY against the rubric. "
        "Return JSON {\"marks\": [{\"criterion\": str, \"marks\": number, \"comment\": str}], \"overall_feedback\": str}. "
        "One entry per rubric criterion, marks between 0 and that criterion's maximum. Do not add criteria. "
        f"\nQUESTION: {prompt}\nRUBRIC: {json.dumps(rubric)}\nSTUDENT ANSWER: {answer[:4000]}"
    )
    try:
        data = gemini_service.generate_json(ask, temperature=0.1, max_tokens=900, schema=RubricResult)
    except gemini_service.GeminiUnavailable as exc:
        logger.warning("rubric grading failed: %s", exc)
        return 0.0, {"overall_feedback": "AI grading failed. Your answer was saved; retry grading later.", "marks": [], "ungraded": True}, "unavailable"
    caps = {c["criterion"]: float(c.get("marks", 1)) for c in rubric}
    clean = []
    for m in data["marks"]:
        cap = caps.get(m["criterion"])
        if cap is None:
            continue
        clean.append({"criterion": m["criterion"], "marks": min(float(m["marks"]), cap), "max": cap, "comment": m.get("comment", "")})
    got = sum(c["marks"] for c in clean)
    return min(1.0, got / max_total), {"marks": clean, "overall_feedback": data.get("overall_feedback", "")}, "gemini"
