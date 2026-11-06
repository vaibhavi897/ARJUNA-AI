/** Detailed study view for one calendar date. Every control writes to the API. */
import { useState } from "react";
import { Link } from "react-router-dom";
import { Check, CheckCheck, ClipboardCheck, Flag, Lock, Moon, NotebookPen, RotateCcw, SkipForward, Sparkles } from "lucide-react";
import { lh, type Day, type Task } from "../../lib/learning";
import { useToast } from "../../lib/auth";
import { cn } from "../../lib/utils";
import { CAT, fmtLong, hm } from "./shared";

const STATUS_BADGE: Record<string, string> = { pending: "bg-slate-100 text-slate-600", rescheduled: "bg-amber-100 text-amber-800", completed: "bg-emerald-100 text-emerald-800", partial: "bg-sky-100 text-sky-800", skipped: "bg-slate-200 text-slate-500" };

function TaskCard({ t, planEnd, planStart, onChange }: { t: Task; planStart: string; planEnd: string; onChange: (t: Task) => void }) {
  const { push } = useToast();
  const [busy, setBusy] = useState(false);
  const [notes, setNotes] = useState(t.notes ?? "");
  const [pct, setPct] = useState(t.status === "partial" ? t.progress_pct : 50);
  const [open, setOpen] = useState(t.status !== "completed");
  const c = CAT[t.category];
  const q = encodeURIComponent(t.topic || t.title);

  async function patch(body: Record<string, unknown>, ok?: string) {
    setBusy(true);
    try {
      const next = await lh.patchTask(t.id, body);
      onChange(next);
      if (ok) push({ title: ok, variant: "success" });
    } catch (e) {
      push({ title: "Could not update", description: (e as Error).message, variant: "error" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className={cn("overflow-hidden rounded-2xl border bg-white shadow-sm transition-all", t.missed && t.status !== "completed" ? "border-rose-300" : "border-line")}>
      <header className="flex cursor-pointer flex-wrap items-start gap-3 p-4" onClick={() => setOpen((o) => !o)}>
        <span className={cn("mt-0.5 rounded-lg px-2.5 py-1 text-[11px] font-extrabold uppercase tracking-wide", c.chip)}>{c.label}</span>
        <div className="min-w-0 flex-1">
          <h4 className={cn("font-bold leading-snug", t.status === "completed" && "text-ink-400 line-through")}>{t.title}</h4>
          <p className="mt-0.5 text-xs text-ink-500">{t.topic ? `${t.topic} · ` : ""}{hm(t.est_minutes)}{t.difficulty ? ` · ${t.difficulty}` : ""}{t.reschedule_count ? ` · moved ${t.reschedule_count}×` : ""}</p>
        </div>
        {t.locked ? <Lock size={14} className="mt-1 text-ink-400" aria-label="Date pinned" /> : null}
        <span className={cn("rounded-full px-2.5 py-1 text-[11px] font-bold capitalize", STATUS_BADGE[t.status])}>{t.missed && t.status !== "completed" ? "missed" : t.status === "partial" ? `partial ${t.progress_pct}%` : t.status}</span>
      </header>

      {open ? (
        <div className="space-y-4 border-t border-line/70 p-4">
          {t.objectives.length ? <div><h5 className="text-xs font-extrabold uppercase tracking-wide text-ink-400">Objectives</h5><ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-ink-700">{t.objectives.map((o) => <li key={o}>{o}</li>)}</ul></div> : null}
          {t.subtopics.length ? <div className="flex flex-wrap gap-1.5">{t.subtopics.map((s) => <span key={s} className="rounded-full bg-sage-100 px-2.5 py-1 text-xs font-medium text-forest-800">{s}</span>)}</div> : null}
          {t.assignment ? <div className="rounded-xl border border-dashed border-brand-300 bg-brand-50/60 p-3 text-sm"><span className="font-bold text-brand-800">Practical task. </span>{t.assignment}</div> : null}
          {t.resources.length ? (
            <div><h5 className="text-xs font-extrabold uppercase tracking-wide text-ink-400">Suggested resources <span className="font-medium normal-case">(AI suggestions to search for, not verified links)</span></h5>
              <ul className="mt-1 space-y-0.5 text-sm text-ink-700">{t.resources.map((r, i) => <li key={i}><b>{r.name}</b> <span className="text-ink-400">({r.kind})</span>{r.search_query ? <> · <a className="underline" target="_blank" rel="noreferrer" href={`https://www.google.com/search?q=${encodeURIComponent(r.search_query)}`}>search “{r.search_query}”</a></> : null}</li>)}</ul></div>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <Link to={`/app/learning/materials?topic=${q}`} className="inline-flex items-center gap-1.5 rounded-xl border border-line-strong px-3 py-2 text-sm font-bold hover:border-brand-400 hover:text-brand-700"><Sparkles size={14} />Generate study notes</Link>
            <Link to={`/app/learning/quizzes?topic=${q}`} className="inline-flex items-center gap-1.5 rounded-xl border border-line-strong px-3 py-2 text-sm font-bold hover:border-brand-400 hover:text-brand-700"><ClipboardCheck size={14} />Quiz me</Link>
            <Link to={`/app/learning/notes`} className="inline-flex items-center gap-1.5 rounded-xl border border-line-strong px-3 py-2 text-sm font-bold hover:border-brand-400 hover:text-brand-700"><NotebookPen size={14} />Open notebooks</Link>
          </div>

          <div className="rounded-2xl bg-sage-50 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <button disabled={busy} onClick={() => patch({ status: "completed" }, "Marked complete")} className="inline-flex items-center gap-1.5 rounded-xl bg-brand-600 px-3.5 py-2 text-sm font-bold text-white hover:bg-brand-700 disabled:opacity-50"><CheckCheck size={15} />Complete</button>
              <button disabled={busy} onClick={() => patch({ status: "partial", progress_pct: pct }, "Saved partial progress")} className="inline-flex items-center gap-1.5 rounded-xl border border-sky-300 bg-white px-3.5 py-2 text-sm font-bold text-sky-700 hover:bg-sky-50 disabled:opacity-50"><Check size={15} />Partial ({pct}%)</button>
              <button disabled={busy} onClick={() => patch({ status: "skipped" }, "Skipped")} className="inline-flex items-center gap-1.5 rounded-xl border border-line-strong bg-white px-3.5 py-2 text-sm font-bold text-ink-600 hover:bg-sage-100 disabled:opacity-50"><SkipForward size={15} />Skip</button>
              {t.status !== "pending" ? <button disabled={busy} onClick={() => patch({ status: "pending" })} className="inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-bold text-ink-500 hover:bg-sage-100"><RotateCcw size={14} />Reset</button> : null}
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <label className="text-xs font-bold text-ink-500">Partial progress<input type="range" min={5} max={95} step={5} value={pct} onChange={(e) => setPct(Number(e.target.value))} className="mt-1 w-full accent-brand-600" aria-label="Partial progress percent" /></label>
              <label className="text-xs font-bold text-ink-500">Reschedule to<input type="date" min={planStart} max={planEnd} defaultValue={t.date} onChange={(e) => e.target.value && e.target.value !== t.date && patch({ date: e.target.value }, "Rescheduled")} className="input-base mt-1 h-9" /></label>
              <div className="text-xs font-bold text-ink-500">How hard was it?
                <div className="mt-1 flex gap-1" role="radiogroup" aria-label="Self-reported difficulty">
                  {[1, 2, 3, 4, 5].map((n) => <button key={n} role="radio" aria-checked={t.self_difficulty === n} onClick={() => patch({ self_difficulty: n })} className={cn("h-9 w-9 rounded-lg border text-sm font-extrabold transition", t.self_difficulty === n ? "border-brand-600 bg-brand-600 text-white" : "border-line-strong bg-white text-ink-600 hover:border-brand-400")}>{n}</button>)}
                </div>
              </div>
            </div>
            <label className="mt-3 block text-xs font-bold text-ink-500">Your notes for this task
              <textarea value={notes} onChange={(e) => setNotes(e.target.value)} onBlur={() => notes !== (t.notes ?? "") && patch({ notes })} rows={2} placeholder="What clicked? What was confusing?" className="input-base mt-1 resize-y" />
            </label>
            <label className="mt-2 inline-flex cursor-pointer items-center gap-2 text-xs font-bold text-ink-500"><input type="checkbox" checked={t.locked} onChange={(e) => patch({ locked: e.target.checked })} className="accent-brand-600" />Pin this date (kept when I regenerate the plan)</label>
          </div>
        </div>
      ) : null}
    </article>
  );
}

export function DayPanel({ date, day, next, planStart, planEnd, onChange, onPick }: { date: string; day?: Day; next?: Day; planStart: string; planEnd: string; onChange: (t: Task) => void; onPick: (d: string) => void }) {
  const tasks = (day?.tasks ?? []).filter((t) => t.category !== "rest");
  const mins = tasks.reduce((s, t) => s + t.est_minutes, 0);
  const done = tasks.filter((t) => t.status === "completed").length;
  return (
    <section aria-label={`Study plan for ${fmtLong(date)}`} className="space-y-3">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div><h3 className="text-xl font-extrabold text-forest-900">{fmtLong(date)}</h3>
          <p className="text-sm text-ink-500">{day?.rest ? "Rest day. Recovery is part of learning." : tasks.length ? `${done}/${tasks.length} done · about ${hm(mins)} planned` : "Nothing planned for this date."}</p></div>
      </header>
      {day?.milestone ? <div className="flex items-center gap-2 rounded-xl border border-fuchsia-200 bg-fuchsia-50 px-4 py-3 text-sm font-bold text-fuchsia-800"><Flag size={16} />{day.milestone.title}</div> : null}
      {day?.rest && !tasks.length ? <div className="grid place-items-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 py-10 text-slate-500"><Moon size={28} /><p className="mt-2 text-sm font-semibold">No tasks. Enjoy your break.</p></div> : null}
      {tasks.map((t) => <TaskCard key={`${t.id}-${t.status}-${t.date}`} t={t} planStart={planStart} planEnd={planEnd} onChange={onChange} />)}
      {next && next.tasks.some((t) => t.category !== "rest") ? (
        <button onClick={() => onPick(next.date)} className="w-full rounded-2xl border border-dashed border-line-strong bg-white/60 p-3 text-left transition hover:border-brand-400">
          <p className="text-xs font-extrabold uppercase tracking-wide text-ink-400">Next up · {fmtLong(next.date)}</p>
          <p className="mt-1 text-sm font-semibold text-ink-700">{next.tasks.filter((t) => t.category !== "rest").map((t) => t.title).join(" · ")}</p>
        </button>
      ) : null}
    </section>
  );
}
