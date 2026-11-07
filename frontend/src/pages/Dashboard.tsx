/**
 * Student dashboard. Every value shown here comes from the /api/dashboard
 * response, which is computed from the signed-in student's own rows.
 */
import SkillMap from "../components/SkillMap";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Compass,
  AlertTriangle,
  Activity as ActivityIcon,
  Award,
  BarChart3,
  Brain,
  Briefcase,
  CheckCircle2,
  ChevronRight,
  Circle,
  Clock,
  ExternalLink,
  FileText,
  FolderGit2,
  GaugeCircle,
  GraduationCap,
  Info,
  LineChart as LineChartIcon,
  ListChecks,
  RefreshCw,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  Trophy,
  Zap,
} from "lucide-react";
import {
  CategoryBars,
  DomainAverageBars,
  OverallTrend,
  RoleScoreBars,
  ScoreHistoryChart,
  SkillComparisonBars,
  SkillRadar,
} from "../components/charts";
import { AppShell } from "../components/layout";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  InlineNote,
  LoadingBlock,
  Modal,
  PageLoader,
  ProgressBar,
  ScoreRing,
  SectionHeader,
  Tabs,
} from "../components/ui";
import { ApiError, api, type Dashboard as DashboardData, type RoleDetail } from "../lib/api";
import { useToast } from "../lib/auth";
import {
  bandColor,
  cn,
  formatDateTime,
  gapStatusLabel,
  monthsToText,
  priorityStyles,
  relativeTime,
  scoreTone,
  severityStyles,
  titleCase,
} from "../lib/utils";

export default function Dashboard() {
  const { push } = useToast();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [openRole, setOpenRole] = useState<string | null>(null);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [detail, setDetail] = useState<RoleDetail | null>(null);
  const [savingTask, setSavingTask] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const payload = await api.dashboard();
      setData(payload);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load your dashboard.");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);


  const activeSlug = useMemo(() => {
    const r = data?.readiness;
    if (!r) return null;
    const pool = r.preferred_roles.length ? r.preferred_roles : r.roles;
    const sorted = pool.slice().sort((x, y) => y.score - x.score).slice(0, 6);
    return (sorted.find((x) => x.role_slug === selectedSlug) ?? sorted.find((x) => x.is_primary) ?? sorted[0])?.role_slug ?? null;
  }, [data, selectedSlug]);

  useEffect(() => {
    if (!activeSlug) return;
    let live = true;
    api.roleDetail(activeSlug).then((d) => live && setDetail(d)).catch(() => live && setDetail(null));
    return () => { live = false; };
  }, [activeSlug]);

  const recalculate = async () => {
    setRefreshing(true);
    try {
      const result = await api.recalculate();
      await load();
      push({
        title: "Assessment refreshed",
        description: result.message,
        variant: "success",
      });
    } catch (err) {
      push({
        title: "Could not refresh",
        description: err instanceof ApiError ? err.message : "Please try again.",
        variant: "error",
      });
    } finally {
      setRefreshing(false);
    }
  };

  const setTaskStatus = async (id: number, status: string) => {
    setSavingTask(id);
    try {
      await api.updateTask(id, status);
      await load();
    } catch (err) {
      push({
        title: "Could not update the task",
        description: err instanceof ApiError ? err.message : "Please try again.",
        variant: "error",
      });
    } finally {
      setSavingTask(null);
    }
  };

  if (error && !data) {
    return (
      <AppShell title="Student Dashboard">
        <ErrorState message={error} onRetry={load} />
      </AppShell>
    );
  }

  if (!data) {
    return (
      <AppShell title="Student Dashboard">
        <PageLoader label="Building your dashboard" />
      </AppShell>
    );
  }

  const { welcome, readiness, skills, roadmap, resume_insights, portfolio, progress } = data;
  const pendingTasks = roadmap.tasks.filter((task) => task.status !== "completed");

  const targetRoles = (readiness.preferred_roles.length ? readiness.preferred_roles : readiness.roles).slice().sort((a, b) => b.score - a.score).slice(0, 6);
  const active = targetRoles.find((r) => r.role_slug === selectedSlug) ?? targetRoles.find((r) => r.is_primary) ?? targetRoles[0];
  const gaps = (detail?.skill_gaps ?? skills.role_gaps).slice(0, 5);
  const strengths = (detail?.strengths ?? data.strengths).slice(0, 3);
  const improvements = (detail?.improvements ?? data.improvements).slice(0, 3);
  const nextTasks = pendingTasks.slice(0, 4);
  const trend = progress.overall_series;
  const delta = trend.length > 1 ? Math.round(trend[trend.length - 1].score - trend[0].score) : null;
  const firstName = welcome.full_name?.split(" ")[0] ?? "there";
  const resumeFixes = resume_insights.improvements.slice(0, 3);

  return (
    <AppShell
      title="Student Dashboard"
      subtitle={`Last assessed ${welcome.last_assessment_at ? relativeTime(welcome.last_assessment_at) : "never"}`}
      actions={
        <Button size="sm" variant="outline" loading={refreshing} onClick={recalculate} icon={<RefreshCw size={14} />}>
          Re-assess
        </Button>
      }
    >
      <div className="space-y-4">
        {/* 1. Greeting: one short line */}
        <div className="rounded-2xl bg-gradient-to-r from-brand-600 to-emerald-400 px-5 py-3.5 text-white shadow-card">
          <p className="text-base font-bold sm:text-lg">
            Hi {firstName}, {readiness.has_assessments && active ? `you are ${Math.round(active.score)}/100 ready for ${active.role_name}.` : "run your first assessment to see how ready you are."}
          </p>
        </div>

        {!readiness.has_assessments ? (
          <EmptyState icon={<GaugeCircle size={18} />} title="No assessment yet" description="Run an assessment to generate your role-wise readiness scores."
            action={<Button loading={refreshing} onClick={recalculate} icon={<Sparkles size={15} />}>Run my first assessment</Button>} />
        ) : (
          <>
            {/* 2 + 3. Overall readiness (prominent) and best domains (top 3) */}
            <div className="grid gap-4 lg:grid-cols-12">
              <Card className="flex flex-col items-center justify-center p-5 lg:col-span-5">
                <p className="section-label mb-2">Overall readiness</p>
                <ScoreRing score={readiness.overall_score ?? 0} label={readiness.overall_band ?? ""} sublabel={`${readiness.preferred_roles.length ? "target" : "scored"} roles`} />
              </Card>
              <Card className="p-5 lg:col-span-7">
                <h3 className="flex items-center gap-2 text-base font-extrabold text-forest-900"><Compass size={16} className="text-brand-600" />Best matching domains</h3>
                <ul className="mt-4 space-y-4">
                  {readiness.domain_averages.slice(0, 3).map((d) => (
                    <li key={d.domain_slug}>
                      <div className="mb-1.5 flex items-baseline justify-between gap-2">
                        <span className="truncate text-sm font-semibold text-ink-800">{d.domain_name}</span>
                        <span className="text-sm font-extrabold tabular-nums" style={{ color: scoreTone(d.average_score) }}>{Math.round(d.average_score)}</span>
                      </div>
                      <ProgressBar value={d.average_score} size="sm" />
                    </li>
                  ))}
                </ul>
              </Card>
            </div>

            {/* 4 + 5. Target role readiness (one copy) and strengths/improvements for the selected role */}
            <div className="grid gap-4 lg:grid-cols-12">
              <Card className="p-4 lg:col-span-7">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="flex items-center gap-2 text-base font-extrabold text-forest-900"><Target size={16} className="text-brand-600" />{readiness.preferred_roles.length ? "Target role readiness" : "Role readiness"}</h3>
                  <button className="text-xs font-bold text-brand-700 hover:underline" onClick={() => active && setOpenRole(active.role_slug)}>Full breakdown</button>
                </div>
                <ul className="mt-3 space-y-1.5">
                  {targetRoles.map((r) => {
                    const on = r.role_slug === active?.role_slug;
                    return (
                      <li key={r.role_slug}>
                        <button onClick={() => setSelectedSlug(r.role_slug)} aria-pressed={on} className={cn("w-full rounded-xl border px-3 py-2 text-left transition", on ? "border-brand-400 bg-brand-50" : "border-transparent hover:bg-brand-50/60")}>
                          <div className="flex items-baseline justify-between gap-3">
                            <span className="truncate text-sm font-semibold text-ink-800">{r.role_name}</span>
                            <span className="flex shrink-0 items-center gap-2 text-sm font-extrabold tabular-nums" style={{ color: scoreTone(r.score) }}>
                              {r.score_delta ? <span className={cn("text-[11px] font-bold", r.score_delta > 0 ? "text-brand-600" : "text-danger-700")}>{r.score_delta > 0 ? "+" : ""}{r.score_delta}</span> : null}
                              {Math.round(r.score)}
                            </span>
                          </div>
                          <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-brand-100"><div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.min(100, r.score)}%`, background: scoreTone(r.score) }} /></div>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </Card>

              <Card className="p-4 lg:col-span-5">
                <h3 className="flex items-center gap-2 text-base font-extrabold text-forest-900"><Sparkles size={16} className="text-brand-600" />Strengths and focus{active ? <span className="truncate text-xs font-semibold text-ink-500"> · {active.role_name}</span> : null}</h3>
                <div className="mt-3 space-y-3">
                  <div>
                    <p className="section-label mb-1.5">Strong</p>
                    <ul className="space-y-1.5">
                      {strengths.map((s: any, i: number) => <li key={i} className="flex gap-2 text-sm text-ink-700"><CheckCircle2 size={15} className="mt-0.5 shrink-0 text-brand-600" /><span>{s.title}</span></li>)}
                      {!strengths.length ? <li className="text-sm text-ink-500">Add skills and projects to reveal strengths.</li> : null}
                    </ul>
                  </div>
                  <div>
                    <p className="section-label mb-1.5">Improve first</p>
                    <ul className="space-y-1.5">
                      {improvements.map((s: any, i: number) => <li key={i} className="flex items-start justify-between gap-2 text-sm text-ink-700"><span>{s.title}</span>{s.points_at_stake ? <Badge tone="warn">{s.points_at_stake} pts</Badge> : null}</li>)}
                      {!improvements.length ? <li className="text-sm text-ink-500">Nothing urgent.</li> : null}
                    </ul>
                  </div>
                </div>
              </Card>
            </div>

            {/* 6 + 7. Skill gaps and AI roadmap */}
            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="p-4">
                <h3 className="flex items-center gap-2 text-base font-extrabold text-forest-900"><AlertTriangle size={16} className="text-warn-600" />Most important missing skills</h3>
                {gaps.length ? (
                  <ul className="mt-3 divide-y divide-line">
                    {gaps.map((g: any) => (
                      <li key={g.skill_name} className="py-2 first:pt-0 last:pb-0">
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-sm font-semibold text-ink-800">{g.skill_name}</span>
                          <Badge tone={g.status === "missing" ? "danger" : "warn"}>-{g.points_lost} pts</Badge>
                        </div>
                        <p className="mt-0.5 line-clamp-1 text-xs text-ink-500">{g.recommendation ?? `${gapStatusLabel(g.status)} · expects ${g.expected_proficiency}`}</p>
                      </li>
                    ))}
                  </ul>
                ) : <p className="mt-3 text-sm text-ink-500">No gaps found for this role.</p>}
              </Card>

              <Card className="p-4">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="flex items-center gap-2 text-base font-extrabold text-forest-900"><CheckCircle2 size={16} className="text-brand-600" />AI roadmap: do next</h3>
                  <span className="text-xs font-semibold text-ink-500">{roadmap.completed_tasks}/{roadmap.total_tasks} done</span>
                </div>
                {nextTasks.length ? (
                  <ul className="mt-3 space-y-2">
                    {nextTasks.map((task) => (
                      <li key={task.id} className="flex items-start gap-3 rounded-xl border border-line bg-brand-50/40 p-2.5">
                        <button aria-label={`Mark "${task.title}" done`} disabled={savingTask === task.id} onClick={() => setTaskStatus(task.id, "completed")} className="mt-0.5 h-5 w-5 shrink-0 rounded-full border-2 border-brand-400 transition hover:bg-brand-500" />
                        <p className="min-w-0 flex-1 text-sm font-semibold text-ink-800">{task.title}</p>
                        <span className={cn("shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase", priorityStyles(task.priority))}>{task.priority}</span>
                      </li>
                    ))}
                  </ul>
                ) : <p className="mt-3 text-sm text-ink-500">Everything on your roadmap is done. Re-assess for new actions.</p>}
              </Card>
            </div>

            {/* 8 + 9 + 10. Resume, portfolio summary, one trend chart */}
            <div className="grid gap-4 lg:grid-cols-12">
              <div className="space-y-4 lg:col-span-5">
                <Card className="p-4">
                  <h3 className="flex items-center gap-2 text-base font-extrabold text-forest-900"><FileText size={16} className="text-brand-600" />Resume insights</h3>
                  {resume_insights.has_resume ? (
                    <>
                      <p className="mt-2 text-sm text-ink-700">Score <b className="text-xl text-brand-700">{resume_insights.quality_score ?? "—"}</b>/100</p>
                      <ul className="mt-2 space-y-1">
                        {resumeFixes.map((f, i) => <li key={i} className="flex gap-2 text-xs text-ink-600"><ArrowRight size={12} className="mt-0.5 shrink-0 text-brand-600" />{f}</li>)}
                      </ul>
                    </>
                  ) : <p className="mt-2 text-sm text-ink-500">No resume uploaded yet.</p>}
                  <Link to="/app/resume-builder" className="mt-3 inline-flex items-center gap-1.5 text-sm font-bold text-brand-700 hover:underline">Build a tailored resume <ArrowRight size={14} /></Link>
                </Card>
                <Card className="p-4">
                  <h3 className="text-base font-extrabold text-forest-900">Experience summary</h3>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                    {([["Projects", portfolio.projects], ["Internships", portfolio.internships], ["Achievements", portfolio.achievements]] as const).map(([l, n]) => (
                      <div key={l} className="rounded-xl bg-brand-50 py-2.5"><p className="text-xl font-extrabold text-brand-700">{n}</p><p className="text-[11px] font-semibold text-ink-500">{l}</p></div>
                    ))}
                  </div>
                </Card>
              </div>

              <Card className="p-4 lg:col-span-7">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="flex items-center gap-2 text-base font-extrabold text-forest-900"><LineChartIcon size={16} className="text-brand-600" />Readiness over time</h3>
                  {delta !== null ? <Badge tone={delta >= 0 ? "brand" : "danger"}>{delta >= 0 ? "+" : ""}{delta} since first</Badge> : null}
                </div>
                {trend.length > 1 ? <div className="mt-3"><OverallTrend data={trend} /></div> : <p className="mt-3 text-sm text-ink-500">Re-assess after improving your profile and the trend appears here.</p>}
              </Card>
            </div>
          </>
        )}
      </div>

      <RoleDetailModal slug={openRole} onClose={() => setOpenRole(null)} />
    </AppShell>
  );
}

// ---------------------------------------------------------------------------
// Role breakdown modal
// ---------------------------------------------------------------------------
function RoleDetailModal({ slug, onClose }: { slug: string | null; onClose: () => void }) {
  const [detail, setDetail] = useState<RoleDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState("breakdown");

  useEffect(() => {
    if (!slug) {
      setDetail(null);
      return;
    }
    setDetail(null);
    setError(null);
    setTab("breakdown");
    api
      .roleDetail(slug)
      .then(setDetail)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Could not load this role breakdown.")
      );
  }, [slug]);

  const gapsByStatus = useMemo(() => {
    const groups: Record<string, RoleDetail["skill_gaps"]> = {};
    for (const gap of detail?.skill_gaps ?? []) {
      groups[gap.status] = groups[gap.status] ?? [];
      groups[gap.status].push(gap);
    }
    return groups;
  }, [detail]);

  return (
    <Modal
      open={Boolean(slug)}
      onClose={onClose}
      size="xl"
      title={detail?.role.name ?? "Role breakdown"}
      description={
        detail
          ? `${detail.role.domain_name} · assessed ${formatDateTime(detail.computed_at)} · engine v${detail.engine_version}`
          : undefined
      }
    >
      {error ? <ErrorState message={error} /> : null}
      {!detail && !error ? <LoadingBlock rows={4} /> : null}

      {detail ? (
        <div className="space-y-5">
          {/* Summary */}
          <div className="flex flex-wrap items-center gap-5 rounded-2xl border border-line bg-surface-muted p-4">
            <ScoreRing score={detail.score} size={116} label={detail.band} />
            <div className="min-w-0 flex-1 space-y-2">
              <p className="text-sm leading-relaxed text-ink-700">{detail.role.description}</p>
              <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-500">
                <span>
                  Required skills matched:{" "}
                  <strong className="text-ink-800">
                    {detail.match_summary.required_matched}/{detail.match_summary.required_total}
                  </strong>
                </span>
                <span>
                  Evidence-backed:{" "}
                  <strong className="text-ink-800">
                    {detail.match_summary.evidence_backed_skills}
                  </strong>
                </span>
                <span>
                  Relevant projects:{" "}
                  <strong className="text-ink-800">{detail.match_summary.relevant_projects}</strong>
                </span>
                <span>
                  Rubric expects:{" "}
                  <strong className="text-ink-800">
                    {detail.role.expected_projects} projects, {detail.role.expected_internships}{" "}
                    internship(s), CGPA {detail.role.min_cgpa}+
                  </strong>
                </span>
              </div>
              {detail.score_delta !== null ? (
                <p
                  className={cn(
                    "text-xs font-semibold",
                    detail.score_delta >= 0 ? "text-brand-600" : "text-danger-500"
                  )}
                >
                  {detail.score_delta >= 0 ? "+" : ""}
                  {detail.score_delta} points since the previous assessment (
                  {detail.previous_score})
                </p>
              ) : null}
            </div>
          </div>

          <Tabs
            active={tab}
            onChange={setTab}
            tabs={[
              { id: "breakdown", label: "Score breakdown", count: detail.breakdowns.length },
              { id: "skills", label: "Skills vs rubric", count: detail.skill_comparison.length },
              { id: "gaps", label: "Gaps", count: detail.skill_gaps.length },
              { id: "history", label: "History", count: detail.history.length },
            ]}
          />

          {tab === "breakdown" ? (
            <div className="space-y-2.5">
              <InlineNote tone="info" icon={<Info size={15} />}>
                Weights are specific to this role and total {Math.round(
                  Object.values(detail.weights).reduce((sum, value) => sum + value, 0)
                )}{" "}
                points. Your score is the share of those points you earned.
              </InlineNote>
              {detail.breakdowns.map((component) => (
                <div key={component.component} className="rounded-xl border border-line bg-white p-4">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <p className="text-sm font-bold text-ink-900">{component.label}</p>
                    <p className="text-sm font-bold tabular-nums" style={{ color: scoreTone(component.raw_ratio * 100) }}>
                      {component.points_earned}
                      <span className="text-xs font-medium text-ink-400">
                        {" "}
                        / {component.points_possible} pts
                      </span>
                    </p>
                  </div>
                  <div className="mt-2">
                    <ProgressBar value={component.raw_ratio * 100} size="sm" />
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-ink-600">
                    {component.explanation}
                  </p>
                </div>
              ))}
            </div>
          ) : null}

          {tab === "skills" ? (
            <div className="space-y-4">
              <SkillComparisonBars
                data={detail.skill_comparison}
                height={Math.max(300, detail.skill_comparison.length * 30)}
              />
              <div className="overflow-hidden rounded-xl border border-line">
                <table className="w-full text-left text-xs">
                  <thead className="bg-sage-50 text-2xs uppercase tracking-wider text-ink-500">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Skill</th>
                      <th className="px-3 py-2 font-semibold">Importance</th>
                      <th className="px-3 py-2 font-semibold">Expected</th>
                      <th className="px-3 py-2 font-semibold">You</th>
                      <th className="px-3 py-2 font-semibold">Evidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {detail.skill_comparison.map((row) => (
                      <tr key={row.skill_name} className="bg-white">
                        <td className="px-3 py-2 font-medium text-ink-800">{row.skill_name}</td>
                        <td className="px-3 py-2 capitalize text-ink-500">{row.importance}</td>
                        <td className="px-3 py-2 capitalize text-ink-500">
                          {row.expected_proficiency}
                        </td>
                        <td className="px-3 py-2">
                          {row.has_skill ? (
                            <span className="capitalize text-ink-800">
                              {row.student_proficiency}
                            </span>
                          ) : (
                            <span className="text-danger-700">missing</span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          {row.is_evidence_backed ? (
                            <span className="font-semibold text-brand-700">
                              {row.evidence_count}× proven
                            </span>
                          ) : row.has_skill ? (
                            <span className="text-warn-700">claimed only</span>
                          ) : (
                            <span className="text-ink-300">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          {tab === "gaps" ? (
            <div className="space-y-4">
              {Object.entries(gapsByStatus).map(([status, gaps]) => (
                <div key={status}>
                  <p className="section-label mb-2">
                    {gapStatusLabel(status)} ({gaps.length})
                  </p>
                  <div className="space-y-2">
                    {gaps.map((gap) => (
                      <div key={gap.skill_id} className="rounded-xl border border-line bg-white p-3">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-semibold text-ink-900">{gap.skill_name}</p>
                          <Badge tone={gap.points_lost > 1 ? "warn" : "neutral"}>
                            -{gap.points_lost} pts
                          </Badge>
                        </div>
                        <p className="mt-0.5 text-2xs text-ink-400">
                          {gap.importance} · expects {gap.expected_proficiency}
                          {gap.student_proficiency ? ` · you: ${gap.student_proficiency}` : ""}
                        </p>
                        {gap.recommendation ? (
                          <p className="mt-1.5 text-xs leading-relaxed text-ink-600">
                            {gap.recommendation}
                          </p>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              {!detail.skill_gaps.length ? (
                <EmptyState title="No gaps" description="You meet this role's rubric on every skill." />
              ) : null}
            </div>
          ) : null}

          {tab === "history" ? (
            <div className="overflow-hidden rounded-xl border border-line">
              <table className="w-full text-left text-xs">
                <thead className="bg-sage-50 text-2xs uppercase tracking-wider text-ink-500">
                  <tr>
                    <th className="px-3 py-2 font-semibold">Assessed</th>
                    <th className="px-3 py-2 font-semibold">Score</th>
                    <th className="px-3 py-2 font-semibold">Band</th>
                    <th className="px-3 py-2 font-semibold">Version</th>
                    <th className="px-3 py-2 font-semibold">Trigger</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {[...detail.history].reverse().map((row) => (
                    <tr key={`${row.at}-${row.version}`} className="bg-white">
                      <td className="px-3 py-2 text-ink-700">{formatDateTime(row.at)}</td>
                      <td className="px-3 py-2 font-bold tabular-nums text-ink-900">{row.score}</td>
                      <td className="px-3 py-2 text-ink-500">{row.band}</td>
                      <td className="px-3 py-2 tabular-nums text-ink-500">v{row.version}</td>
                      <td className="px-3 py-2 text-ink-500">
                        {row.trigger ? titleCase(row.trigger) : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {detail.insights.length ? (
            <div className="space-y-2 border-t border-line pt-4">
              <p className="section-label">Observations for this role</p>
              {detail.insights.map((insight: any, index) => (
                <div
                  key={index}
                  className={cn("rounded-xl border-l-[3px] p-3.5", severityStyles(insight.severity))}
                >
                  <p className="text-sm font-semibold text-ink-900">{insight.title}</p>
                  <p className="mt-1 text-xs leading-relaxed text-ink-600">{insight.body}</p>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </Modal>
  );
}
