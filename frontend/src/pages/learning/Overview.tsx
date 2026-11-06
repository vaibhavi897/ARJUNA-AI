/** Learning Overview: a personalised command centre. */
import { Link, useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowRight, BookOpen, CalendarCheck, Clock, Flame, Plus, RefreshCcw, Sparkles, ThumbsDown, ThumbsUp, Trophy } from "lucide-react";
import { Badge, Button, Card, EmptyState, ErrorState } from "../../components/ui";
import { CountUp, Reveal } from "../../components/fx";
import { CAT, STATUS_STYLE, Skeleton, Stat, fmtShort, hm, useLoad } from "../../components/learning/shared";
import { lh, type Rec } from "../../lib/learning";
import { useToast } from "../../lib/auth";
import { cn } from "../../lib/utils";
import { useState } from "react";

function Ring({ pct, size = 112 }: { pct: number; size?: number }) {
  const r = size / 2 - 9, c = 2 * Math.PI * r;
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }} role="img" aria-label={`${Math.round(pct)} percent complete`}>
      <svg viewBox={`0 0 ${size} ${size}`} className="absolute inset-0 -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,.2)" strokeWidth="9" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="url(#ringg)" strokeWidth="9" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct / 100)} style={{ transition: "stroke-dashoffset 1.2s ease" }} />
        <defs><linearGradient id="ringg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor="#6EE7B7" /><stop offset="100%" stopColor="#34D399" /></linearGradient></defs>
      </svg>
      <span className="text-2xl font-extrabold text-white"><CountUp value={pct} format={(v) => `${Math.round(v)}%`} /></span>
    </div>
  );
}

function route(a: Rec["action"]): string {
  switch (a.type) {
    case "open_missed": return "/app/learning/planner?missed=1";
    case "open_day": return `/app/learning/planner?date=${a.date}`;
    case "revision_quiz": return "/app/learning/quizzes?scope=revision";
    case "quiz": return `/app/learning/quizzes?topic=${encodeURIComponent(String(a.topic))}`;
    case "materials": return "/app/learning/materials";
    default: return "/app/learning/planner?new=1";
  }
}

export default function Overview() {
  const nav = useNavigate();
  const { push } = useToast();
  const ov = useLoad(() => lh.overview(), []);
  const [voted, setVoted] = useState<Record<string, boolean>>({});
  if (ov.loading && !ov.data) return <div className="space-y-4"><Skeleton className="h-52" /><div className="grid gap-4 sm:grid-cols-4"><Skeleton className="h-28" /><Skeleton className="h-28" /><Skeleton className="h-28" /><Skeleton className="h-28" /></div><Skeleton className="h-64" /></div>;
  if (ov.error || !ov.data) return <ErrorState message={ov.error ?? "Could not load"} onRetry={ov.reload} />;
  const d = ov.data, p = d.plan;

  async function vote(r: Rec, helpful: boolean) {
    setVoted((v) => ({ ...v, [r.id]: true }));
    try { await lh.feedback({ kind: "recommendation", ref: r.id, value: { helpful, kind: r.kind } }); push({ title: "Thanks, noted", description: "Feedback tunes future suggestions.", variant: "success" }); } catch { /* feedback is best-effort */ }
  }

  return (
    <div className="space-y-6">
      {/* goal card */}
      <Reveal>
        <Card className="relative overflow-hidden p-0">
          <div className="relative bg-gradient-to-br from-forest-900 via-forest-800 to-[#12305A] p-6 text-white sm:p-8">
            <span className="cv-blob" style={{ right: -60, top: -80, width: 300, height: 300, background: "#34D399" }} />
            {p ? (
              <div className="relative flex flex-wrap items-center gap-6">
                <Ring pct={p.completion_pct} />
                <div className="min-w-[260px] flex-1">
                  <p className="text-[11px] font-extrabold uppercase tracking-[0.2em] text-emerald-300">Current learning goal</p>
                  <h2 className="mt-1 font-display text-3xl font-extrabold !text-white">{p.goal}</h2>
                  <p className="mt-1 text-sm text-white/70">Day {p.day_number} of {p.total_days} · {p.tasks_done}/{p.tasks_total} tasks done · level <b className="capitalize">{p.starting_level}</b>{p.next_milestone ? <> · next checkpoint {fmtShort(p.next_milestone.due)}</> : null}</p>
                  {p.summary ? <p className="mt-2 line-clamp-2 max-w-2xl text-sm text-white/60">{p.summary}</p> : null}
                </div>
                <div className="flex flex-col gap-2"><Link to="/app/learning/planner"><Button variant="secondary" icon={<CalendarCheck size={16} />}>Open planner</Button></Link><Link to="/app/learning/planner?new=1"><Button variant="primary" icon={<Plus size={16} />}>New learning plan</Button></Link></div>
              </div>
            ) : (
              <div className="relative max-w-2xl">
                <h2 className="font-display text-3xl font-extrabold !text-white">Start with a goal.</h2>
                <p className="mt-2 text-white/75">Pick any duration and a target role. Gemini reads your existing profile, finds your real starting level, and builds a day-by-day calendar around your schedule.</p>
                <Button size="lg" className="mt-5" onClick={() => nav("/app/learning/planner?new=1")} icon={<Sparkles size={18} />}>Create my learning plan</Button>
              </div>
            )}
          </div>
        </Card>
      </Reveal>

      {p?.missed ? (
        <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-5 py-3 text-sm text-rose-800"><AlertTriangle size={16} /><span className="flex-1 font-semibold">{p.missed} missed task{p.missed > 1 ? "s" : ""} are waiting. A quick reschedule keeps your deadline realistic.</span><Link to="/app/learning/planner?missed=1"><Button size="sm" variant="outline">Review</Button></Link></div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Reveal><Stat label="Study streak" tone="amber" icon={<Flame className="text-amber-500" size={20} />} value={<><CountUp value={d.streak.current} /> <span className="text-base font-bold text-ink-400">days</span></>} sub={`Best ${d.streak.best} · ${d.streak.active_days} active days`} /></Reveal>
        <Reveal delay={60}><Stat label="Roadmap" tone="sky" value={p ? <CountUp value={p.completion_pct} format={(v) => `${Math.round(v)}%`} /> : "–"} sub={p ? `${p.tasks_done}/${p.tasks_total} tasks done` : "No plan yet"} /></Reveal>
        <Reveal delay={120}><Stat label="This week" tone="brand" icon={<CalendarCheck className="text-emerald-600" size={20} />} value={p ? `${p.week.done}/${p.week.total}` : "–"} sub={p ? "tasks completed" : "No plan yet"} /></Reveal>
        <Reveal delay={180}><Stat label="Revisions due" tone="violet" icon={<RefreshCcw className="text-violet-500" size={20} />} value={d.upcoming_revisions.filter((r) => r.due <= new Date().toISOString().slice(0, 10)).length} sub={`${d.upcoming_revisions.length} in the next 7 days`} /></Reveal>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-5">
          <Card className="space-y-3 p-5">
            <div className="flex items-center justify-between"><h3 className="font-extrabold text-forest-900">Today's tasks</h3>{p ? <Link className="text-xs font-bold text-brand-700 underline" to={`/app/learning/planner?date=${new Date().toISOString().slice(0, 10)}`}>Open day</Link> : null}</div>
            {!p ? <EmptyState icon={<BookOpen size={20} />} title="No plan yet" description="Create a plan to see what to study today." /> : !p.today.filter((t) => t.category !== "rest").length ? <p className="rounded-xl bg-slate-50 p-4 text-sm font-semibold text-slate-500">{p.today.some((t) => t.category === "rest") ? "Rest day. Recovery is part of learning." : "Nothing scheduled today."}</p> :
              p.today.filter((t) => t.category !== "rest").map((t) => (
                <Link key={t.id} to={`/app/learning/planner?date=${t.date}`} className="flex items-center gap-3 rounded-xl border border-line p-3 transition hover:border-brand-300 hover:shadow-sm">
                  <span className={cn("rounded-lg px-2 py-1 text-[10px] font-extrabold uppercase", CAT[t.category].chip)}>{CAT[t.category].label}</span>
                  <span className={cn("flex-1 text-sm font-bold", t.status === "completed" && "text-ink-400 line-through")}>{t.title}</span><span className="text-xs text-ink-500">{hm(t.est_minutes)}</span>
                </Link>))}
          </Card>
          <Card className="space-y-3 p-5">
            <h3 className="font-extrabold text-forest-900">Upcoming</h3>
            {!p?.upcoming.length ? <p className="text-sm text-ink-500">Nothing in the next 7 days.</p> : p.upcoming.map((t) => (
              <div key={t.id} className="flex items-center gap-3 text-sm"><span className="w-14 shrink-0 text-xs font-bold text-ink-400">{fmtShort(t.date)}</span><i className={cn("h-2 w-2 rounded-full", CAT[t.category].dot)} /><span className="flex-1 truncate font-medium">{t.title}</span><span className="text-xs text-ink-400">{hm(t.est_minutes)}</span></div>))}
          </Card>
        </div>

        <div className="space-y-5">
          <Card className="space-y-3 p-5">
            <h3 className="flex items-center gap-2 font-extrabold text-forest-900"><Sparkles size={16} className="text-brand-600" />Recommended next actions</h3>
            {d.recommendations.map((r) => (
              <div key={r.id} className="rounded-xl border border-line bg-sage-50/60 p-3">
                <p className="text-sm font-bold">{r.title}</p>
                <p className="mt-0.5 text-xs text-ink-500"><b>Why:</b> {r.reason}</p>
                <div className="mt-2 flex items-center gap-2"><Link to={route(r.action)}><Button size="sm" icon={<ArrowRight size={14} />}>Go</Button></Link>
                  {!voted[r.id] ? <><button aria-label="Helpful" onClick={() => vote(r, true)} className="rounded-lg p-1.5 text-ink-400 hover:bg-white hover:text-emerald-600"><ThumbsUp size={15} /></button><button aria-label="Not helpful" onClick={() => vote(r, false)} className="rounded-lg p-1.5 text-ink-400 hover:bg-white hover:text-rose-600"><ThumbsDown size={15} /></button></> : <span className="text-[11px] font-semibold text-ink-400">Thanks!</span>}</div>
              </div>))}
          </Card>
          <Card className="space-y-3 p-5">
            <h3 className="flex items-center gap-2 font-extrabold text-forest-900"><Trophy size={16} className="text-amber-500" />Recent quizzes</h3>
            {!d.recent_quizzes.length ? <p className="text-sm text-ink-500">No quizzes yet. <Link className="font-bold text-brand-700 underline" to="/app/learning/quizzes">Take one</Link>.</p> : d.recent_quizzes.map((q) => (
              <Link key={q.id} to={`/app/learning/quizzes?result=${q.id}`} className="flex items-center gap-3 text-sm hover:text-brand-700"><span className="flex-1 truncate font-medium">{q.topic}</span><Badge tone={(q.accuracy ?? 0) >= 75 ? "brand" : (q.accuracy ?? 0) >= 50 ? "warn" : "danger"}>{Math.round(q.accuracy ?? 0)}%</Badge></Link>))}
          </Card>
          <Card className="space-y-3 p-5">
            <h3 className="font-extrabold text-forest-900">Weak topics</h3>
            {!d.weak_topics.length ? <p className="text-sm text-ink-500">Nothing flagged. Quiz results will show where to focus.</p> : d.weak_topics.map((w) => (
              <Link key={w.topic} to={`/app/learning/quizzes?topic=${encodeURIComponent(w.topic)}`} className="flex items-center gap-3 text-sm"><span className="flex-1 truncate font-medium">{w.topic}</span><span className={cn("rounded-full px-2 py-0.5 text-[11px] font-bold", STATUS_STYLE[w.status])}>{w.status_label}</span><span className="w-9 text-right text-xs font-bold text-ink-500">{Math.round(w.mastery)}%</span></Link>))}
            {d.upcoming_revisions.length ? <div className="border-t border-line pt-3"><p className="text-xs font-extrabold uppercase tracking-wide text-ink-400">Upcoming revisions</p>{d.upcoming_revisions.slice(0, 4).map((r) => <p key={r.topic} className="mt-1 flex justify-between text-sm"><span className="truncate">{r.topic}</span><span className="text-xs text-ink-500">{fmtShort(r.due)}</span></p>)}</div> : null}
          </Card>
        </div>
      </div>
    </div>
  );
}
