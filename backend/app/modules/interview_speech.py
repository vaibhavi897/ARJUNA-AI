"""Communication analysis for interview answers.

Everything here is measured from what the candidate actually said or typed:
  * filler words and hedging, counted from the transcript;
  * vocabulary range, from the words used;
  * clarity of structure, from sentence shape and reasoning markers;
  * delivery (pace, pauses, vocal steadiness), ONLY for answers dictated by voice, from browser audio measurements.

Nothing is invented. When voice was not used, the delivery section says so instead of guessing. Scores are
transparent heuristics shown with the numbers behind them, not hidden model judgements.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
SENT = re.compile(r"(?<=[.!?])\s+")

FILLER_SINGLE = {"um", "uh", "umm", "uhh", "er", "erm", "ah", "hmm", "like", "basically", "actually", "literally", "honestly", "right", "okay", "so"}
FILLER_PHRASES = ["you know", "i mean", "kind of", "sort of", "you see", "or something", "and stuff", "to be honest"]
# "like" and "so" are only fillers some of the time; they are counted at half weight below to avoid over-penalising.
SOFT_FILLERS = {"like", "so", "right", "okay", "actually"}
HEDGES = ["maybe", "i think", "i guess", "probably", "perhaps", "not sure", "i suppose", "might be", "kind of", "sort of", "i feel like", "hopefully"]
STRUCTURE = ["first", "second", "third", "finally", "because", "therefore", "as a result", "for example", "for instance", "in conclusion", "overall",
             "the reason", "which led", "so that", "this meant", "specifically", "in summary", "however", "on the other hand"]
STOP = set("the a an and or but if of to in on for with at by from as is are was were be been it its this that these those i you he she we they my our your their me us them do did does done have has had not no so very just can could would should will shall may might about into over than then there here also more most some any".split())
COMMON = set("people thing things really good great nice work working team make made get got want need use used time way lot lots many much well".split())


def _words(text: str) -> list[str]:
    return [w.lower() for w in WORD.findall(text or "")]


def _count_phrase(text: str, phrase: str) -> int:
    return len(re.findall(r"\b" + re.escape(phrase) + r"\b", text))


def fillers(text: str) -> tuple[Counter, float]:
    """Return (counter of fillers, weighted total)."""
    low = (text or "").lower()
    c: Counter = Counter()
    for p in FILLER_PHRASES:
        n = _count_phrase(low, p)
        if n:
            c[p] += n
    for w in _words(low):
        if w in FILLER_SINGLE:
            c[w] += 1
    # "so" opening a sentence is the common filler; mid-sentence "so" is usually a real connective
    weighted = sum(n * (0.5 if k in SOFT_FILLERS else 1.0) for k, n in c.items())
    return c, weighted


def _mattr(words: list[str], window: int = 50) -> float:
    """Moving-average type-token ratio: lexical variety that does not depend on answer length."""
    if len(words) < 8:
        return len(set(words)) / max(1, len(words))
    if len(words) <= window:
        return len(set(words)) / len(words)
    vals = [len(set(words[i:i + window])) / window for i in range(0, len(words) - window + 1, max(1, window // 5))]
    return sum(vals) / len(vals)


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> int:
    return int(round(max(lo, min(hi, x))))


def _band(score: int) -> str:
    return "Excellent" if score >= 80 else "Good" if score >= 65 else "Fair" if score >= 50 else "Needs work"


def vocabulary(text: str) -> dict[str, Any]:
    ws = _words(text)
    n = len(ws)
    if n < 20:
        return {"available": False, "message": "Too little text to judge vocabulary."}
    content = [w for w in ws if w not in STOP]
    variety = _mattr(ws)
    avg_len = sum(len(w) for w in content) / max(1, len(content))
    advanced = [w for w in set(content) if len(w) >= 9 and w not in COMMON and w not in FILLER_SINGLE and not w.endswith("ly")]
    counts = Counter(content)
    overused = [(w, k) for w, k in counts.most_common(8) if k >= 4 and len(w) > 3 and w not in COMMON][:4]
    # variety carries most of the weight; precise (longer, less common) words add a little
    score = _clamp(35 + (variety - 0.55) * 140 + (avg_len - 5.0) * 9 + min(len(advanced), 12) * 1.2 - sum(k - 3 for _, k in overused) * 1.5)
    notes = []
    if variety < 0.62:
        notes.append("You repeat the same words fairly often. Vary your phrasing.")
    if avg_len < 5.2:
        notes.append("Your word choice is plain. Add precise, role-specific terms where they fit.")
    if overused:
        notes.append("Overused: " + ", ".join(f"\"{w}\" ({k}x)" for w, k in overused) + ".")
    if not notes:
        notes.append("Good range of words with enough precise terms.")
    return {"available": True, "score": score, "band": _band(score), "unique_ratio": round(variety, 2), "avg_word_length": round(avg_len, 1),
            "advanced_words": sorted(advanced)[:10], "overused": [{"word": w, "count": k} for w, k in overused], "notes": notes}


def clarity(text: str) -> dict[str, Any]:
    ws = _words(text)
    n = len(ws)
    sents = [s for s in SENT.split((text or "").strip()) if len(_words(s)) >= 2]
    if n < 20 or not sents:
        return {"available": False, "message": "Too little text to judge clarity."}
    lens = [len(_words(s)) for s in sents]
    avg = sum(lens) / len(lens)
    longest = max(lens)
    low = (text or "").lower()
    markers = sum(_count_phrase(low, m) for m in STRUCTURE)
    hedges = sum(_count_phrase(low, h) for h in HEDGES)
    has_numbers = bool(re.search(r"\d", text or ""))
    # sweet spot 12-22 words per sentence; penalise run-ons and one-word fragments
    length_pts = 30 - abs(avg - 17) * 1.6
    run_on = sum(1 for l in lens if l > 40)
    score = _clamp(30 + length_pts + min(markers, 8) * 4 + (6 if has_numbers else 0) - hedges * 2.5 - run_on * 8)
    notes = []
    if avg > 26 or run_on:
        notes.append("Some sentences run very long. Break them up so each carries one idea.")
    elif avg < 8:
        notes.append("Sentences are very short. Connect ideas with reasons (because, so, therefore).")
    if markers < max(2, n // 80):
        notes.append("Add signposts like first, because, for example and as a result so your reasoning is easy to follow.")
    if hedges > max(2, n // 60):
        notes.append(f"You hedged {hedges} times (maybe, I think, probably). State conclusions more directly where you are sure.")
    if not has_numbers:
        notes.append("Back claims with a number or concrete result where you can.")
    if not notes:
        notes.append("Clear structure: well-sized sentences with visible reasoning.")
    return {"available": True, "score": score, "band": _band(score), "avg_sentence_words": round(avg, 1), "longest_sentence_words": longest, "structure_markers": markers, "hedges": hedges, "notes": notes}


def filler_report(text: str) -> dict[str, Any]:
    ws = _words(text)
    n = len(ws)
    if n < 20:
        return {"available": False, "message": "Too little text to count fillers."}
    c, weighted = fillers(text)
    per100 = round(100 * weighted / n, 1)
    score = _clamp(100 - per100 * 14)
    top = [{"word": k, "count": v} for k, v in c.most_common(6)]
    if per100 <= 1.5:
        note = "Very few filler words. Your answers sound controlled."
    elif per100 <= 4:
        note = "A moderate number of fillers. Pause silently instead of saying them."
    else:
        note = "Frequent fillers. Practise pausing for a breath instead of filling the gap."
    return {"available": True, "score": score, "band": _band(score), "total": int(round(weighted)), "per_100_words": per100, "top": top, "note": note}


def delivery(voiced: list[dict[str, Any]]) -> dict[str, Any]:
    """Pace, pauses and vocal steadiness, only from answers the candidate actually spoke."""
    usable = [v for v in voiced if (v.get("spoken_seconds") or 0) >= 8 and (v.get("words") or 0) >= 15]
    if not usable:
        return {"available": False, "message": "No voice answers were recorded. Use \"Answer by voice\" to get pace, pause and vocal-confidence feedback."}
    secs = sum(v["spoken_seconds"] for v in usable)
    total_secs = sum(max(v.get("total_seconds") or 0, v["spoken_seconds"]) for v in usable)
    words = sum(v["words"] for v in usable)
    wpm = round(words / (total_secs / 60)) if total_secs else 0
    pauses = sum(int(v.get("long_pauses") or 0) for v in usable)
    pauses_per_min = round(pauses / (total_secs / 60), 1) if total_secs else 0
    cvs = [v["volume_cv"] for v in usable if isinstance(v.get("volume_cv"), (int, float))]
    levels = [v["volume_mean"] for v in usable if isinstance(v.get("volume_mean"), (int, float))]
    steadiness = None
    if cvs:
        cv = sum(cvs) / len(cvs)
        steadiness = _clamp(100 - max(0.0, cv - 0.35) * 160)
    loud = (sum(levels) / len(levels)) if levels else None
    energy = _clamp(((loud or 0) - 0.015) / 0.06 * 100) if loud is not None else None
    pace_pts = _clamp(100 - abs(wpm - 145) * 1.1)
    pause_pts = _clamp(100 - max(0.0, pauses_per_min - 3) * 12)
    parts = [pace_pts * 0.35, pause_pts * 0.25]
    weights = 0.6
    if steadiness is not None:
        parts.append(steadiness * 0.25); weights += 0.25
    if energy is not None:
        parts.append(energy * 0.15); weights += 0.15
    confidence = _clamp(sum(parts) / weights)
    notes = []
    if wpm > 175:
        notes.append(f"You spoke fast ({wpm} words per minute). Slow down so key points land; aim for about 130 to 160.")
    elif wpm < 105:
        notes.append(f"Your pace was slow ({wpm} words per minute), which can sound unsure. Aim for about 130 to 160.")
    else:
        notes.append(f"Good pace ({wpm} words per minute).")
    if pauses_per_min > 5:
        notes.append("Many long pauses. Plan your first sentence before you start so you do not stall.")
    if steadiness is not None and steadiness < 55:
        notes.append("Your volume swung a lot. Keep a steady, projected voice, especially at the ends of sentences.")
    if energy is not None and energy < 35:
        notes.append("You spoke quietly. Sit closer to the microphone and project more.")
    return {"available": True, "confidence_score": confidence, "confidence_band": _band(confidence), "words_per_minute": wpm, "long_pauses_per_minute": pauses_per_min,
            "volume_steadiness": steadiness, "voice_energy": energy, "spoken_answers": len(usable), "spoken_seconds": int(secs), "notes": notes,
            "caveat": "Measured from your microphone during dictation. These are indicators of delivery, not a judgement of your character."}


def analyse(attempted: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the communication section of the report from the attempted student answers."""
    texts = [a.get("text", "") for a in attempted if a.get("text", "").strip()]
    full = "\n".join(texts)
    voiced = [a["voice"] for a in attempted if isinstance(a.get("voice"), dict) and a["voice"].get("spoken")]
    total_words = len(_words(full))
    per_answer = []
    for i, a in enumerate(attempted):
        t = a.get("text", "")
        c, w = fillers(t)
        n = len(_words(t))
        per_answer.append({"index": i + 1, "question": a.get("question"), "words": n, "fillers": int(round(w)), "spoken": bool(isinstance(a.get("voice"), dict) and a["voice"].get("spoken"))})
    return {
        "words_total": total_words,
        "avg_answer_words": round(total_words / max(1, len(texts))),
        "vocabulary": vocabulary(full),
        "clarity": clarity(full),
        "fillers": filler_report(full),
        "delivery": delivery(voiced),
        "per_answer": per_answer,
        "caveat": "Voice dictation in the browser often drops filler sounds like \"um\", so filler counts for spoken answers can be lower than what you really said.",
    }
