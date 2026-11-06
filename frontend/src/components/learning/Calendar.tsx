/** Interactive plan calendar: month and week grids, colour-coded by task category. */
import { ChevronLeft, ChevronRight, Flag, Moon } from "lucide-react";
import type { Day } from "../../lib/learning";
import { cn } from "../../lib/utils";
import { CAT, addDays, hm, iso, parse, startOfWeek, todayIso } from "./shared";

const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export type CalView = "month" | "week" | "day";

export function CalendarHeader({ view, onView, cursor, onCursor }: { view: CalView; onView: (v: CalView) => void; cursor: Date; onCursor: (d: Date) => void }) {
  const step = (dir: number) => onCursor(view === "month" ? new Date(cursor.getFullYear(), cursor.getMonth() + dir, 1) : addDays(cursor, dir * (view === "week" ? 7 : 1)));
  const label = view === "month" ? cursor.toLocaleDateString(undefined, { month: "long", year: "numeric" })
    : view === "week" ? `${startOfWeek(cursor).toLocaleDateString(undefined, { day: "numeric", month: "short" })} – ${addDays(startOfWeek(cursor), 6).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}`
    : cursor.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-1">
        <button aria-label="Previous" onClick={() => step(-1)} className="grid h-9 w-9 place-items-center rounded-xl border border-line-strong bg-white hover:border-brand-400 hover:text-brand-700"><ChevronLeft size={18} /></button>
        <button aria-label="Next" onClick={() => step(1)} className="grid h-9 w-9 place-items-center rounded-xl border border-line-strong bg-white hover:border-brand-400 hover:text-brand-700"><ChevronRight size={18} /></button>
        <button onClick={() => onCursor(new Date())} className="ml-1 h-9 rounded-xl border border-line-strong bg-white px-3 text-sm font-bold hover:border-brand-400 hover:text-brand-700">Today</button>
      </div>
      <h3 className="min-w-[200px] flex-1 text-lg font-extrabold text-forest-900" aria-live="polite">{label}</h3>
      <div className="inline-flex rounded-xl bg-sage-100 p-1" role="tablist" aria-label="Calendar view">
        {(["month", "week", "day"] as const).map((v) => (
          <button key={v} role="tab" aria-selected={view === v} onClick={() => onView(v)} className={cn("rounded-lg px-4 py-1.5 text-sm font-bold capitalize transition-all", view === v ? "bg-white text-forest-800 shadow" : "text-ink-500 hover:text-ink-800")}>{v}</button>
        ))}
      </div>
    </div>
  );
}

function DayCell({ date, day, inPlan, selected, onSelect, compact }: { date: Date; day?: Day; inPlan: boolean; selected: boolean; onSelect: (d: string) => void; compact?: boolean }) {
  const key = iso(date);
  const today = key === todayIso();
  const tasks = (day?.tasks ?? []).filter((t) => t.category !== "rest");
  const missed = tasks.some((t) => t.missed);
  const pct = day && day.total ? Math.round((100 * day.done) / day.total) : 0;
  const max = compact ? 6 : 3;
  return (
    <button onClick={() => onSelect(key)} aria-label={`${date.toDateString()}${tasks.length ? `, ${tasks.length} tasks` : day?.rest ? ", rest day" : ""}`} aria-pressed={selected}
      className={cn("group relative flex min-h-[112px] flex-col rounded-xl border p-1.5 text-left transition-all", compact && "min-h-[300px] p-2",
        !inPlan ? "border-transparent bg-transparent opacity-40" : day?.rest ? "border-slate-200 bg-slate-50/80" : "border-line bg-white hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-md",
        selected && "ring-2 ring-brand-500 ring-offset-1", today && "border-brand-500")}>
      <div className="flex items-center justify-between">
        <span className={cn("grid h-6 min-w-6 place-items-center rounded-full px-1 text-xs font-extrabold", today ? "bg-brand-600 text-white" : "text-ink-600")}>{date.getDate()}</span>
        <span className="flex items-center gap-1">
          {missed ? <span title="Missed tasks" className="h-2 w-2 rounded-full bg-rose-500" /> : null}
          {day?.milestone ? <Flag size={13} className="text-fuchsia-600" aria-label={day.milestone.title} /> : null}
          {day?.rest && inPlan ? <Moon size={12} className="text-slate-400" aria-label="Rest day" /> : null}
        </span>
      </div>
      <div className="mt-1 flex-1 space-y-1 overflow-hidden">
        {tasks.slice(0, max).map((t) => (
          <div key={t.id} title={t.title} className={cn("flex items-center gap-1 truncate rounded-md border px-1.5 py-0.5 text-[11px] font-semibold leading-tight", CAT[t.category].soft, CAT[t.category].text, t.status === "completed" && "opacity-60 line-through", t.status === "skipped" && "opacity-40")}>
            <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", CAT[t.category].dot)} />
            <span className="truncate">{compact ? `${t.title} · ${hm(t.est_minutes)}` : t.title}</span>
          </div>
        ))}
        {tasks.length > max ? <p className="px-1 text-[10px] font-bold text-ink-400">+{tasks.length - max} more</p> : null}
        {day?.rest && inPlan && !tasks.length ? <p className="px-1 pt-2 text-[11px] font-semibold text-slate-400">Rest day</p> : null}
      </div>
      {day && day.total > 0 ? <div className="mt-1 h-1 overflow-hidden rounded-full bg-sage-200"><div className="h-full rounded-full bg-brand-500 transition-all duration-700" style={{ width: `${pct}%` }} /></div> : null}
    </button>
  );
}

export function Calendar({ view, cursor, days, planStart, planEnd, selected, onSelect }: { view: Exclude<CalView, "day">; cursor: Date; days: Map<string, Day>; planStart: string; planEnd: string; selected: string | null; onSelect: (d: string) => void }) {
  const cells: Date[] = [];
  if (view === "month") {
    const first = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    const start = startOfWeek(first);
    for (let i = 0; i < 42; i++) cells.push(addDays(start, i));
    while (cells.length > 35 && cells.slice(-7).every((d) => d.getMonth() !== cursor.getMonth())) cells.splice(-7);
  } else {
    const start = startOfWeek(cursor);
    for (let i = 0; i < 7; i++) cells.push(addDays(start, i));
  }
  const ps = parse(planStart), pe = parse(planEnd);
  return (
    <div role="grid" aria-label="Learning calendar">
      <div className="mb-1 grid grid-cols-7 gap-1.5" role="row">
        {DOW.map((d) => <div key={d} role="columnheader" className="px-2 text-[11px] font-extrabold uppercase tracking-wide text-ink-400">{d}</div>)}
      </div>
      <div key={`${view}-${iso(cursor)}`} className="cv-rise grid grid-cols-7 gap-1.5">
        {cells.map((d) => (
          <DayCell key={iso(d)} date={d} day={days.get(iso(d))} inPlan={d >= ps && d <= pe && (view === "week" || d.getMonth() === cursor.getMonth() || true)} selected={selected === iso(d)} onSelect={onSelect} compact={view === "week"} />
        ))}
      </div>
    </div>
  );
}

export function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-ink-500" aria-label="Legend">
      {(["learn", "practice", "project", "revision", "assessment"] as const).map((c) => <span key={c} className="inline-flex items-center gap-1.5"><i className={cn("h-2.5 w-2.5 rounded-full", CAT[c].dot)} />{CAT[c].label}</span>)}
      <span className="inline-flex items-center gap-1.5"><Flag size={12} className="text-fuchsia-600" />Milestone</span>
      <span className="inline-flex items-center gap-1.5"><Moon size={12} className="text-slate-400" />Rest day</span>
      <span className="inline-flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-rose-500" />Missed</span>
    </div>
  );
}
