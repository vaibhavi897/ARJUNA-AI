/** My Learning Planner: create a plan, then live in the calendar. */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertTriangle, CalendarClock, CalendarPlus, Loader2, RefreshCw, Settings2, Sparkles, Target, Wand2 } from "lucide-react";
import { Badge, Button, Card, EmptyState, ErrorState, InlineNote, Modal, ProgressBar } from "../../components/ui";
import { Calendar, CalendarHeader, Legend, type CalView } from "../../components/learning/Calendar";
import { DayPanel } from "../../components/learning/DayPanel";
import { CAT, Skeleton, addDays, fmtShort, iso, parse, todayIso, useLoad } from "../../components/learning/shared";
import { lh, type Day, type Plan, type Task } from "../../lib/learning";
import { useToast } from "../../lib/auth";
import { cn } from "../../lib/utils";

const DURATIONS = [30, 60, 90, 100, 120, 180];
const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const FILTERS = [["all", "All tasks"], ["pending", "Pending"], ["completed", "Completed"], ["revision", "Revision"], ["assessments", "Assessments"], ["missed", "Missed"]] as const;
const MESSAGES = ["Reading your profile and finding your starting level…", "Building the Foundation phase…", "Designing the Intermediate phase…", "Planning Advanced topics and projects…", "Scheduling every day around your availability…", "Placing revision, assessments and milestones…"];

const split = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

// ------------------------------------------------------------------ wizard
function Wizard({ onDone, onCancel }: { onDone: (p: Plan) => void; onCancel?: () => void }) {
  const { push } = useToast();
  const tracks = useLoad(() => lh.tracks(), []);
  const [track, setTrack] = useState("backend-developer");
  const [role, setRole] = useState("Backend Developer");
  const [days, setDays] = useState(100);
  const [custom, setCustom] = useState("");
  const [hours, setHours] = useState(2);
  const [study, setStudy] = useState<number[]>([0, 1, 2, 3, 4]);
  const [start, setStart] = useState(todayIso());
  const [know, setKnow] = useState("");
  const [skip, setSkip] = useState("");
  const [focus, setFocus] = useState("");
  const [companies, setCompanies] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [gap, setGap] = useState<Awaited<ReturnType<typeof lh.skillGap>> | null>(null);
  const [gapBusy, setGapBusy] = useState(false);

  useEffect(() => { if (!busy) return; const id = setInterval(() => setMsg((m) => Math.min(m + 1, MESSAGES.length - 1)), 7000); return () => clearInterval(id); }, [busy]);
  const total = custom ? Number(custom) : days;
  const valid = role.trim().length >= 2 && total >= 7 && total <= 365 && study.length > 0 && hours >= 0.5 && hours <= 12;
  const studyDays = Math.round((total / 7) * study.length);

  async function analyse() {
    setGapBusy(true);
    try { setGap(await lh.skillGap(track, role)); } catch (e) { push({ title: "Skill gap unavailable", description: (e as Error).message, variant: "error" }); } finally { setGapBusy(false); }
  }
  async function submit() {
    setBusy(true); setError(null); setMsg(0);
    try {
      const plan = await lh.createPlan({ target_role: role.trim(), track_slug: track || null, duration_days: total, daily_hours: hours, study_days: study, start_date: start, existing_knowledge: know || null, skip_topics: split(skip), focus_areas: split(focus), target_companies: split(companies) });
      push({ title: "Your plan is ready", description: `${total} days built around ${study.length} study days a week.`, variant: "success" });
      onDone(plan);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <Card className="overflow-hidden p-0">
      <div className="relative overflow-hidden bg-gradient-to-br from-forest-900 via-forest-800 to-[#12305A] px-6 py-7 text-white sm:px-8">
        <span className="cv-blob" style={{ right: -40, top: -60, width: 260, height: 260, background: "#34D399" }} />
        <h2 className="relative font-display text-2xl font-extrabold !text-white sm:text-3xl">Design your learning journey</h2>
        <p className="relative mt-1 max-w-2xl text-sm text-white/75">Tell us the goal and your real availability. Gemini reads your existing profile and writes a roadmap for <i>your</i> starting level; ARJUNA schedules it so no day is overloaded.</p>
      </div>
      {busy ? (
        <div className="grid place-items-center px-6 py-16 text-center" role="status" aria-live="polite">
          <Loader2 className="animate-spin text-brand-600" size={36} />
          <p className="mt-4 text-lg font-extrabold text-forest-900">Generating your {total}-day roadmap</p>
          <p key={msg} className="cv-rise mt-1 text-sm text-ink-500">{MESSAGES[msg]}</p>
          <p className="mt-6 max-w-sm text-xs text-ink-400">This usually takes 20–90 seconds. Nothing is saved unless the whole plan is generated successfully.</p>
        </div>
      ) : (
        <div className="grid gap-6 p-6 sm:p-8 lg:grid-cols-2">
          <div className="space-y-5">
            <label className="block text-sm font-bold">Career track
              <select value={track} onChange={(e) => { setTrack(e.target.value); const t = tracks.data?.items.find((x) => x.slug === e.target.value); if (t) setRole(t.title); setGap(null); }} className="input-base mt-1.5" aria-label="Career track">
                {tracks.data?.items.map((t) => <option key={t.slug} value={t.slug}>{t.title} ({t.category})</option>)}
              </select>
            </label>
            <label className="block text-sm font-bold">Target role<input value={role} onChange={(e) => setRole(e.target.value)} maxLength={160} className="input-base mt-1.5" placeholder="e.g. Backend Developer at a fintech" /></label>
            <div><p className="text-sm font-bold">How long do you want to learn?</p>
              <div className="mt-2 flex flex-wrap gap-2" role="radiogroup" aria-label="Duration in days">
                {DURATIONS.map((d) => <button key={d} role="radio" aria-checked={!custom && days === d} onClick={() => { setDays(d); setCustom(""); }} className={cn("rounded-xl border px-4 py-2 text-sm font-extrabold transition", !custom && days === d ? "border-forest-800 bg-forest-800 text-white shadow" : "border-line-strong bg-white hover:border-brand-400")}>{d} days</button>)}
                <input type="number" min={7} max={365} value={custom} onChange={(e) => setCustom(e.target.value)} placeholder="Custom" aria-label="Custom number of days" className={cn("input-base h-10 w-28", custom && "ring-2 ring-brand-500")} />
              </div></div>
            <div className="grid grid-cols-2 gap-4">
              <label className="block text-sm font-bold">Hours per study day<input type="number" step={0.5} min={0.5} max={12} value={hours} onChange={(e) => setHours(Number(e.target.value))} className="input-base mt-1.5" /></label>
              <label className="block text-sm font-bold">Start date<input type="date" min={iso(addDays(new Date(), -1))} value={start} onChange={(e) => setStart(e.target.value)} className="input-base mt-1.5" /></label>
            </div>
            <div><p className="text-sm font-bold">Preferred study days</p>
              <div className="mt-2 flex gap-1.5" role="group" aria-label="Study days">
                {WEEKDAYS.map((d, i) => <button key={d} aria-pressed={study.includes(i)} onClick={() => setStudy((s) => (s.includes(i) ? s.filter((x) => x !== i) : [...s, i]))} className={cn("h-11 flex-1 rounded-xl border text-xs font-extrabold transition", study.includes(i) ? "border-brand-600 bg-brand-600 text-white" : "border-line-strong bg-white text-ink-500 hover:border-brand-400")}>{d}</button>)}
              </div>
              <p className="mt-2 text-xs text-ink-500">≈ {studyDays} study days, about {Math.round(studyDays * hours)} hours in total. Revision, weekly assessments and a final assessment are reserved automatically.</p>
            </div>
          </div>
          <div className="space-y-5">
            <label className="block text-sm font-bold">What do you already know?<textarea value={know} onChange={(e) => setKnow(e.target.value)} rows={3} maxLength={1500} className="input-base mt-1.5" placeholder="Optional. Your profile is already used; add anything it does not show." /></label>
            <label className="block text-sm font-bold">Topics to skip<input value={skip} onChange={(e) => setSkip(e.target.value)} className="input-base mt-1.5" placeholder="Comma separated, e.g. Git and Linux Basics" /></label>
            <label className="block text-sm font-bold">Focus areas<input value={focus} onChange={(e) => setFocus(e.target.value)} className="input-base mt-1.5" placeholder="e.g. System design, SQL performance" /></label>
            <label className="block text-sm font-bold">Target companies <span className="font-normal text-ink-400">(optional)</span><input value={companies} onChange={(e) => setCompanies(e.target.value)} className="input-base mt-1.5" placeholder="e.g. Razorpay, Flipkart" /></label>
            <div className="rounded-2xl border border-line bg-sage-50 p-4">
              <div className="flex items-center justify-between gap-2"><p className="flex items-center gap-2 text-sm font-extrabold"><Target size={16} className="text-brand-600" />Skill-gap preview</p>
                <Button size="sm" variant="outline" loading={gapBusy} onClick={analyse} icon={<Wand2 size={14} />}>{gap ? "Re-analyse" : "Analyse my profile"}</Button></div>
              {gap ? (
                <div className="cv-rise mt-3 space-y-2 text-sm">
                  <p><Badge tone="brand">{gap.starting_level}</Badge> <span className="text-ink-600">{gap.explanation.summary}</span></p>
                  {!gap.profile_has_data ? <InlineNote tone="warn">Your profile has no skills, projects or resume data yet, so everything starts from the beginning. Add them in Settings to personalise the plan.</InlineNote> : null}
                  {gap.explanation.priority_gaps.length ? <p className="text-xs text-ink-500"><b>Priority gaps:</b> {gap.explanation.priority_gaps.join(", ")}</p> : null}
                  <p className="text-[11px] text-ink-400">Method: {gap.method}</p>
                </div>
              ) : <p className="mt-2 text-xs text-ink-500">Compares your existing profile, resume and skills with this track. Nothing to upload.</p>}
            </div>
          </div>
          <div className="space-y-3 lg:col-span-2">
            {error ? <ErrorState message={error} onRetry={submit} /> : null}
            <div className="flex flex-wrap items-center justify-end gap-3">
              {onCancel ? <Button variant="ghost" onClick={onCancel}>Cancel</Button> : null}
              <Button size="lg" disabled={!valid} onClick={submit} icon={<Sparkles size={18} />}>Generate my {valid ? total : ""}-day plan</Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

// ------------------------------------------------------------------ phase timeline
function Timeline({ plan, days }: { plan: Plan; days: Map<string, Day> }) {
  const total = Math.max(1, (parse(plan.end_date).getTime() - parse(plan.start_date).getTime()) / 86400000 + 1);
  const t = todayIso();
  const pos = (d: string) => Math.max(0, Math.min(100, ((parse(d).getTime() - parse(plan.start_date).getTime()) / 86400000 / total) * 100));
  const colors = ["bg-emerald-500", "bg-sky-500", "bg-violet-500", "bg-amber-500", "bg-rose-500"];
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between"><h3 className="font-extrabold text-forest-900">Roadmap timeline</h3><span className="text-xs text-ink-500">{fmtShort(plan.start_date)} → {fmtShort(plan.end_date)}</span></div>
      <div className="relative mt-5 h-14" aria-label="Learning phases timeline">
        {plan.phases.map((p, i) => {
          const l = pos(p.start), r = pos(p.end) + 100 / total;
          const phaseDays = [...days.values()].filter((d) => d.date >= p.start && d.date <= p.end && !d.rest);
          const done = phaseDays.reduce((s, d) => s + d.done, 0), tot = phaseDays.reduce((s, d) => s + d.total, 0);
          return (
            <div key={p.key} className="absolute top-0 h-9 overflow-hidden rounded-lg" style={{ left: `${l}%`, width: `${Math.max(2, r - l)}%` }} title={`${p.title}: ${fmtShort(p.start)}–${fmtShort(p.end)} · ${done}/${tot} done`}>
              <div className={cn("h-full w-full opacity-25", colors[i % 5])} />
              <div className={cn("absolute inset-y-0 left-0", colors[i % 5])} style={{ width: `${tot ? (100 * done) / tot : 0}%` }} />
              <span className="absolute inset-0 grid place-items-center truncate px-1 text-[11px] font-extrabold text-forest-900">{p.title}</span>
            </div>
          );
        })}
        {plan.milestones.map((m) => <div key={m.id} title={`${m.title} · ${fmtShort(m.due)}`} className={cn("absolute top-10 h-3 w-3 -translate-x-1/2 rotate-45 rounded-[2px]", m.completed ? "bg-fuchsia-600" : "bg-fuchsia-300")} style={{ left: `${pos(m.due)}%` }} />)}
        {t >= plan.start_date && t <= plan.end_date ? <div className="absolute -top-2 bottom-0 w-0.5 bg-rose-500" style={{ left: `${pos(t)}%` }}><span className="absolute -top-1 left-1 whitespace-nowrap text-[10px] font-extrabold text-rose-600">Today</span></div> : null}
      </div>
      <p className="mt-1 text-[11px] text-ink-400">◆ weekly checkpoints · hover a phase for progress</p>
    </Card>
  );
}

// ------------------------------------------------------------------ page
export default function Planner() {
  const { push } = useToast();
  const active = useLoad(() => lh.activePlan(), []);
  const [params] = useSearchParams();
  const [creating, setCreating] = useState(params.get("new") === "1");
  const plan = active.data?.plan ?? null;

  if (active.loading && !active.data) return <div className="space-y-4"><Skeleton className="h-32" /><Skeleton className="h-96" /></div>;
  if (active.error) return <ErrorState message={active.error} onRetry={active.reload} />;
  if (!plan || creating) return <Wizard onCancel={plan ? () => setCreating(false) : undefined} onDone={(p) => { active.setData({ plan: p }); setCreating(false); }} />;
  return <PlanView key={plan.id} plan={plan} deepLink={{ date: params.get("date"), missed: params.get("missed") === "1" }} onPlan={(p) => active.setData({ plan: p })} onNew={() => setCreating(true)} toast={push} />;
}

function PlanView({ plan, onPlan, onNew, toast, deepLink }: { deepLink: { date: string | null; missed: boolean }; plan: Plan; onPlan: (p: Plan) => void; onNew: () => void; toast: ReturnType<typeof useToast>["push"] }) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number][0]>("all");
  const [view, setView] = useState<CalView>("month");
  const initial = deepLink.date && deepLink.date >= plan.start_date && deepLink.date <= plan.end_date ? parse(deepLink.date) : todayIso() >= plan.start_date && todayIso() <= plan.end_date ? new Date() : parse(plan.start_date);
  const [cursor, setCursor] = useState(initial);
  const [selected, setSelected] = useState<string | null>(iso(initial));
  const [days, setDays] = useState<Map<string, Day>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<null | "availability" | "regenerate" | "missed" | "gap">(deepLink.missed ? "missed" : null);

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await lh.calendar(plan.id, plan.start_date, plan.end_date, filter); setDays(new Map(r.days.map((d) => [d.date, d]))); setError(null); }
    catch (e) { setError((e as Error).message); } finally { setLoading(false); }
  }, [plan.id, plan.start_date, plan.end_date, filter]);
  useEffect(() => { load(); }, [load]);

  const stats = useMemo(() => {
    let done = 0, total = 0, missed = 0;
    days.forEach((d) => d.tasks.forEach((t) => { if (t.category === "rest") return; total += 1; if (t.status === "completed") done += 1; if (t.missed) missed += 1; }));
    return { done, total, missed };
  }, [days]);
  // stats should reflect ALL tasks, not the filtered view
  const [overall, setOverall] = useState({ done: 0, total: 0, missed: 0 });
  useEffect(() => { lh.calendar(plan.id, plan.start_date, plan.end_date, "all").then((r) => { let d = 0, t = 0, m = 0; r.days.forEach((x) => x.tasks.forEach((k) => { if (k.category === "rest") return; t++; if (k.status === "completed") d++; if (k.missed) m++; })); setOverall({ done: d, total: t, missed: m }); }).catch(() => undefined); }, [plan.id, plan.version, days]);
  void stats;

  function onTask(t: Task) {
    // optimistic local update, then re-fetch the truth (the task may have moved dates or left the active filter)
    setDays((prev) => {
      const next = new Map<string, Day>();
      prev.forEach((d, k) => next.set(k, { ...d, tasks: d.tasks.filter((x) => x.id !== t.id) }));
      const d = next.get(t.date);
      if (d) next.set(t.date, { ...d, tasks: [...d.tasks, t].sort((a, b) => a.position - b.position) });
      return next;
    });
    load();
  }

  const pct = overall.total ? Math.round((100 * overall.done) / overall.total) : 0;
  const sel = selected ? days.get(selected) : undefined;
  const nextDay = selected ? [...days.values()].find((d) => d.date > selected && d.tasks.some((t) => t.category !== "rest")) : undefined;
  const g = plan.goal;

  return (
    <div className="space-y-5">
      <Card className="overflow-hidden p-0">
        <div className="relative bg-gradient-to-r from-forest-900 to-forest-700 px-6 py-5 text-white">
          <div className="flex flex-wrap items-center gap-4">
            <div className="min-w-[240px] flex-1">
              <p className="text-[11px] font-extrabold uppercase tracking-[0.2em] text-emerald-300">Active goal</p>
              <h2 className="font-display text-2xl font-extrabold !text-white">{g.target_role}</h2>
              <p className="text-sm text-white/70">{g.duration_days} days · {fmtShort(plan.start_date)} → {fmtShort(plan.end_date)} · {g.daily_hours}h on {g.study_days.map((d) => WEEKDAYS[d]).join(", ")} · starting level <b className="capitalize">{plan.starting_level}</b></p>
            </div>
            <div className="w-full max-w-xs"><div className="flex justify-between text-xs font-bold text-white/80"><span>{overall.done}/{overall.total} tasks</span><span>{pct}%</span></div><div className="mt-1 h-2.5 overflow-hidden rounded-full bg-white/20"><div className="h-full rounded-full bg-gradient-to-r from-emerald-300 to-emerald-500 transition-all duration-700" style={{ width: `${pct}%` }} /></div></div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" icon={<Settings2 size={14} />} onClick={() => setModal("availability")}>Availability & breaks</Button>
            <Button size="sm" variant="secondary" icon={<RefreshCw size={14} />} onClick={() => setModal("regenerate")}>Regenerate future</Button>
            <Button size="sm" variant="secondary" icon={<Target size={14} />} onClick={() => setModal("gap")}>Skill gap</Button>
            <Button size="sm" variant="secondary" icon={<CalendarPlus size={14} />} onClick={onNew}>New plan</Button>
          </div>
        </div>
        {overall.missed > 0 ? (
          <div className="flex flex-wrap items-center gap-3 border-t border-rose-200 bg-rose-50 px-6 py-3 text-sm text-rose-800">
            <AlertTriangle size={16} /><span className="flex-1 font-semibold">{overall.missed} task{overall.missed > 1 ? "s" : ""} missed. Preview how they could be spread across your remaining days.</span>
            <Button size="sm" variant="outline" icon={<CalendarClock size={14} />} onClick={() => setModal("missed")}>Review & reschedule</Button>
          </div>
        ) : null}
      </Card>

      <Timeline plan={plan} days={days} />

      <Card className="space-y-4 p-5">
        <CalendarHeader view={view} onView={(v) => { setView(v); if (v === "day" && !selected) setSelected(iso(cursor)); }} cursor={view === "day" && selected ? parse(selected) : cursor} onCursor={(d) => { setCursor(d); if (view === "day") setSelected(iso(d)); }} />
        <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Task filter">
          {FILTERS.map(([k, label]) => <button key={k} aria-pressed={filter === k} onClick={() => setFilter(k)} className={cn("rounded-full border px-3.5 py-1.5 text-xs font-bold transition", filter === k ? "border-forest-800 bg-forest-800 text-white" : "border-line-strong bg-white text-ink-600 hover:border-brand-400")}>{label}</button>)}
        </div>
        <Legend />
        {error ? <ErrorState message={error} onRetry={load} /> : null}
        {loading && days.size === 0 ? <Skeleton className="h-96" /> : null}
        {!loading && !error && filter !== "all" && ![...days.values()].some((d) => d.tasks.length) ? <EmptyState title="Nothing matches this filter" description={filter === "missed" ? "No missed tasks. Nice work." : "Try another filter."} /> : null}
        {view !== "day" ? <Calendar view={view} cursor={cursor} days={days} planStart={plan.start_date} planEnd={plan.end_date} selected={selected} onSelect={(d) => setSelected(d)} /> : null}
      </Card>

      {selected && selected >= plan.start_date && selected <= plan.end_date ? (
        <div className="cv-rise"><DayPanel date={selected} day={sel} next={nextDay} planStart={plan.start_date} planEnd={plan.end_date} onChange={onTask} onPick={(d) => { setSelected(d); setCursor(parse(d)); }} /></div>
      ) : selected ? <InlineNote>That date is outside your plan ({fmtShort(plan.start_date)} – {fmtShort(plan.end_date)}).</InlineNote> : null}

      <AvailabilityModal open={modal === "availability"} plan={plan} onClose={() => setModal(null)} onPlan={(p) => { onPlan(p); load(); }} toast={toast} />
      <RegenerateModal open={modal === "regenerate"} plan={plan} onClose={() => setModal(null)} onPlan={(p) => { onPlan(p); load(); }} toast={toast} />
      <MissedModal open={modal === "missed"} plan={plan} onClose={() => setModal(null)} onDone={load} toast={toast} />
      <Modal open={modal === "gap"} onClose={() => setModal(null)} title="Your skill gap" description={plan.skill_gap.method} size="lg">
        <div className="space-y-3 text-sm">
          <p className="text-ink-700">{plan.skill_gap.explanation?.summary ?? plan.summary}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl bg-emerald-50 p-3"><p className="font-bold text-emerald-800">Already supported ({plan.skill_gap.matched_titles?.length ?? 0})</p><p className="mt-1 text-xs text-ink-600">{(plan.skill_gap.matched_titles ?? []).slice(0, 14).join(", ") || "Nothing evidenced yet."}</p></div>
            <div className="rounded-xl bg-amber-50 p-3"><p className="font-bold text-amber-800">To learn ({plan.skill_gap.missing_titles?.length ?? 0})</p><p className="mt-1 text-xs text-ink-600">{(plan.skill_gap.missing_titles ?? []).slice(0, 14).join(", ")}</p></div>
          </div>
          {plan.skill_gap.dropped_units?.length ? <InlineNote tone="warn">To keep days realistic, {plan.skill_gap.dropped_units.length} unit(s) did not fit your timeframe: {plan.skill_gap.dropped_units.slice(0, 5).join(", ")}.</InlineNote> : null}
        </div>
      </Modal>
    </div>
  );
}

// ------------------------------------------------------------------ modals
function AvailabilityModal({ open, plan, onClose, onPlan, toast }: { open: boolean; plan: Plan; onClose: () => void; onPlan: (p: Plan) => void; toast: ReturnType<typeof useToast>["push"] }) {
  const [study, setStudy] = useState(plan.goal.study_days);
  const [hours, setHours] = useState(plan.goal.daily_hours);
  const [breaks, setBreaks] = useState(plan.goal.breaks);
  const [bs, setBs] = useState(""); const [be, setBe] = useState("");
  const [busy, setBusy] = useState(false);
  const adj = useLoad(() => (open ? lh.adjustments(plan.id) : Promise.resolve(null)), [open]);
  async function save() {
    setBusy(true);
    try { const r = await lh.availability(plan.id, { study_days: study, daily_hours: hours, breaks }); onPlan(r.plan); toast({ title: "Availability updated", description: "Completed work was kept; open future days were re-planned.", variant: "success" }); onClose(); }
    catch (e) { toast({ title: "Could not update", description: (e as Error).message, variant: "error" }); } finally { setBusy(false); }
  }
  return (
    <Modal open={open} onClose={onClose} title="Availability & breaks" description="Completed, partial and pinned work is never touched. Only open future days are re-planned." size="lg"
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={save} disabled={!study.length}>Save and re-plan</Button></>}>
      <div className="space-y-4">
        <div className="flex gap-1.5" role="group" aria-label="Study days">{WEEKDAYS.map((d, i) => <button key={d} aria-pressed={study.includes(i)} onClick={() => setStudy((s) => (s.includes(i) ? s.filter((x) => x !== i) : [...s, i].sort()))} className={cn("h-10 flex-1 rounded-xl border text-xs font-extrabold", study.includes(i) ? "border-brand-600 bg-brand-600 text-white" : "border-line-strong bg-white text-ink-500")}>{d}</button>)}</div>
        <label className="block text-sm font-bold">Hours per study day<input type="number" step={0.5} min={0.5} max={12} value={hours} onChange={(e) => setHours(Number(e.target.value))} className="input-base mt-1.5 w-32" /></label>
        <div><p className="text-sm font-bold">Take a break</p>
          <div className="mt-1.5 flex flex-wrap items-end gap-2"><input type="date" value={bs} onChange={(e) => setBs(e.target.value)} className="input-base w-40" aria-label="Break start" /><input type="date" value={be} min={bs} onChange={(e) => setBe(e.target.value)} className="input-base w-40" aria-label="Break end" />
            <Button size="sm" variant="outline" disabled={!bs || !be || be < bs} onClick={() => { setBreaks([...breaks, { start: bs, end: be, reason: "Break" }]); setBs(""); setBe(""); }}>Add break</Button></div>
          <ul className="mt-2 space-y-1">{breaks.map((b, i) => <li key={i} className="flex items-center justify-between rounded-lg bg-sage-50 px-3 py-1.5 text-sm">{fmtShort(b.start)} – {fmtShort(b.end)}<button className="text-xs font-bold text-rose-600" onClick={() => setBreaks(breaks.filter((_, k) => k !== i))}>Remove</button></li>)}</ul></div>
        {adj.data?.notes?.length ? <InlineNote tone="brand"><b>Based on your recent pace:</b><ul className="mt-1 list-disc pl-4">{adj.data.notes.map((n) => <li key={n}>{n}</li>)}</ul>{adj.data.suggested_daily_factor && adj.data.suggested_daily_factor !== 1 ? <button className="mt-2 text-xs font-extrabold underline" onClick={() => setHours(Math.max(0.5, Math.round(plan.goal.daily_hours * adj.data!.suggested_daily_factor! * 2) / 2))}>Apply suggested hours</button> : null}</InlineNote> : null}
      </div>
    </Modal>
  );
}

function RegenerateModal({ open, plan, onClose, onPlan, toast }: { open: boolean; plan: Plan; onClose: () => void; onPlan: (p: Plan) => void; toast: ReturnType<typeof useToast>["push"] }) {
  const [busy, setBusy] = useState(false);
  async function go() {
    setBusy(true);
    try { const r = await lh.regenerate(plan.id); onPlan(r.plan); toast({ title: "Future plan regenerated", description: `${r.replaced} open tasks replaced with ${r.created} new ones. ${r.kept} completed or pinned items were kept.`, variant: "success" }); onClose(); }
    catch (e) { toast({ title: "Could not regenerate", description: (e as Error).message, variant: "error" }); } finally { setBusy(false); }
  }
  return (
    <Modal open={open} onClose={onClose} title="Regenerate the rest of your plan?" description="Gemini rewrites only the open future days, using your completion pattern and weak topics." size="md"
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={go} icon={<RefreshCw size={15} />}>Regenerate future</Button></>}>
      <ul className="list-disc space-y-1 pl-5 text-sm text-ink-700"><li>Completed, partial, skipped and pinned tasks stay exactly as they are.</li><li>Pending tasks from tomorrow onwards are replaced.</li><li>Your deadline ({fmtShort(plan.end_date)}) does not move.</li></ul>
    </Modal>
  );
}

function MissedModal({ open, plan, onClose, onDone, toast }: { open: boolean; plan: Plan; onClose: () => void; onDone: () => void; toast: ReturnType<typeof useToast>["push"] }) {
  const pv = useLoad(() => (open ? lh.missed(plan.id) : Promise.resolve(null)), [open]);
  const [busy, setBusy] = useState(false);
  async function apply() {
    setBusy(true);
    try { const r = await lh.applyMissed(plan.id, true); toast({ title: `Rescheduled ${r.moved} task${r.moved === 1 ? "" : "s"}`, variant: "success" }); onDone(); onClose(); }
    catch (e) { toast({ title: "Could not reschedule", description: (e as Error).message, variant: "error" }); } finally { setBusy(false); }
  }
  const d = pv.data;
  return (
    <Modal open={open} onClose={onClose} title="Missed tasks" description="Nothing changes until you confirm." size="lg"
      footer={<><Button variant="ghost" onClick={onClose}>Not now</Button><Button loading={busy} onClick={apply} disabled={!d || !d.moves.length}>Move {d?.moves.length ?? 0} task(s)</Button></>}>
      {pv.loading ? <Skeleton className="h-40" /> : pv.error ? <ErrorState message={pv.error} onRetry={pv.reload} /> : d ? (
        <div className="space-y-3 text-sm">
          <p className="font-semibold text-ink-700">{d.message}</p>
          {d.significant ? <InlineNote tone="warn">This is a significant change. Review the list before confirming.</InlineNote> : null}
          <ul className="max-h-64 space-y-1 overflow-y-auto">{d.moves.map((m) => <li key={m.task_id} className="flex items-center justify-between gap-3 rounded-lg bg-sage-50 px-3 py-2"><span className="truncate font-medium">{m.title}</span><span className="shrink-0 text-xs font-bold text-ink-500">{fmtShort(m.from)} → <span className="text-brand-700">{fmtShort(m.to)}</span></span></li>)}</ul>
          {d.overflow.length ? <InlineNote tone="warn"><b>Will not fit before your deadline:</b> {d.overflow.map((o) => o.title).join(", ")}. Add study time, extend your availability, or skip them.</InlineNote> : null}
        </div>
      ) : null}
    </Modal>
  );
}
