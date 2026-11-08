/** Quizzes & Assessments: generate, take, review. Scoring happens on the server. */
import QuizReview, { type ReviewItem } from "../../components/learning/QuizReview";
import CodeEditor from "../../components/CodeEditor";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AlertCircle, CheckCircle2, ChevronLeft, ChevronRight, Clock, Loader2, RefreshCw, Send, Sparkles, XCircle } from "lucide-react";
import { Badge, Button, Card, EmptyState, ErrorState, InlineNote, Modal } from "../../components/ui";
import { CountUp } from "../../components/fx";
import { Skeleton, hm, useLoad } from "../../components/learning/shared";
import { lh, type Question, type Quiz, type Report } from "../../lib/learning";
import { useToast } from "../../lib/auth";
import { cn } from "../../lib/utils";

const TYPES: [string, string][] = [["mcq", "Multiple choice"], ["true_false", "True / false"], ["output_prediction", "Output prediction"], ["code_tracing", "Code tracing"], ["short_answer", "Short answer"], ["scenario", "Scenario-based"], ["coding", "Coding (sandboxed)"], ["debugging", "Debugging"]];
const SCOPES: [string, string, string][] = [["topic", "A topic", "Focused on one concept"], ["subject", "A subject", "Broad coverage"], ["week", "A week of my plan", "Everything studied that week"], ["roadmap", "My whole roadmap", "Cumulative review"], ["revision", "Revision", "Aimed at topics you struggled with"]];
const DIFF_STYLE: Record<string, string> = { easy: "bg-emerald-100 text-emerald-800", medium: "bg-amber-100 text-amber-800", hard: "bg-rose-100 text-rose-800" };
const mmss = (s: number) => `${Math.floor(Math.max(0, s) / 60)}:${String(Math.max(0, s) % 60).padStart(2, "0")}`;

// ------------------------------------------------------------------ config
function Config({ onStart }: { onStart: (q: Quiz) => void }) {
  const [params] = useSearchParams();
  const [topic, setTopic] = useState(params.get("topic") ?? "");
  const [scope, setScope] = useState(params.get("scope") ?? "topic");
  const [week, setWeek] = useState(1);
  const [count, setCount] = useState(8);
  const [difficulty, setDifficulty] = useState("mixed");
  const [level, setLevel] = useState("intermediate");
  const [limit, setLimit] = useState("");
  const [types, setTypes] = useState<string[]>(["mcq", "true_false", "short_answer"]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const needsTopic = scope === "topic" || scope === "subject";
  const ok = (!needsTopic || topic.trim().length >= 2) && types.length > 0;

  async function go() {
    setBusy(true); setError(null);
    try { onStart(await lh.createQuiz({ topic, scope, count, difficulty, level, week: scope === "week" ? week : null, time_limit_minutes: limit ? Number(limit) : null, types })); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  if (busy) return <div role="status" className="card grid place-items-center gap-3 p-16 text-center"><Loader2 className="animate-spin text-brand-600" size={34} /><p className="text-lg font-extrabold text-forest-900">Gemini is writing {count} fresh questions…</p><p className="text-xs text-ink-400">Coding questions are checked against their own test cases before you see them. This can take up to a minute.</p></div>;
  return (
    <Card className="space-y-6 p-6 sm:p-8">
      <div><h2 className="text-xl font-extrabold text-forest-900">Build an assessment</h2><p className="text-sm text-ink-500">Every quiz is newly generated. Objective answers are scored by the server, coding runs against test cases, and written answers are graded against a rubric.</p></div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5" role="radiogroup" aria-label="Scope">
        {SCOPES.map(([k, t, d]) => <button key={k} role="radio" aria-checked={scope === k} onClick={() => setScope(k)} className={cn("rounded-2xl border p-3 text-left transition", scope === k ? "border-forest-800 bg-forest-800 text-white shadow-md" : "border-line bg-white hover:border-brand-400")}><p className="text-sm font-extrabold">{t}</p><p className={cn("text-[11px]", scope === k ? "text-white/70" : "text-ink-400")}>{d}</p></button>)}
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-4">
          {needsTopic ? <label className="block text-sm font-bold">{scope === "subject" ? "Subject" : "Topic"}<input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. SQL joins, Python decorators, DCF valuation" className="input-base mt-1.5" maxLength={200} /></label> : null}
          {scope === "week" ? <label className="block text-sm font-bold">Week number<input type="number" min={1} max={60} value={week} onChange={(e) => setWeek(Number(e.target.value))} className="input-base mt-1.5 w-28" /></label> : null}
          <label className="block text-sm font-bold">Number of questions: <span className="text-brand-700">{count}</span><input type="range" min={3} max={30} value={count} onChange={(e) => setCount(Number(e.target.value))} className="mt-2 w-full accent-brand-600" aria-label="Question count" /></label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm font-bold">Difficulty<select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} className="input-base mt-1.5">{["mixed", "easy", "medium", "hard"].map((d) => <option key={d} value={d} className="capitalize">{d}</option>)}</select></label>
            <label className="block text-sm font-bold">Your level<select value={level} onChange={(e) => setLevel(e.target.value)} className="input-base mt-1.5">{["beginner", "intermediate", "advanced"].map((d) => <option key={d}>{d}</option>)}</select></label>
          </div>
          <label className="block text-sm font-bold">Time limit (minutes) <span className="font-normal text-ink-400">optional</span><input type="number" min={1} max={240} value={limit} onChange={(e) => setLimit(e.target.value)} placeholder="No limit" className="input-base mt-1.5 w-36" /></label>
        </div>
        <div><p className="text-sm font-bold">Question types</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">{TYPES.map(([k, l]) => <label key={k} className={cn("flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2.5 text-sm font-semibold transition", types.includes(k) ? "border-brand-500 bg-brand-50" : "border-line hover:border-brand-300")}><input type="checkbox" checked={types.includes(k)} onChange={() => setTypes((t) => (t.includes(k) ? t.filter((x) => x !== k) : [...t, k]))} className="accent-brand-600" />{l}</label>)}</div>
          <p className="mt-2 text-xs text-ink-400">Coding and debugging questions use Python and run in a restricted sandbox.</p></div>
      </div>
      {error ? <ErrorState message={error} onRetry={go} /> : null}
      <div className="flex justify-end"><Button size="lg" disabled={!ok} onClick={go} icon={<Sparkles size={18} />}>Generate quiz</Button></div>
    </Card>
  );
}

// ------------------------------------------------------------------ taking
type Ans = Record<number, Record<string, unknown>>;

function QuestionView({ q, ans, set }: { q: Question; ans: Record<string, unknown> | undefined; set: (v: Record<string, unknown>) => void }) {
  if (q.qtype === "mcq") return <div className="grid gap-2" role="radiogroup" aria-label="Options">{q.options.map((o, i) => <button key={i} role="radio" aria-checked={ans?.choice === i} onClick={() => set({ choice: i })} className={cn("flex items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm font-medium transition", ans?.choice === i ? "border-brand-600 bg-brand-50 shadow-sm" : "border-line bg-white hover:border-brand-300")}><span className={cn("grid h-6 w-6 shrink-0 place-items-center rounded-full border text-xs font-extrabold", ans?.choice === i ? "border-brand-600 bg-brand-600 text-white" : "border-line-strong")}>{String.fromCharCode(65 + i)}</span>{o}</button>)}</div>;
  if (q.qtype === "true_false") return <div className="flex gap-3" role="radiogroup" aria-label="True or false">{[true, false].map((v) => <button key={String(v)} role="radio" aria-checked={ans?.value === v} onClick={() => set({ value: v })} className={cn("h-14 flex-1 rounded-xl border text-base font-extrabold transition", ans?.value === v ? "border-brand-600 bg-brand-600 text-white" : "border-line bg-white hover:border-brand-300")}>{v ? "True" : "False"}</button>)}</div>;
  if (q.qtype === "output_prediction" || q.qtype === "code_tracing") return <input value={String(ans?.text ?? "")} onChange={(e) => set({ text: e.target.value })} placeholder="Type the exact output" className="input-base font-mono" aria-label="Your answer" />;
  if (q.qtype === "coding" || q.qtype === "debugging") {
    const value = String(ans?.code ?? q.starter_code ?? "");
    return (
      <div className="space-y-2">
        <CodeEditor value={value} onChange={(code) => set({ code })} />
        <p className="text-xs text-ink-500">Write a Python function named <code className="rounded bg-sage-100 px-1">{q.entry_function}</code>. Only the standard library is available; files, network and system access are blocked.</p>
        {q.examples.length ? <div className="rounded-xl bg-sage-50 p-3 text-xs"><b>Examples:</b>{q.examples.map((e, i) => <p key={i} className="font-mono">{q.entry_function}({e.args.map((a) => JSON.stringify(a)).join(", ")}) → {JSON.stringify(e.expected)}</p>)}</div> : null}
      </div>
    );
  }
  return <textarea value={String(ans?.text ?? "")} onChange={(e) => set({ text: e.target.value })} rows={6} placeholder="Write your answer. It is graded against a rubric." className="input-base" aria-label="Your answer" />;
}

function Taking({ quiz, onDone }: { quiz: Quiz; onDone: (r: Report) => void }) {
  const { push } = useToast();
  const [i, setI] = useState(0);
  const [ans, setAns] = useState<Ans>({});
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [left, setLeft] = useState<number | null>(quiz.time_limit_minutes ? quiz.time_limit_minutes * 60 : null);
  const sent = useRef(false);
  const q = quiz.questions[i];
  const answered = (k: Question) => { const a = ans[k.id]; return !!a && (a.choice !== undefined || a.value !== undefined || (typeof a.text === "string" && a.text.trim() !== "") || (typeof a.code === "string" && a.code.trim() !== "" && a.code !== k.starter_code)); };
  const unanswered = quiz.questions.filter((k) => !answered(k)).length;

  const submit = useCallback(async () => {
    if (sent.current) return;
    sent.current = true; setBusy(true); setConfirm(false);
    try { onDone(await lh.submitQuiz(quiz.id, ans)); } catch (e) { sent.current = false; push({ title: "Could not submit", description: (e as Error).message, variant: "error" }); } finally { setBusy(false); }
  }, [ans, onDone, push, quiz.id]);

  useEffect(() => { if (left === null) return; if (left <= 0) { submit(); return; } const id = setTimeout(() => setLeft((l) => (l === null ? l : l - 1)), 1000); return () => clearTimeout(id); }, [left, submit]);
  useEffect(() => { const h = (e: BeforeUnloadEvent) => { if (!sent.current) e.preventDefault(); }; window.addEventListener("beforeunload", h); return () => window.removeEventListener("beforeunload", h); }, []);

  if (busy) return <div role="status" className="card grid place-items-center gap-3 p-16 text-center"><Loader2 className="animate-spin text-brand-600" size={34} /><p className="text-lg font-extrabold">Grading your answers…</p><p className="text-xs text-ink-400">Running coding tests and rubric grading. Hold on.</p></div>;
  return (
    <div className="space-y-4">
      <Card className="sticky top-14 z-10 flex flex-wrap items-center gap-3 p-3">
        <div className="min-w-0 flex-1"><p className="truncate text-sm font-extrabold">{quiz.topic}</p><p className="text-xs text-ink-500">Question {i + 1} of {quiz.questions.length} · {quiz.questions.length - unanswered} answered</p></div>
        {left !== null ? <span className={cn("inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 font-mono text-sm font-extrabold", left < 60 ? "bg-rose-100 text-rose-700" : "bg-sage-100 text-forest-800")} role="timer" aria-live="off"><Clock size={14} />{mmss(left)}</span> : null}
        <Button onClick={() => setConfirm(true)} icon={<Send size={15} />}>Submit</Button>
      </Card>
      <div className="flex flex-wrap gap-1.5" aria-label="Question navigator">{quiz.questions.map((k, n) => <button key={k.id} onClick={() => setI(n)} aria-label={`Question ${n + 1}${answered(k) ? ", answered" : ""}`} className={cn("h-9 w-9 rounded-lg border text-xs font-extrabold transition", n === i ? "border-forest-800 bg-forest-800 text-white" : answered(k) ? "border-brand-500 bg-brand-50 text-brand-700" : "border-line bg-white text-ink-500 hover:border-brand-300")}>{n + 1}</button>)}</div>
      <Card key={q.id} className="cv-rise space-y-4 p-6 sm:p-8">
        <div className="flex flex-wrap items-center gap-2"><span className={cn("rounded-full px-2.5 py-1 text-[11px] font-extrabold capitalize", DIFF_STYLE[q.difficulty])}>{q.difficulty}</span><Badge>{TYPES.find((t) => t[0] === q.qtype)?.[1] ?? q.qtype}</Badge><span className="text-xs text-ink-400">{q.topic}{q.subtopic ? ` › ${q.subtopic}` : ""} · {q.points} pt</span></div>
        <div className="whitespace-pre-wrap text-[17px] font-semibold leading-8 text-forest-900">{q.prompt}</div>
        <QuestionView q={q} ans={ans[q.id]} set={(v) => setAns((a) => ({ ...a, [q.id]: v }))} />
      </Card>
      <div className="flex justify-between"><Button variant="outline" disabled={i === 0} onClick={() => setI(i - 1)} icon={<ChevronLeft size={16} />}>Previous</Button><Button variant={i === quiz.questions.length - 1 ? "primary" : "outline"} onClick={() => (i === quiz.questions.length - 1 ? setConfirm(true) : setI(i + 1))}>{i === quiz.questions.length - 1 ? "Finish" : "Next"} <ChevronRight size={16} className="ml-1" /></Button></div>
      <Modal open={confirm} onClose={() => setConfirm(false)} title="Submit your quiz?" description={unanswered ? `${unanswered} question${unanswered > 1 ? "s are" : " is"} unanswered and will score zero.` : "All questions answered."} size="md" footer={<><Button variant="ghost" onClick={() => setConfirm(false)}>Keep working</Button><Button onClick={submit}>Submit now</Button></>}><p className="text-sm text-ink-600">You cannot change answers after submitting. You can always retry with newly generated questions.</p></Modal>
    </div>
  );
}

// ------------------------------------------------------------------ results
function Results({ r, review, onRetry, onNew, onRevision, retrying }: { r: Report; review: ReviewItem[] | null; onRetry: () => void; onNew: () => void; onRevision: () => void; retrying: boolean }) {
  const tone = r.accuracy >= 75 ? "text-emerald-600" : r.accuracy >= 50 ? "text-amber-600" : "text-rose-600";
  const rows = (r.by_topic.length ? r.by_topic : []).map((t) => ({ name: t.topic.length > 28 ? t.topic.slice(0, 27) + "…" : t.topic, accuracy: t.accuracy }));
  return (
    <div className="space-y-5">
      <Card className="relative overflow-hidden p-0">
        <div className="bg-gradient-to-br from-forest-900 to-forest-700 p-6 text-white sm:p-8">
          <div className="flex flex-wrap items-center gap-6">
            <div className="text-center"><p className={cn("font-display text-6xl font-extrabold", r.accuracy >= 75 ? "text-emerald-300" : r.accuracy >= 50 ? "text-amber-300" : "text-rose-300")}><CountUp value={r.accuracy} format={(v) => `${Math.round(v)}%`} /></p><p className="text-xs font-bold uppercase tracking-wide text-white/60">Accuracy</p></div>
            <div className="min-w-[220px] flex-1"><h2 className="font-display text-2xl font-extrabold !text-white">{r.topic}</h2>
              <p className="mt-1 text-sm text-white/70">Score {r.score}/{r.max_score} · {r.correct}/{r.questions} fully correct · {mmss(r.time_taken_seconds)} taken{r.time_limit_minutes ? ` of ${r.time_limit_minutes}:00` : ""}{r.overtime ? " (over time)" : ""}</p></div>
            <div className="flex flex-col gap-2"><Button variant="secondary" loading={retrying} onClick={onRetry} icon={<RefreshCw size={15} />}>Retry with new questions</Button><Button variant="primary" onClick={onRevision} icon={<Sparkles size={15} />}>Revision quiz on weak topics</Button></div>
          </div>
        </div>
      </Card>
      {r.ungraded ? <InlineNote tone="warn">{r.ungraded} written answer(s) could not be graded because the AI was unavailable. They are excluded from your score and do not affect mastery.</InlineNote> : null}
      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="space-y-3 p-5"><h3 className="font-extrabold text-forest-900">Accuracy by topic</h3>
          {rows.length ? <div style={{ height: Math.max(140, rows.length * 44) }}><ResponsiveContainer width="100%" height="100%"><BarChart data={rows} layout="vertical" margin={{ left: 8, right: 16 }}><CartesianGrid horizontal={false} strokeDasharray="3 3" /><XAxis type="number" domain={[0, 100]} fontSize={11} /><YAxis type="category" dataKey="name" width={150} fontSize={11} /><Tooltip formatter={(v: number) => `${v}%`} /><Bar dataKey="accuracy" radius={[0, 8, 8, 0]}>{rows.map((x, i) => <Cell key={i} fill={x.accuracy >= 75 ? "#229A63" : x.accuracy >= 50 ? "#F2B35E" : "#E25555"} />)}</Bar></BarChart></ResponsiveContainer></div> : <p className="text-sm text-ink-500">No graded questions.</p>}</Card>
        <Card className="space-y-4 p-5">
          <div><h3 className="text-sm font-extrabold text-emerald-700">Strong areas</h3><div className="mt-1.5 flex flex-wrap gap-1.5">{r.strong_areas.length ? r.strong_areas.map((s) => <Badge key={s} tone="brand">{s}</Badge>) : <span className="text-sm text-ink-500">None above 80% yet.</span>}</div></div>
          <div><h3 className="text-sm font-extrabold text-rose-700">Weak areas</h3><div className="mt-1.5 flex flex-wrap gap-1.5">{r.weak_areas.length ? r.weak_areas.map((s) => <Badge key={s} tone="danger">{s}</Badge>) : <span className="text-sm text-ink-500">No area below 60%.</span>}</div></div>
          <div><h3 className="text-sm font-extrabold text-forest-800">Recommended revisions</h3><ul className="mt-1.5 space-y-1 text-sm">{r.recommended_revisions.map((x, i) => <li key={i}><b>{x.topic}</b> <span className="text-ink-500">· {x.reason}</span></li>)}</ul></div>
        </Card>
      </div>
      {review ? <QuizReview items={review} /> : (
      <Card className="space-y-4 p-5">
        <h3 className="font-extrabold text-forest-900">Review your answers {r.incorrect.length ? `(${r.incorrect.length} to learn from)` : ""}</h3>
        {!r.incorrect.length ? <div className="flex items-center gap-2 rounded-xl bg-emerald-50 p-4 font-bold text-emerald-800"><CheckCircle2 />Everything correct. Try a harder quiz.</div> : r.incorrect.map((w) => (
          <details key={w.question_id} className="rounded-2xl border border-line p-4" open={r.incorrect.length <= 3}>
            <summary className="flex cursor-pointer items-start gap-2 font-bold"><XCircle size={18} className="mt-0.5 shrink-0 text-rose-500" /><span className="flex-1">{w.position}. {w.prompt.slice(0, 160)}{w.prompt.length > 160 ? "…" : ""}</span><span className={cn("rounded-full px-2 py-0.5 text-[11px] capitalize", DIFF_STYLE[w.difficulty])}>{w.difficulty}</span></summary>
            <div className="mt-3 space-y-2 text-sm">
              <p className="whitespace-pre-wrap text-ink-700">{w.prompt}</p>
              <p><b>Your answer:</b> <code className="rounded bg-rose-50 px-1.5 py-0.5">{w.your_answer?.code ?? w.your_answer?.text ?? (w.your_answer?.choice !== undefined ? `Option ${String.fromCharCode(65 + w.your_answer.choice)}` : w.your_answer?.value !== undefined ? String(w.your_answer.value) : "(blank)")}</code></p>
              {w.correct?.index !== undefined ? <p><b>Correct answer:</b> Option {String.fromCharCode(65 + w.correct.index)}</p> : w.correct?.answer ? <p><b>Correct answer:</b> <code className="rounded bg-emerald-50 px-1.5 py-0.5">{w.correct.answer}</code></p> : w.correct?.value !== undefined ? <p><b>Correct answer:</b> {String(w.correct.value)}</p> : w.correct?.reference_solution ? <div><b>Reference solution:</b><pre className="mt-1 overflow-x-auto rounded-xl bg-[#0F1B2D] p-3 text-xs text-emerald-100">{w.correct.reference_solution}</pre></div> : null}
              {w.feedback?.total !== undefined ? <p className="text-ink-600"><b>Tests passed:</b> {w.feedback.passed}/{w.feedback.total}{w.feedback.error ? ` · ${w.feedback.error}` : ""}</p> : w.feedback?.passed !== undefined ? <p className="text-ink-600"><b>Tests passed:</b> {w.feedback.passed}/{w.feedback.total}{w.feedback.error ? ` · ${w.feedback.error}` : ""}</p> : null}
              {w.feedback?.overall_feedback ? <p className="text-ink-600"><b>Feedback:</b> {w.feedback.overall_feedback}</p> : null}
              {w.feedback?.marks?.length ? <ul className="list-disc pl-5 text-ink-600">{w.feedback.marks.map((m: any, i: number) => <li key={i}>{m.criterion}: {m.marks}/{m.max}{m.comment ? ` · ${m.comment}` : ""}</li>)}</ul> : null}
              {w.explanation ? <div className="rounded-xl bg-sage-50 p-3"><b>Explanation:</b> {w.explanation}</div> : null}
            </div>
          </details>))}
      </Card>
      )}
      <div className="flex justify-center"><Button variant="outline" onClick={onNew}>Build another quiz</Button></div>
    </div>
  );
}

// ------------------------------------------------------------------ page
export default function Quizzes() {
  const { push } = useToast();
  const [params, setParams] = useSearchParams();
  const [mode, setMode] = useState<"home" | "taking" | "results">("home");
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [review, setReview] = useState<ReviewItem[] | null>(null);
  const [busy, setBusy] = useState(false);
  const hist = useLoad(() => lh.quizzes(), [mode]);
  const openResult = useCallback(async (id: number) => {
    try { const r = await lh.results(id); setQuiz(r.quiz); setReport(r.report); setReview(r.review); setMode("results"); } catch (e) { push({ title: "Could not open results", description: (e as Error).message, variant: "error" }); }
  }, [push]);
  useEffect(() => { const id = params.get("result"); if (id) { openResult(Number(id)); } }, [params, openResult]);

  async function retry() {
    if (!quiz) return;
    setBusy(true);
    try { const q = await lh.retryQuiz(quiz.id); setQuiz(q); setReport(null); setReview(null); setMode("taking"); window.scrollTo({ top: 0 }); }
    catch (e) { push({ title: "Could not create a retry", description: (e as Error).message, variant: "error" }); } finally { setBusy(false); }
  }
  async function revision() {
    setBusy(true);
    try { const q = await lh.createQuiz({ scope: "revision", count: 8, difficulty: "mixed", types: ["mcq", "true_false", "short_answer"], level: "intermediate" }); setQuiz(q); setReport(null); setReview(null); setMode("taking"); }
    catch (e) { push({ title: "No revision quiz yet", description: (e as Error).message, variant: "info" }); } finally { setBusy(false); }
  }
  const home = () => { setMode("home"); setQuiz(null); setReport(null); if (params.get("result")) setParams({}); };

  if (mode === "taking" && quiz) return <Taking quiz={quiz} onDone={(r) => { setReport(r); setMode("results"); lh.results(quiz.id).then((x) => { setQuiz(x.quiz); setReview(x.review); }).catch(() => undefined); }} />;
  if (mode === "results" && report) return <Results r={report} review={review} retrying={busy} onRetry={retry} onNew={home} onRevision={revision} />;
  return (
    <div className="space-y-5">
      <Config onStart={(q) => { setQuiz(q); setMode("taking"); window.scrollTo({ top: 0 }); }} />
      <Card className="space-y-3 p-5">
        <div className="flex items-center justify-between"><h3 className="font-extrabold text-forest-900">Assessment history</h3><Button size="sm" variant="outline" loading={busy} onClick={revision} icon={<RefreshCw size={14} />}>Revision quiz</Button></div>
        {hist.loading && !hist.data ? <Skeleton className="h-24" /> : !hist.data?.items.length ? <EmptyState icon={<AlertCircle size={20} />} title="No assessments yet" description="Generate your first quiz above." /> : (
          <ul className="divide-y divide-line">{hist.data.items.map((h) => (
            <li key={h.id} className="flex flex-wrap items-center gap-3 py-2.5"><span className="min-w-[200px] flex-1 truncate font-bold">{h.topic}</span><span className="text-xs capitalize text-ink-400">{h.scope} · {h.questions} q</span>
              {h.status === "submitted" ? <><Badge tone={(h.accuracy ?? 0) >= 75 ? "brand" : (h.accuracy ?? 0) >= 50 ? "warn" : "danger"}>{Math.round(h.accuracy ?? 0)}%</Badge><Button size="sm" variant="ghost" onClick={() => openResult(h.id)}>Review</Button></> : <Button size="sm" variant="outline" onClick={async () => { try { const q = await lh.quiz(h.id); setQuiz(q); setMode("taking"); } catch (e) { push({ title: "Could not open", description: (e as Error).message, variant: "error" }); } }}>Resume</Button>}
            </li>))}</ul>)}
      </Card>
    </div>
  );
}
void hm; void useMemo;
