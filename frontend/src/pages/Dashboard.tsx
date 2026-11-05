/**
 * Student dashboard. Every value shown here comes from the /api/dashboard
 * response, which is computed from the signed-in student's own rows.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
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

  return (
    <AppShell
      title="Student Dashboard"
      subtitle={`Last assessed ${welcome.last_assessment_at ? relativeTime(welcome.last_assessment_at) : "never"} · engine v${readiness.engine_version ?? "-"}`}
      actions={
        <>
          <Badge tone={data.ai_mode === "llm_assisted" ? "brand" : "neutral"} className="hidden sm:inline-flex">
            {data.ai_mode === "llm_assisted" ? "AI-assisted analysis" : "Rule-based analysis"}
          </Badge>
          <Button
            size="sm"
            variant="outline"
            loading={refreshing}
            onClick={recalculate}
            icon={<RefreshCw size={14} />}
          >
            Re-assess
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        {/* ---------------- A. Welcome ---------------- */}
        <Card className="overflow-hidden p-0">
          <div className="mesh-forest relative px-5 py-6 text-white sm:px-7">
            <div className="absolute inset-0 grid-lines opacity-[0.06]" aria-hidden />
            <div className="relative flex flex-wrap items-start justify-between gap-5">
              <div className="min-w-0 max-w-2xl">
                <p className="text-2xs font-semibold uppercase tracking-[0.14em] text-brand-300">
                  {data.ai_mode === "llm_assisted"
                    ? "AI-generated greeting"
                    : "Personalised greeting"}
                </p>
                <h2 className="mt-1.5 text-balance font-display text-xl font-extrabold leading-snug sm:text-2xl">
                  {welcome.greeting}
                </h2>
                <div className="mt-3.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-white/65">
                  {welcome.college ? (
                    <span className="flex items-center gap-1.5">
                      <GraduationCap size={13} />
                      {welcome.college}
                    </span>
                  ) : null}
                  {welcome.degree ? (
                    <span>
                      {welcome.degree}
                      {welcome.branch ? ` · ${welcome.branch}` : ""}
                    </span>
                  ) : null}
                  {welcome.current_academic_year ? <span>{welcome.current_academic_year}</span> : null}
                  {welcome.graduation_year ? <span>Class of {welcome.graduation_year}</span> : null}
                  {welcome.cgpa !== null ? (
                    <span>
                      CGPA {welcome.cgpa}/{welcome.cgpa_scale}
                    </span>
                  ) : null}
                </div>

                {welcome.career_interests.length ? (
                  <div className="mt-4">
                    <p className="text-2xs font-semibold uppercase tracking-[0.14em] text-white/40">
                      Career interests
                    </p>
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {welcome.career_interests.map((interest) => (
                        <span
                          key={interest}
                          className="rounded-full bg-white/10 px-2.5 py-1 text-2xs font-semibold text-white/85"
                        >
                          {interest}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>

              <div className="w-full max-w-[240px] shrink-0 rounded-2xl bg-white/[0.08] p-4 ring-1 ring-white/10">
                <div className="flex items-center justify-between text-2xs font-semibold text-white/55">
                  <span>Profile completion</span>
                  <span className="tabular-nums text-brand-300">{welcome.profile_completion}%</span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-brand-400 transition-[width] duration-700 ease-smooth"
                    style={{ width: `${welcome.profile_completion}%` }}
                  />
                </div>
                <ul className="mt-3 space-y-1">
                  {Object.entries(welcome.completion_breakdown)
                    .filter(([, value]: any) => !value.complete)
                    .slice(0, 3)
                    .map(([key, value]: any) => (
                      <li key={key} className="flex items-center justify-between text-2xs text-white/60">
                        <span>{value.label}</span>
                        <span className="tabular-nums">
                          {value.earned}/{value.weight}
                        </span>
                      </li>
                    ))}
                </ul>
                <Link to="/app/settings" className="mt-3 block">
                  <Button size="sm" variant="secondary" fullWidth>
                    Complete profile
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </Card>

        {/* ---------------- B. Readiness overview ---------------- */}
        {!readiness.has_assessments ? (
          <EmptyState
            icon={<GaugeCircle size={18} />}
            title="No assessment yet"
            description="Run an assessment to generate your role-wise readiness scores."
            action={
              <Button loading={refreshing} onClick={recalculate} icon={<Sparkles size={15} />}>
                Run my first assessment
              </Button>
            }
          />
        ) : (
          <>
            <div className="grid gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
              <Card className="p-5">
                <SectionHeader title="Overall readiness" icon={<GaugeCircle size={17} />} />
                <div className="mt-4 flex flex-col items-center">
                  <ScoreRing
                    score={readiness.overall_score ?? 0}
                    label={readiness.overall_band ?? ""}
                    sublabel="across target roles"
                  />
                  <p className="mt-3 text-center text-xs leading-relaxed text-ink-500">
                    Average of your {readiness.preferred_roles.length || readiness.roles.length}{" "}
                    {readiness.preferred_roles.length ? "target" : "scored"} role
                    {(readiness.preferred_roles.length || readiness.roles.length) === 1 ? "" : "s"}.
                    Assessed {formatDateTime(readiness.last_assessed_at)}.
                  </p>
                </div>

                <div className="mt-5 space-y-2.5 border-t border-line pt-4">
                  <p className="section-label">Best matching domains</p>
                  {readiness.domain_averages.slice(0, 4).map((domain) => (
                    <div key={domain.domain_slug}>
                      <div className="mb-1 flex items-baseline justify-between gap-2">
                        <span className="truncate text-xs font-medium text-ink-700">
                          {domain.domain_name}
                        </span>
                        <span className="shrink-0 text-xs font-bold tabular-nums text-ink-800">
                          {domain.average_score}
                        </span>
                      </div>
                      <ProgressBar value={domain.average_score} size="sm" />
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-5">
                <SectionHeader
                  title="Role-wise readiness"
                  description="Each role is scored against its own rubric. Click a role for the full breakdown."
                  icon={<Target size={17} />}
                />
                <div className="mt-4">
                  <RoleScoreBars
                    data={readiness.roles}
                    height={Math.max(300, readiness.roles.length * 26)}
                    onSelect={(slug) => slug && setOpenRole(slug)}
                  />
                </div>
              </Card>
            </div>

            {/* Preferred role cards */}
            <div>
              <SectionHeader
                title="Your target roles"
                description="Scores for the roles you selected during onboarding."
                icon={<Trophy size={17} />}
                action={
                  <Link to="/app/settings">
                    <Button size="sm" variant="ghost">
                      Change targets
                    </Button>
                  </Link>
                }
              />
              <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {(readiness.preferred_roles.length
                  ? readiness.preferred_roles
                  : readiness.best_matches
                ).map((role) => (
                  <Card
                    key={role.role_id}
                    interactive
                    className="cursor-pointer p-4"
                    as="button"
                  >
                    <div
                      onClick={() => setOpenRole(role.role_slug)}
                      className="w-full text-left"
                      role="button"
                      tabIndex={0}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") setOpenRole(role.role_slug);
                      }}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span
                              className="h-2 w-2 shrink-0 rounded-full"
                              style={{ backgroundColor: role.accent_color ?? "#187C4F" }}
                            />
                            <p className="truncate text-sm font-bold text-ink-900">
                              {role.role_name}
                            </p>
                          </div>
                          <p className="mt-0.5 truncate text-2xs text-ink-400">
                            {role.domain_name}
                          </p>
                        </div>
                        {role.is_primary ? <Badge tone="forest">Primary</Badge> : null}
                      </div>

                      <div className="mt-3 flex items-end justify-between gap-3">
                        <div>
                          <p
                            className="font-display text-3xl font-extrabold leading-none tabular-nums"
                            style={{ color: scoreTone(role.score) }}
                          >
                            {role.score}
                            <span className="text-sm font-semibold text-ink-300">/100</span>
                          </p>
                          <span
                            className={cn(
                              "mt-1.5 inline-block rounded-full border px-2 py-0.5 text-2xs font-semibold",
                              bandColor(role.band)
                            )}
                          >
                            {role.band}
                          </span>
                        </div>
                        {role.score_delta !== null ? (
                          <span
                            className={cn(
                              "flex items-center gap-1 text-xs font-bold",
                              role.score_delta >= 0 ? "text-brand-600" : "text-danger-500"
                            )}
                          >
                            {role.score_delta >= 0 ? (
                              <TrendingUp size={13} />
                            ) : (
                              <TrendingDown size={13} />
                            )}
                            {role.score_delta > 0 ? "+" : ""}
                            {role.score_delta}
                          </span>
                        ) : null}
                      </div>

                      <div className="mt-3">
                        <ProgressBar value={role.score} size="sm" />
                      </div>

                      <div className="mt-3 flex items-center justify-between border-t border-line pt-2.5 text-2xs text-ink-500">
                        <span>
                          {role.matched_required}/{role.total_required} required skills
                        </span>
                        <span className="flex items-center gap-0.5 font-semibold text-brand-600">
                          Breakdown <ChevronRight size={11} />
                        </span>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>

            {/* ---------------- C. Strengths & improvements ---------------- */}
            <div className="grid gap-5 lg:grid-cols-2">
              <Card className="p-5">
                <SectionHeader
                  title="Your strengths"
                  description={`For ${readiness.preferred_roles.find((r) => r.is_primary)?.role_name ?? readiness.roles[0]?.role_name ?? "your top role"}`}
                  icon={<CheckCircle2 size={17} />}
                />
                <div className="mt-4 space-y-2.5">
                  {data.strengths.length ? (
                    data.strengths.map((item: any, index) => (
                      <div
                        key={index}
                        className="rounded-xl border border-brand-100 bg-brand-50/50 p-3.5"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-sm font-semibold text-forest-800">{item.title}</p>
                          {item.score_contribution ? (
                            <Badge tone="brand">+{item.score_contribution} pts</Badge>
                          ) : null}
                        </div>
                        <p className="mt-1 text-xs leading-relaxed text-ink-600">{item.detail}</p>
                      </div>
                    ))
                  ) : (
                    <EmptyState
                      title="No strengths identified yet"
                      description="Add projects and internships so the engine has evidence to work with."
                    />
                  )}
                </div>
              </Card>

              <Card className="p-5">
                <SectionHeader
                  title="Areas to improve"
                  description="Ordered by the points at stake"
                  icon={<Target size={17} />}
                />
                <div className="mt-4 space-y-2.5">
                  {data.improvements.length ? (
                    data.improvements.map((item: any, index) => (
                      <div
                        key={index}
                        className="rounded-xl border border-warn-500/20 bg-warn-50/40 p-3.5"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-sm font-semibold text-ink-900">{item.title}</p>
                          {item.points_at_stake ? (
                            <Badge tone="warn">{item.points_at_stake} pts</Badge>
                          ) : null}
                        </div>
                        <p className="mt-1 text-xs leading-relaxed text-ink-600">{item.detail}</p>
                      </div>
                    ))
                  ) : (
                    <EmptyState title="No gaps detected" description="Your profile clears this role's rubric." />
                  )}
                </div>
              </Card>
            </div>

            {/* ---------------- Domain comparison ---------------- */}
            <Card className="p-5">
              <SectionHeader
                title="Domain comparison"
                description="Average and best score within each career domain."
                icon={<BarChart3 size={17} />}
              />
              <div className="mt-4">
                <DomainAverageBars data={readiness.domain_averages} />
              </div>
            </Card>
          </>
        )}

        {/* ---------------- D. Skill analysis ---------------- */}
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
          <Card className="p-5">
            <SectionHeader
              title="Skill analysis"
              description={`${skills.total_skills} skills · ${skills.evidence_backed} backed by projects or internships`}
              icon={<Zap size={17} />}
              action={
                <Link to="/app/settings">
                  <Button size="sm" variant="ghost">
                    Edit skills
                  </Button>
                </Link>
              }
            />

            {skills.total_skills ? (
              <>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  {[
                    { label: "Total skills", value: skills.total_skills, tone: "neutral" as const },
                    {
                      label: "Evidence-backed",
                      value: skills.evidence_backed,
                      tone: "brand" as const,
                    },
                    { label: "Claimed only", value: skills.claimed_only, tone: "warn" as const },
                  ].map((stat) => (
                    <div key={stat.label} className="rounded-xl border border-line bg-surface-muted p-3.5">
                      <p className="font-display text-2xl font-extrabold tabular-nums text-forest-800">
                        {stat.value}
                      </p>
                      <p className="mt-0.5 text-2xs font-medium text-ink-500">{stat.label}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-5 grid gap-5 sm:grid-cols-2">
                  <div>
                    <p className="section-label mb-2">By category</p>
                    <CategoryBars
                      data={skills.by_category.map((item) => ({
                        label: item.label,
                        count: item.count,
                      }))}
                    />
                  </div>
                  <div>
                    <p className="section-label mb-2">Technical vs business mix</p>
                    <CategoryBars data={skills.technical_vs_business} color="#0C3326" />
                  </div>
                </div>

                <div className="mt-5 border-t border-line pt-4">
                  <p className="section-label mb-2.5">Strongest skills</p>
                  <div className="flex flex-wrap gap-1.5">
                    {skills.top_skills.map((skill) => (
                      <span
                        key={skill.name}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-white px-2.5 py-1.5 text-xs"
                      >
                        <span className="font-semibold text-ink-800">{skill.name}</span>
                        <span className="text-2xs capitalize text-ink-400">{skill.proficiency}</span>
                        {skill.evidence_count ? (
                          <span className="rounded bg-brand-50 px-1 py-0.5 text-2xs font-bold text-brand-700">
                            {skill.evidence_count}× proven
                          </span>
                        ) : null}
                      </span>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <EmptyState
                className="mt-4"
                icon={<Zap size={18} />}
                title="No skills on your profile"
                description="Add skills from Settings to unlock skill analysis."
                action={
                  <Link to="/app/settings">
                    <Button size="sm">Add skills</Button>
                  </Link>
                }
              />
            )}
          </Card>

          <div className="space-y-5">
            <Card className="p-5">
              <SectionHeader title="Proficiency coverage" icon={<BarChart3 size={17} />} />
              {skills.radar.length >= 3 ? (
                <SkillRadar data={skills.radar} />
              ) : (
                <EmptyState
                  className="mt-4"
                  title="Not enough categories"
                  description="Add skills across at least three categories to see the radar."
                />
              )}
            </Card>

            {skills.role_gaps.length ? (
              <Card className="p-5">
                <SectionHeader
                  title="Skill gaps for your primary role"
                  description="Biggest point losses first."
                  icon={<Target size={17} />}
                />
                <div className="mt-3 space-y-2">
                  {skills.role_gaps.slice(0, 6).map((gap) => (
                    <div key={gap.skill_name} className="rounded-xl border border-line bg-white p-3">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-semibold text-ink-900">{gap.skill_name}</p>
                        <Badge
                          tone={
                            gap.status === "missing"
                              ? "danger"
                              : gap.status === "claimed_only"
                                ? "warn"
                                : "neutral"
                          }
                        >
                          -{gap.points_lost}
                        </Badge>
                      </div>
                      <p className="mt-0.5 text-2xs text-ink-400">
                        {gapStatusLabel(gap.status)} · {gap.importance} · expects{" "}
                        {gap.expected_proficiency}
                      </p>
                      {gap.recommendation ? (
                        <p className="mt-1.5 text-xs leading-relaxed text-ink-600">
                          {gap.recommendation}
                        </p>
                      ) : null}
                    </div>
                  ))}
                </div>
              </Card>
            ) : null}
          </div>
        </div>

        {/* ---------------- E. Roadmap ---------------- */}
        <Card className="p-5">
          <SectionHeader
            title="AI improvement roadmap"
            description={
              roadmap.generated_at
                ? `${roadmap.completed_tasks} of ${roadmap.total_tasks} actions complete · generated ${relativeTime(roadmap.generated_at)} (${roadmap.generator === "rule_based" ? "rule-based" : roadmap.generator})`
                : "No roadmap generated yet."
            }
            icon={<ListChecks size={17} />}
            action={
              roadmap.total_tasks ? (
                <div className="w-32">
                  <ProgressBar value={roadmap.completion_percent} size="sm" showLabel />
                </div>
              ) : null
            }
          />

          {roadmap.tasks.length ? (
            <div className="mt-4 space-y-2.5">
              {[...pendingTasks, ...roadmap.tasks.filter((task) => task.status === "completed")].map(
                (task) => {
                  const done = task.status === "completed";
                  return (
                    <div
                      key={task.id}
                      className={cn(
                        "rounded-xl border p-4 transition-all duration-200",
                        done ? "border-line bg-sage-50/60 opacity-75" : "border-line bg-white"
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <button
                          onClick={() => setTaskStatus(task.id, done ? "pending" : "completed")}
                          disabled={savingTask === task.id}
                          className={cn(
                            "mt-0.5 shrink-0 rounded-full transition-colors",
                            done ? "text-brand-600" : "text-ink-300 hover:text-brand-500"
                          )}
                          aria-label={done ? "Mark as pending" : "Mark as completed"}
                        >
                          {done ? <CheckCircle2 size={20} /> : <Circle size={20} />}
                        </button>

                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <p
                              className={cn(
                                "text-sm font-bold",
                                done ? "text-ink-500 line-through" : "text-ink-900"
                              )}
                            >
                              {task.title}
                            </p>
                            <span
                              className={cn(
                                "rounded-full border px-2 py-0.5 text-2xs font-semibold capitalize",
                                priorityStyles(task.priority)
                              )}
                            >
                              {task.priority}
                            </span>
                            {task.expected_score_gain ? (
                              <Badge tone="brand">+{task.expected_score_gain} pts</Badge>
                            ) : null}
                          </div>

                          <p className="mt-1.5 text-xs leading-relaxed text-ink-600">{task.reason}</p>

                          <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-2xs text-ink-400">
                            {task.suggested_duration ? (
                              <span className="flex items-center gap-1">
                                <Clock size={11} />
                                {task.suggested_duration}
                              </span>
                            ) : null}
                            {task.expected_improvement_area ? (
                              <span className="flex items-center gap-1">
                                <Target size={11} />
                                {task.expected_improvement_area}
                              </span>
                            ) : null}
                            {task.related_skill ? (
                              <span className="flex items-center gap-1">
                                <Zap size={11} />
                                {task.related_skill}
                              </span>
                            ) : null}
                            {done && task.completed_at ? (
                              <span className="text-brand-600">
                                Completed {relativeTime(task.completed_at)}
                              </span>
                            ) : null}
                          </div>
                        </div>

                        {!done ? (
                          <Button
                            size="sm"
                            variant="outline"
                            loading={savingTask === task.id}
                            onClick={() => setTaskStatus(task.id, "completed")}
                            className="hidden shrink-0 sm:inline-flex"
                          >
                            Mark done
                          </Button>
                        ) : null}
                      </div>
                    </div>
                  );
                }
              )}
            </div>
          ) : (
            <EmptyState
              className="mt-4"
              icon={<ListChecks size={18} />}
              title="No roadmap yet"
              description="Run an assessment and the engine will turn your gaps into ordered actions."
            />
          )}
        </Card>

        {/* ---------------- F + G. Resume insights & portfolio ---------------- */}
        <div className="grid gap-5 lg:grid-cols-2">
          <Card className="p-5">
            <SectionHeader
              title="Resume insights"
              description={
                resume_insights.has_resume
                  ? `${resume_insights.resume?.filename} · ${resume_insights.word_count} words`
                  : "No resume uploaded yet."
              }
              icon={<FileText size={17} />}
              action={
                <Link to="/onboarding?step=6">
                  <Button size="sm" variant="ghost">
                    {resume_insights.has_resume ? "Replace" : "Upload"}
                  </Button>
                </Link>
              }
            />

            {resume_insights.has_resume ? (
              <div className="mt-4 space-y-4">
                <div className="flex items-center gap-5">
                  <ScoreRing
                    score={resume_insights.quality_score ?? 0}
                    size={104}
                    strokeWidth={9}
                    label="quality"
                  />
                  <div className="min-w-0 flex-1 space-y-1.5">
                    {resume_insights.sections_found.length ? (
                      <div>
                        <p className="section-label">Sections found</p>
                        <p className="text-xs text-ink-600">
                          {resume_insights.sections_found.map(titleCase).join(", ")}
                        </p>
                      </div>
                    ) : null}
                    {resume_insights.sections_missing.length ? (
                      <div>
                        <p className="section-label">Missing sections</p>
                        <p className="text-xs text-warn-700">
                          {resume_insights.sections_missing.map(titleCase).join(", ")}
                        </p>
                      </div>
                    ) : null}
                  </div>
                </div>

                {resume_insights.missing_keywords.length ? (
                  <div>
                    <p className="section-label mb-2">
                      Role keywords
                      {resume_insights.resume?.focus_role
                        ? ` for ${resume_insights.resume.focus_role}`
                        : ""}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {resume_insights.missing_keywords.map((item) => (
                        <span
                          key={item.keyword}
                          className={cn(
                            "rounded-lg border px-2 py-1 text-2xs font-medium",
                            item.present
                              ? "border-brand-200 bg-brand-50 text-brand-700"
                              : "border-dashed border-line-strong bg-white text-ink-400"
                          )}
                        >
                          {item.present ? "✓ " : "× "}
                          {item.keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}

                {resume_insights.improvements.length ? (
                  <div className="border-t border-line pt-3.5">
                    <p className="section-label mb-2">Suggested improvements</p>
                    <ul className="space-y-1.5">
                      {resume_insights.improvements.slice(0, 4).map((item) => (
                        <li key={item} className="flex items-start gap-2 text-xs text-ink-600">
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-warn-500" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {resume_insights.strengths.length ? (
                  <div>
                    <p className="section-label mb-2">Resume strengths</p>
                    <div className="flex flex-wrap gap-1.5">
                      {resume_insights.strengths.map((item) => (
                        <Badge key={item} tone="brand">
                          {item}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <EmptyState
                className="mt-4"
                icon={<FileText size={18} />}
                title="Resume not analysed"
                description="Upload a PDF or DOCX to unlock keyword analysis and the resume component of every role score."
                action={
                  <Link to="/onboarding?step=6">
                    <Button size="sm">Upload resume</Button>
                  </Link>
                }
              />
            )}
          </Card>

          <Card className="p-5">
            <SectionHeader
              title="Projects & experience"
              description="Everything the scoring engine treats as evidence."
              icon={<FolderGit2 size={17} />}
              action={
                <Link to="/app/settings">
                  <Button size="sm" variant="ghost">
                    Manage
                  </Button>
                </Link>
              }
            />

            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
              {[
                { label: "Projects", value: portfolio.projects, icon: <FolderGit2 size={14} /> },
                { label: "Internships", value: portfolio.internships, icon: <Briefcase size={14} /> },
                { label: "Work roles", value: portfolio.work_experience, icon: <Briefcase size={14} /> },
                { label: "Certifications", value: portfolio.certifications, icon: <Award size={14} /> },
                { label: "Achievements", value: portfolio.achievements, icon: <Trophy size={14} /> },
                {
                  label: "Leadership",
                  value: portfolio.positions_of_responsibility,
                  icon: <Sparkles size={14} />,
                },
              ].map((stat) => (
                <div key={stat.label} className="rounded-xl border border-line bg-surface-muted p-3">
                  <span className="text-brand-600">{stat.icon}</span>
                  <p className="mt-1 font-display text-xl font-extrabold tabular-nums text-forest-800">
                    {stat.value}
                  </p>
                  <p className="text-2xs font-medium text-ink-500">{stat.label}</p>
                </div>
              ))}
            </div>

            <p className="mt-3 text-xs text-ink-500">
              Total internship and work exposure:{" "}
              <strong className="text-ink-800">
                {monthsToText(portfolio.total_experience_months)}
              </strong>
            </p>

            {portfolio.recent_projects.length ? (
              <div className="mt-4 border-t border-line pt-4">
                <p className="section-label mb-2.5">Recent projects</p>
                <div className="space-y-2">
                  {portfolio.recent_projects.map((project) => (
                    <div key={project.id} className="rounded-xl border border-line bg-white p-3">
                      <div className="flex items-start justify-between gap-2">
                        <p className="truncate text-sm font-semibold text-ink-900">
                          {project.title}
                        </p>
                        {project.category ? <Badge tone="neutral">{project.category}</Badge> : null}
                      </div>
                      {project.technologies.length ? (
                        <p className="mt-1 truncate text-2xs text-ink-400">
                          {project.technologies.join(" · ")}
                        </p>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {portfolio.links.github || portfolio.links.linkedin || portfolio.links.portfolio ? (
              <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4">
                {[
                  { label: "GitHub", url: portfolio.links.github },
                  { label: "LinkedIn", url: portfolio.links.linkedin },
                  { label: "Portfolio", url: portfolio.links.portfolio },
                ]
                  .filter((link) => link.url)
                  .map((link) => (
                    <a
                      key={link.label}
                      href={link.url as string}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-white px-2.5 py-1.5 text-xs font-semibold text-ink-700 transition-colors hover:border-brand-300 hover:text-brand-700"
                    >
                      {link.label}
                      <ExternalLink size={11} />
                    </a>
                  ))}
              </div>
            ) : null}
          </Card>
        </div>

        {/* ---------------- H. Career fit ---------------- */}
        {data.career_fit.length ? (
          <Card className="p-5">
            <SectionHeader
              title="Career fit recommendations"
              description="Why each role fits, and what is missing for the rest."
              icon={<Target size={17} />}
            />
            <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {data.career_fit.map((fit) => (
                <div key={fit.role_id} className="rounded-2xl border border-line bg-surface-muted p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-ink-900">{fit.role_name}</p>
                      <p className="text-2xs text-ink-400">{fit.domain_name}</p>
                    </div>
                    <span
                      className="shrink-0 font-display text-xl font-extrabold tabular-nums"
                      style={{ color: scoreTone(fit.score) }}
                    >
                      {fit.score}
                    </span>
                  </div>

                  <span
                    className={cn(
                      "mt-2 inline-block rounded-full border px-2 py-0.5 text-2xs font-semibold",
                      bandColor(fit.band)
                    )}
                  >
                    {fit.fit_label}
                  </span>

                  {fit.why_good_fit.length ? (
                    <div className="mt-3">
                      <p className="text-2xs font-semibold uppercase tracking-wider text-brand-600">
                        Working for you
                      </p>
                      <ul className="mt-1 space-y-1">
                        {fit.why_good_fit.map((item) => (
                          <li key={item} className="flex items-start gap-1.5 text-2xs text-ink-600">
                            <CheckCircle2 size={10} className="mt-1 shrink-0 text-brand-500" />
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  {fit.whats_missing.length ? (
                    <div className="mt-2.5">
                      <p className="text-2xs font-semibold uppercase tracking-wider text-warn-700">
                        Still missing
                      </p>
                      <ul className="mt-1 space-y-1">
                        {fit.whats_missing.map((item) => (
                          <li key={item} className="flex items-start gap-1.5 text-2xs text-ink-600">
                            <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-warn-500" />
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  <button
                    onClick={() => setOpenRole(fit.role_slug)}
                    className="mt-3 flex w-full items-center justify-center gap-1 rounded-lg bg-white px-2 py-1.5 text-2xs font-semibold text-brand-700 ring-1 ring-line transition-colors hover:bg-brand-50"
                  >
                    Full breakdown <ChevronRight size={11} />
                  </button>
                </div>
              ))}
            </div>
          </Card>
        ) : null}

        {/* ---------------- I. Progress ---------------- */}
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
          <Card className="p-5">
            <SectionHeader
              title="Progress over time"
              description={`${progress.assessment_count} assessment snapshot(s) stored since ${progress.first_assessed_at ? relativeTime(progress.first_assessed_at) : "-"}`}
              icon={<LineChartIcon size={17} />}
            />
            {progress.overall_series.length > 1 ? (
              <div className="mt-4 space-y-5">
                <div>
                  <p className="section-label mb-1">Average across roles</p>
                  <OverallTrend data={progress.overall_series} />
                </div>
                <div className="border-t border-line pt-4">
                  <p className="section-label mb-1">Per-role history (target roles)</p>
                  <ScoreHistoryChart
                    series={progress.series.filter((series) =>
                      readiness.preferred_roles.some((role) => role.role_slug === series.role_slug)
                    )}
                  />
                </div>
              </div>
            ) : (
              <InlineNote tone="info" icon={<Info size={15} />}>
                Only one assessment so far. Update your profile or press "Re-assess" and the
                comparison appears here - every assessment is stored as a snapshot.
              </InlineNote>
            )}

            {progress.best_improvement ? (
              <div className="mt-4 rounded-xl border border-brand-100 bg-brand-50/60 p-3.5">
                <p className="text-xs font-semibold text-brand-800">
                  Biggest improvement: {progress.best_improvement.role_name}
                </p>
                <p className="mt-0.5 text-2xs text-brand-700">
                  {progress.best_improvement.from_score} → {progress.best_improvement.to_score} (
                  {progress.best_improvement.delta > 0 ? "+" : ""}
                  {progress.best_improvement.delta} points)
                </p>
              </div>
            ) : null}
          </Card>

          <div className="space-y-5">
            {/* K. AI insights */}
            <Card className="p-5">
              <SectionHeader
                title="Career insights"
                description={
                  data.ai_mode === "llm_assisted"
                    ? "Generated with LLM assistance from your profile."
                    : "Derived from your profile by the rule-based engine."
                }
                icon={<Brain size={17} />}
              />
              <div className="mt-3 space-y-2.5">
                {data.ai_insights.length ? (
                  data.ai_insights.map((insight, index) => (
                    <div
                      key={index}
                      className={cn("rounded-xl border-l-[3px] p-3.5", severityStyles(insight.severity))}
                    >
                      <p className="text-sm font-semibold text-ink-900">{insight.title}</p>
                      <p className="mt-1 text-xs leading-relaxed text-ink-600">{insight.body}</p>
                    </div>
                  ))
                ) : (
                  <EmptyState title="No insights yet" description="Complete an assessment first." />
                )}
              </div>
            </Card>

            {/* J. Recent activity */}
            <Card className="p-5">
              <SectionHeader title="Recent activity" icon={<ActivityIcon size={17} />} />
              <ol className="mt-3 space-y-0">
                {data.recent_activity.length ? (
                  data.recent_activity.map((item, index) => (
                    <li key={item.id} className="relative flex gap-3 pb-4 last:pb-0">
                      {index < data.recent_activity.length - 1 ? (
                        <span className="absolute left-[11px] top-6 h-full w-px bg-line" aria-hidden />
                      ) : null}
                      <span className="relative mt-0.5 grid h-[22px] w-[22px] shrink-0 place-items-center rounded-full bg-brand-50 ring-1 ring-brand-100">
                        <span className="h-1.5 w-1.5 rounded-full bg-brand-500" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold text-ink-800">{item.title}</p>
                        {item.description ? (
                          <p className="mt-0.5 line-clamp-2 text-2xs text-ink-500">
                            {item.description}
                          </p>
                        ) : null}
                        <p className="mt-0.5 text-2xs text-ink-400">{relativeTime(item.created_at)}</p>
                      </div>
                    </li>
                  ))
                ) : (
                  <EmptyState title="No activity yet" />
                )}
              </ol>
            </Card>
          </div>
        </div>
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
