/** Progress & Mastery: consistency, assessment trends and multi-signal topic mastery. */
import { useState } from "react";
import { CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Bar, BarChart } from "recharts";
import { Flame, Info, RefreshCw, TrendingUp } from "lucide-react";
import { Badge, Button, Card, EmptyState, ErrorState, InlineNote } from "../../components/ui";
import { CountUp } from "../../components/fx";
import { STATUS_STYLE, Skeleton, Stat, addDays, fmtShort, hm, iso, parse, useLoad } from "../../components/learning/shared";
import { lh } from "../../lib/learning";
import { useToast } from "../../lib/auth";
import { cn } from "../../lib/utils";

const STATUS_COLOR: Record<string, string> = { not_started: "#CBD5E1", learning: "#38BDF8", developing: "#F59E0B", needs_revision: "#F43F5E", strong: "#10B981", mastered: "#8B5CF6" };
const SIGNALS: [string, string][] = [["accuracy", "Weighted accuracy"], ["coverage", "Subtopic coverage"], ["coding", "Coding"], ["retention", "Retention"], ["trend", "Improvement"]];

function Heatmap({ data }: { data: { date: string; tasks: number }[] }) {
  const map = new Map(data.map((d) => [d.date, d]));
  const end = new Date();
  const start = addDays(end, -(17 * 7 - 1) - ((end.getDay() + 6) % 7));
  const cols: Date[][] = [];
  for (let w = 0; w < 18; w++) cols.push(Array.from({ length: 7 }, (_, d) => addDays(start, w * 7 + d)));
  const shade = (n: number) => (n === 0 ? "bg-sage-100" : n === 1 ? "bg-emerald-200" : n === 2 ? "bg-emerald-300" : n <= 4 ? "bg-emerald-500" : "bg-emerald-700");
  return (
    <div className="overflow-x-auto pb-1" role="img" aria-label="Study activity heatmap for the last 18 weeks">
      <div className="flex gap-1">
        {cols.map((c, i) => <div key={i} className="flex flex-col gap-1">{c.map((d) => { const v = map.get(iso(d)); const future = d > end; return <span key={iso(d)} title={future ? "" : `${fmtShort(iso(d))}: ${v ? `${v.tasks} task${v.tasks > 1 ? "s" : ""} completed` : "no activity"}`} className={cn("h-4 w-4 rounded-[4px] transition hover:scale-125", future ? "bg-transparent" : shade(v?.tasks ?? 0))} />; })}</div>)}
      </div>
      <div className="mt-2 flex items-center gap-1.5 text-[11px] text-ink-400">Less {["bg-sage-100", "bg-emerald-200", "bg-emerald-300", "bg-emerald-500", "bg-emerald-700"].map((c) => <i key={c} className={cn("h-3 w-3 rounded-[3px]", c)} />)} More</div>
    </div>
  );
}

export default function Progress() {
  const { push } = useToast();
  const pr = useLoad(() => lh.progress(), []);
  const ps = useLoad(() => lh.personalization(), []);
  const st = useLoad(() => lh.settings(), []);
  const rv = useLoad(() => lh.revisions(), []);
  const [scale, setScale] = useState<number | null>(null);
  const [filter, setFilter] = useState("all");
  if (pr.loading && !pr.data) return <div className="space-y-4"><div className="grid gap-4 sm:grid-cols-4"><Skeleton className="h-28" /><Skeleton className="h-28" /><Skeleton className="h-28" /><Skeleton className="h-28" /></div><Skeleton className="h-64" /></div>;
  if (pr.error || !pr.data) return <ErrorState message={pr.error ?? "Could not load"} onRetry={pr.reload} />;
  const d = pr.data;
  const donut = Object.entries(d.mastery_counts).filter(([, v]) => v > 0).map(([k, v]) => ({ key: k, name: d.status_labels[k], value: v }));
  const topics = d.mastery.filter((m) => filter === "all" || m.status === filter);
  const phaseDone = d.phases.reduce((s, p) => s + p.done, 0), phaseTotal = d.phases.reduce((s, p) => s + p.total, 0);
  const effScale = scale ?? st.data?.interval_scale ?? 1;

  async function saveScale() {
    try { await lh.putSettings({ interval_scale: effScale }); push({ title: "Revision intervals updated", description: effScale < 1 ? "Topics will come back sooner." : effScale > 1 ? "Topics will come back later." : "Standard spacing.", variant: "success" }); st.reload(); rv.reload(); } catch (e) { push({ title: "Could not save", description: (e as Error).message, variant: "error" }); }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Roadmap" tone="brand" value={<><CountUp value={phaseTotal ? (100 * phaseDone) / phaseTotal : 0} format={(v) => `${Math.round(v)}`} />%</>} sub={`${phaseDone}/${phaseTotal} tasks across phases`} />
        <Stat label="Streak" tone="amber" icon={<Flame size={20} className="text-amber-500" />} value={<>{d.streak.current}<span className="text-base font-bold text-ink-400"> days</span></>} sub={`Best ${d.streak.best} · ${d.streak.active_days} active days`} />
        <Stat label="Topics tracked" tone="sky" value={d.mastery.length} sub={`${d.mastery_counts.strong + d.mastery_counts.mastered} strong or mastered`} />
        <Stat label="Revision" tone="violet" value={`${d.revision.tasks_done}/${d.revision.tasks_total}`} sub={`${d.revision.due_now} due now · ${d.revision.topics_tracked} topics scheduled`} />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="space-y-4 p-5"><h3 className="font-extrabold text-forest-900">Consistency (tasks completed, last 18 weeks)</h3><Heatmap data={d.heatmap} />
          {d.weekly.length ? <div className="h-36"><ResponsiveContainer width="100%" height="100%"><BarChart data={d.weekly.slice(-12).map((w) => ({ ...w, label: fmtShort(w.week) }))}><CartesianGrid vertical={false} strokeDasharray="3 3" /><XAxis dataKey="label" fontSize={10} /><YAxis fontSize={10} width={28} /><Tooltip formatter={(v: number) => `${v} task${v === 1 ? "" : "s"}`} /><Bar dataKey="tasks" fill="#229A63" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div> : <p className="text-sm text-ink-500">Complete tasks to see your weekly activity.</p>}
        </Card>
        <Card className="space-y-3 p-5"><h3 className="flex items-center gap-2 font-extrabold text-forest-900"><TrendingUp size={16} className="text-brand-600" />Quiz accuracy trend</h3>
          {d.quiz_trend.length < 2 ? <EmptyState title={d.quiz_trend.length ? "One more quiz to see a trend" : "No assessments yet"} description="Accuracy over time appears after two or more quizzes." /> : <div className="h-60"><ResponsiveContainer width="100%" height="100%"><LineChart data={d.quiz_trend.map((q, i) => ({ n: i + 1, accuracy: Math.round(q.accuracy), topic: q.topic }))}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="n" fontSize={11} label={{ value: "Quiz #", position: "insideBottom", offset: -2, fontSize: 11 }} /><YAxis domain={[0, 100]} fontSize={11} width={30} /><Tooltip formatter={(v: number, _n, p: any) => [`${v}%`, p.payload.topic]} /><Line type="monotone" dataKey="accuracy" stroke="#229A63" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 7 }} /></LineChart></ResponsiveContainer></div>}
          {d.improvement.length ? <div className="border-t border-line pt-3"><p className="text-xs font-extrabold uppercase tracking-wide text-ink-400">Skill improvement (first → latest)</p>{d.improvement.slice(0, 4).map((x) => <p key={x.topic} className="mt-1 flex items-center justify-between text-sm"><span className="truncate pr-2">{x.topic}</span><span className={cn("font-extrabold", x.change >= 0 ? "text-emerald-600" : "text-rose-600")}>{Math.round(x.first)}% → {Math.round(x.latest)}% ({x.change >= 0 ? "+" : ""}{Math.round(x.change)})</span></p>)}</div> : null}
        </Card>
      </div>

      <Card className="space-y-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-extrabold text-forest-900">Topic mastery</h3>
          <div className="flex flex-wrap gap-1.5">{["all", ...Object.keys(d.status_labels).filter((k) => k !== "not_started")].map((k) => <button key={k} aria-pressed={filter === k} onClick={() => setFilter(k)} className={cn("rounded-full border px-3 py-1 text-xs font-bold transition", filter === k ? "border-forest-800 bg-forest-800 text-white" : "border-line-strong bg-white text-ink-600 hover:border-brand-400")}>{k === "all" ? "All" : d.status_labels[k]}</button>)}</div></div>
        <InlineNote><Info size={14} className="mr-1 inline" />Mastery comes from quiz results only: difficulty- and recency-weighted accuracy, subtopic coverage, coding performance, spaced-repetition retention and improvement between attempts. Reading notes or watching videos does not raise it.</InlineNote>
        {!d.mastery.length ? <EmptyState title="No mastery data yet" description="Take a quiz on any topic and your proficiency appears here, with the signals behind it." /> : (
          <div className="grid gap-5 lg:grid-cols-[260px_1fr]">
            <div className="h-56"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={donut} dataKey="value" innerRadius={50} outerRadius={80} paddingAngle={3} stroke="none" onClick={(p: any) => setFilter(filter === p.key ? "all" : p.key)}>{donut.map((x) => <Cell key={x.key} fill={STATUS_COLOR[x.key]} style={{ cursor: "pointer" }} opacity={filter !== "all" && filter !== x.key ? 0.35 : 1} />)}</Pie><Tooltip formatter={(v: number, n: string) => [`${v} topic${v > 1 ? "s" : ""}`, n]} /></PieChart></ResponsiveContainer></div>
            <ul className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
              {topics.map((m) => (
                <li key={m.topic} className="rounded-2xl border border-line p-3">
                  <div className="flex items-center gap-3"><span className="flex-1 truncate font-bold">{m.topic}</span><span className={cn("rounded-full px-2.5 py-0.5 text-[11px] font-bold", STATUS_STYLE[m.status])}>{m.status_label}</span><span className="w-10 text-right text-sm font-extrabold">{Math.round(m.score)}%</span></div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-sage-200"><div className="h-full rounded-full transition-all duration-700" style={{ width: `${m.score}%`, background: STATUS_COLOR[m.status] }} /></div>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] text-ink-500">{SIGNALS.map(([k, l]) => <span key={k}>{l}: <b>{m.signals[k] == null ? "n/a" : `${Math.round((m.signals[k] as number) * 100)}%`}</b></span>)}<span>{m.attempts} questions</span></div>
                </li>))}
              {!topics.length ? <p className="text-sm text-ink-500">No topics with that status.</p> : null}
            </ul>
          </div>)}
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="space-y-3 p-5"><h3 className="font-extrabold text-forest-900">Phases & milestones</h3>
          {d.phases.map((p) => <div key={p.key}><div className="flex justify-between text-xs font-bold text-ink-600"><span>{p.title}</span><span>{p.done}/{p.total}</span></div><div className="mt-1 h-2 overflow-hidden rounded-full bg-sage-200"><div className="h-full rounded-full bg-brand-500 transition-all duration-700" style={{ width: `${p.total ? (100 * p.done) / p.total : 0}%` }} /></div></div>)}
          {!d.phases.length ? <p className="text-sm text-ink-500">Create a plan to track phases.</p> : null}
          {d.milestones.length ? <ul className="space-y-1 border-t border-line pt-3">{d.milestones.slice(0, 8).map((m) => <li key={m.week + m.title} className="flex items-center gap-2 text-sm"><i className={cn("h-2.5 w-2.5 rotate-45 rounded-[2px]", m.completed ? "bg-fuchsia-600" : "bg-fuchsia-200")} /><span className="flex-1 truncate">{m.title}</span><span className="text-xs text-ink-400">{fmtShort(m.due)}</span></li>)}</ul> : null}
        </Card>
        <Card className="space-y-3 p-5"><h3 className="font-extrabold text-forest-900">Assessment history</h3>
          {!d.assessment_history.length ? <p className="text-sm text-ink-500">No assessments yet.</p> : <ul className="max-h-60 divide-y divide-line overflow-y-auto">{d.assessment_history.map((a) => <li key={a.id} className="flex items-center gap-3 py-2 text-sm"><span className="flex-1 truncate font-medium">{a.topic}</span><span className="text-xs text-ink-400">{fmtShort(a.at.slice(0, 10))}</span><Badge tone={a.accuracy >= 75 ? "brand" : a.accuracy >= 50 ? "warn" : "danger"}>{Math.round(a.accuracy)}%</Badge></li>)}</ul>}
        </Card>
      </div>

      <Card className="space-y-4 p-5">
        <div className="flex items-center gap-2"><RefreshCw size={16} className="text-brand-600" /><h3 className="font-extrabold text-forest-900">Spaced repetition</h3></div>
        <div className="grid gap-5 lg:grid-cols-2">
          <div>
            <p className="text-sm text-ink-600">After each quiz, topics return at growing intervals (1, 6, then roughly ×ease days). A poor result resets the topic to tomorrow. Due reviews are added to your planner as revision tasks.</p>
            <label className="mt-4 block text-sm font-bold">Interval scale: <span className="text-brand-700">{effScale.toFixed(2)}×</span> <span className="font-normal text-ink-400">({effScale < 1 ? "more frequent" : effScale > 1 ? "less frequent" : "standard"})</span>
              <input type="range" min={0.5} max={2} step={0.1} value={effScale} onChange={(e) => setScale(Number(e.target.value))} className="mt-2 w-full accent-brand-600" aria-label="Revision interval scale" /></label>
            <Button size="sm" className="mt-2" onClick={saveScale} disabled={scale === null}>Save</Button>
          </div>
          <div><p className="text-xs font-extrabold uppercase tracking-wide text-ink-400">Upcoming reviews</p>
            {!rv.data?.items.length ? <p className="mt-2 text-sm text-ink-500">None scheduled yet. They start after your first quiz or completed study task.</p> : <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto">{rv.data.items.map((r) => <li key={r.topic} className="flex items-center gap-2 text-sm"><span className="flex-1 truncate">{r.topic}</span><span className={cn("text-xs font-bold", r.overdue ? "text-rose-600" : "text-ink-500")}>{r.overdue ? "Overdue · " : ""}{fmtShort(r.due)}</span><span className="text-[11px] text-ink-400">{r.interval_days}d</span></li>)}</ul>}
          </div>
        </div>
      </Card>

      {ps.data ? <InlineNote tone="brand"><b>How recommendations work:</b> {ps.data.note} <span className="opacity-70">({ps.data.events_collected} learning events and {ps.data.feedback_collected} feedback signals collected; a learned policy needs about {ps.data.rl_min_events}.)</span></InlineNote> : null}
    </div>
  );
}
