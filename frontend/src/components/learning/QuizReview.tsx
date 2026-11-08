/** Full quiz review: every question marked right, wrong, partly right or skipped, with the correct answer beside yours. */
import { useMemo, useState } from "react";
import { CheckCircle2, CircleDashed, MinusCircle, XCircle } from "lucide-react";
import { Badge, Card } from "../ui";
import { cn } from "../../lib/utils";

export type ReviewItem = {
  question_id: number; position: number; qtype: string; difficulty: string; topic: string; subtopic: string | null; prompt: string; options: string[]; points: number;
  status: "correct" | "wrong" | "partial" | "skipped" | "ungraded"; score: number; your_answer: Record<string, any>; correct: Record<string, any>;
  explanation: string | null; rubric: { criterion: string; marks: number }[] | null; feedback: Record<string, any>;
};

const META: Record<ReviewItem["status"], { label: string; chip: string; ring: string; icon: React.ReactNode }> = {
  correct: { label: "Correct", chip: "bg-emerald-100 text-emerald-800", ring: "border-emerald-300 bg-emerald-50", icon: <CheckCircle2 size={18} className="text-emerald-600" /> },
  wrong: { label: "Incorrect", chip: "bg-rose-100 text-rose-800", ring: "border-rose-300 bg-rose-50", icon: <XCircle size={18} className="text-rose-600" /> },
  partial: { label: "Partly correct", chip: "bg-amber-100 text-amber-800", ring: "border-amber-300 bg-amber-50", icon: <CircleDashed size={18} className="text-amber-600" /> },
  skipped: { label: "Not answered", chip: "bg-slate-200 text-slate-700", ring: "border-slate-300 bg-slate-50", icon: <MinusCircle size={18} className="text-slate-500" /> },
  ungraded: { label: "Not graded", chip: "bg-slate-200 text-slate-700", ring: "border-slate-300 bg-slate-50", icon: <MinusCircle size={18} className="text-slate-500" /> },
};
const DOT: Record<ReviewItem["status"], string> = { correct: "bg-emerald-500 text-white", wrong: "bg-rose-500 text-white", partial: "bg-amber-400 text-white", skipped: "bg-slate-300 text-slate-700", ungraded: "bg-slate-300 text-slate-700" };
const letter = (i: number) => String.fromCharCode(65 + i);

function Choice({ text, tag, mark }: { text: string; tag: string; mark: "right" | "yours-wrong" | "yours-right" | "none" }) {
  const style = mark === "right" ? "border-emerald-400 bg-emerald-50" : mark === "yours-wrong" ? "border-rose-400 bg-rose-50" : mark === "yours-right" ? "border-emerald-500 bg-emerald-100" : "border-line bg-white";
  return (
    <li className={cn("flex items-start gap-3 rounded-xl border px-3 py-2 text-sm", style)}>
      <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-white text-xs font-extrabold text-ink-700 ring-1 ring-line">{tag}</span>
      <span className="flex-1 text-ink-800">{text}</span>
      {mark === "right" ? <span className="shrink-0 text-xs font-bold text-emerald-700">Correct answer</span> : null}
      {mark === "yours-wrong" ? <span className="shrink-0 text-xs font-bold text-rose-700">Your answer</span> : null}
      {mark === "yours-right" ? <span className="shrink-0 text-xs font-bold text-emerald-700">Your answer · correct</span> : null}
    </li>
  );
}

function Body({ r }: { r: ReviewItem }) {
  const a = r.your_answer ?? {};
  if (r.qtype === "mcq") {
    const right = r.correct.index as number | undefined;
    const mine = a.choice as number | undefined;
    return (
      <ul className="space-y-1.5">
        {r.options.map((o, i) => (
          <Choice key={i} text={o} tag={letter(i)} mark={i === mine ? (i === right ? "yours-right" : "yours-wrong") : i === right ? "right" : "none"} />
        ))}
        {mine === undefined ? <li className="text-xs font-semibold text-slate-500">You did not choose an option.</li> : null}
      </ul>
    );
  }
  if (r.qtype === "true_false") {
    const right = r.correct.value as boolean | undefined;
    const mine = a.value as boolean | undefined;
    return (
      <ul className="grid gap-1.5 sm:grid-cols-2">
        {[true, false].map((v) => (
          <Choice key={String(v)} text={v ? "True" : "False"} tag={v ? "T" : "F"} mark={v === mine ? (v === right ? "yours-right" : "yours-wrong") : v === right ? "right" : "none"} />
        ))}
      </ul>
    );
  }
  if (r.qtype === "coding" || r.qtype === "debugging") {
    const f = r.feedback ?? {};
    return (
      <div className="space-y-2 text-sm">
        <div><p className="text-xs font-bold uppercase text-ink-500">Your code</p><pre className="mt-1 overflow-x-auto rounded-xl bg-[#0F1B2D] p-3 text-xs leading-5 text-emerald-100">{a.code?.trim() ? a.code : "(blank)"}</pre></div>
        {f.total !== undefined ? <p className="text-ink-700"><b>Tests passed:</b> {f.passed ?? 0}/{f.total}{f.error ? <span className="text-rose-700"> · {String(f.error)}</span> : null}</p> : null}
        {r.correct.reference_solution ? <div><p className="text-xs font-bold uppercase text-emerald-700">A correct solution</p><pre className="mt-1 overflow-x-auto rounded-xl bg-emerald-950 p-3 text-xs leading-5 text-emerald-100">{String(r.correct.reference_solution)}</pre></div> : null}
      </div>
    );
  }
  if (r.qtype === "output_prediction" || r.qtype === "code_tracing") {
    const mine = String(a.text ?? "").trim();
    return (
      <div className="grid gap-2 text-sm sm:grid-cols-2">
        <div className={cn("rounded-xl border p-3", r.status === "correct" ? "border-emerald-400 bg-emerald-50" : "border-rose-400 bg-rose-50")}><p className="text-xs font-bold uppercase text-ink-500">Your answer</p><code className="mt-1 block break-words">{mine || "(blank)"}</code></div>
        <div className="rounded-xl border border-emerald-400 bg-emerald-50 p-3"><p className="text-xs font-bold uppercase text-emerald-700">Correct answer</p><code className="mt-1 block break-words">{String(r.correct.answer ?? "")}</code></div>
      </div>
    );
  }
  // short answer, scenario: written answers graded against a rubric
  const marks: { criterion: string; marks: number; max: number; comment?: string }[] = r.feedback?.marks ?? [];
  return (
    <div className="space-y-2 text-sm">
      <div className="rounded-xl border border-line bg-white p-3"><p className="text-xs font-bold uppercase text-ink-500">Your answer</p><p className="mt-1 whitespace-pre-wrap text-ink-800">{String(a.text ?? "").trim() || "(blank)"}</p></div>
      {marks.length ? (
        <ul className="space-y-1">
          {marks.map((m, i) => (
            <li key={i} className="flex items-start gap-2 text-ink-700">
              {m.marks >= m.max ? <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-emerald-600" /> : m.marks > 0 ? <CircleDashed size={15} className="mt-0.5 shrink-0 text-amber-600" /> : <XCircle size={15} className="mt-0.5 shrink-0 text-rose-600" />}
              <span><b>{m.criterion}</b> · {m.marks}/{m.max}{m.comment ? ` · ${m.comment}` : ""}</span>
            </li>
          ))}
        </ul>
      ) : r.rubric?.length ? <p className="text-xs text-ink-500">Graded on: {r.rubric.map((x) => `${x.criterion} (${x.marks})`).join(", ")}</p> : null}
      {r.feedback?.overall_feedback ? <p className="text-ink-700"><b>Feedback:</b> {String(r.feedback.overall_feedback)}</p> : null}
    </div>
  );
}

export default function QuizReview({ items }: { items: ReviewItem[] }) {
  const [filter, setFilter] = useState<"all" | "wrong" | "correct">("all");
  const counts = useMemo(() => ({
    correct: items.filter((i) => i.status === "correct").length,
    wrong: items.filter((i) => i.status === "wrong" || i.status === "partial" || i.status === "skipped").length,
  }), [items]);
  const shown = items.filter((i) => filter === "all" || (filter === "correct" ? i.status === "correct" : i.status !== "correct" && i.status !== "ungraded"));
  const tab = (k: typeof filter, label: string) => (
    <button key={k} onClick={() => setFilter(k)} aria-pressed={filter === k} className={cn("rounded-full border px-3.5 py-1.5 text-sm font-bold transition", filter === k ? "border-brand-500 bg-brand-600 text-white" : "border-line bg-white text-ink-700 hover:border-brand-300")}>{label}</button>
  );
  return (
    <Card className="space-y-4 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-extrabold text-forest-900">Question by question</h3>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filter questions">
          {tab("all", `All ${items.length}`)}{tab("wrong", `Needs work ${counts.wrong}`)}{tab("correct", `Correct ${counts.correct}`)}
        </div>
      </div>
      <div className="flex flex-wrap gap-1.5" aria-label="Question navigator">
        {items.map((i) => (
          <a key={i.question_id} href={`#qr-${i.question_id}`} title={`Question ${i.position}: ${META[i.status].label}`} className={cn("grid h-8 w-8 place-items-center rounded-full text-xs font-extrabold transition hover:scale-110", DOT[i.status])}>{i.position}</a>
        ))}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-500">
        {(["correct", "partial", "wrong", "skipped"] as const).map((k) => <span key={k} className="inline-flex items-center gap-1.5"><i className={cn("h-2.5 w-2.5 rounded-full", DOT[k].split(" ")[0])} />{META[k].label}</span>)}
      </div>
      {shown.length === 0 ? <p className="rounded-xl bg-sage-50 p-4 text-sm text-ink-600">{filter === "wrong" ? "Nothing to fix. Every question was correct." : "No questions in this view."}</p> : null}
      <div className="space-y-3">
        {shown.map((r) => (
          <details key={r.question_id} id={`qr-${r.question_id}`} open={r.status !== "correct"} className={cn("rounded-2xl border p-4", META[r.status].ring)}>
            <summary className="flex cursor-pointer list-none items-start gap-2.5 font-bold text-ink-900">
              <span className="mt-0.5 shrink-0">{META[r.status].icon}</span>
              <span className="flex-1">{r.position}. {r.prompt.length > 150 ? r.prompt.slice(0, 149) + "…" : r.prompt}</span>
              <span className={cn("shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-bold", META[r.status].chip)}>{META[r.status].label}{r.status === "partial" || r.status === "wrong" ? ` · ${r.score}/${r.points}` : ""}</span>
            </summary>
            <div className="mt-3 space-y-3">
              <div className="flex flex-wrap items-center gap-1.5"><Badge tone="neutral">{r.topic}</Badge><Badge tone="neutral">{r.difficulty}</Badge><span className="text-xs text-ink-500">{r.points} point{r.points === 1 ? "" : "s"}</span></div>
              <p className="whitespace-pre-wrap text-sm text-ink-800">{r.prompt}</p>
              <Body r={r} />
              {r.explanation ? <div className="rounded-xl bg-white/80 p-3 text-sm text-ink-700 ring-1 ring-line"><b>Why:</b> {r.explanation}</div> : null}
            </div>
          </details>
        ))}
      </div>
    </Card>
  );
}
