/** Career Insights: the full intelligence dashboard for one profession. */
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowLeft, BookOpen, Bookmark, BookmarkCheck, Briefcase, Building2, ExternalLink, GitCompare, Info, Sparkles, Target, ThumbsDown, ThumbsUp, TrendingUp } from "lucide-react";
import { AppShell } from "../components/layout";
import { Badge, Button, Card, EmptyState, ErrorState, InlineNote, LoadingBlock, SectionHeader } from "../components/ui";
import { Chip, useApi } from "../components/careerverse";
import { Aurora, CountUp } from "../components/fx";
import { CompanyExplorer, DemandGauge, FitRadar, SalaryExplorer, SkillMix } from "../components/InsightCharts";
import { request } from "../lib/api";
import { cn } from "../lib/utils";

type SalaryRow = { is_estimate?: boolean; level: string; level_label: string; amount: number | null; range_low: number | null; range_high: number | null; currency: string; location: string | null; experience_min_years: number | null; experience_max_years: number | null; salary_type: string; source_name: string; source_url: string | null; reference_year: number | null; last_verified: string | null };
type Detail = {
  id: number; slug: string; title: string; industry: string; short_description: string;
  overview: { description: string; responsibilities: string[]; industries: string[]; work_environment: string };
  ai_summary: { headline?: string; what_it_is?: string; a_typical_week?: string; who_it_suits?: string; growth_path?: string; things_to_know?: string[] } | null;
  ai_available: boolean;
  salary: { available: boolean; india: { rows: SalaryRow[]; available: boolean; note: string | null }; us: { rows: SalaryRow[]; available: boolean; note: string | null }; international: SalaryRow[]; experience_wise: SalaryRow[]; location_wise: SalaryRow[]; compensation_split: SalaryRow[]; comparison_note: string };
  companies: { companies: { name: string; industry: string; job_titles: string[]; regions: string[] }[]; disclaimer: string };
  trajectory: { stages: { stage: number; level: string; designation: string; experience_min_years: number | null; experience_max_years: number | null }[] };
  work_life_balance: Record<string, string | number>;
  skills: { technical_skills: string[]; tools: string[]; industry_knowledge: string[]; soft_skills: string[]; degrees: string[]; certifications: string[] };
  outlook: { current_demand: string; growth_drivers: string[]; emerging_technologies: string[]; geographic_demand: string[]; employment_growth_note?: string; us_employment?: { value: number; year: number; source: string; scope: string } };
  exits: { roles: string[]; industries: string[]; qualifications: string[] };
  advantages: { aspect: string; note: string }[];
  disadvantages: { aspect: string; note: string }[];
  sources: { kind: string; name: string; url: string | null; covers: string | null; last_verified: string | null }[];
  last_updated: string | null;
};
type Fit = {
  profile_ready: boolean; message?: string; score?: number; explanation?: string; explanation_source?: string; disclaimer?: string; targeted_by_student?: boolean;
  components?: Record<string, { label: string; weight: number; value: number | null; has_data: boolean }>;
  strengths?: string[]; gaps?: string[]; recommendations?: string[];
};
type Jobs = { available: boolean; reason?: string; total?: number; attribution?: string; listings?: { title: string; company: string; location: string; url: string }[] };

const fmt = (n: number | null, cur: string) => (n == null ? "n/a" : new Intl.NumberFormat("en-US", { style: "currency", currency: cur, maximumFractionDigits: 0 }).format(n));
const years = (a: number | null, b: number | null) => (a == null ? "" : b == null ? `${a}+ yrs` : `${a}-${b} yrs`);

function Meter({ value, max = 5 }: { value: number; max?: number }) {
  return (
    <div className="flex gap-1" role="img" aria-label={`${value} out of ${max}`}>
      {Array.from({ length: max }, (_, i) => <span key={i} className={cn("h-2.5 w-7 rounded-full", i < value ? "cv-grow bg-brand-500" : "bg-sage-300")} style={{ animationDelay: `${i * 0.12}s` }} />)}
    </div>
  );
}

function SourceLine({ r }: { r: SalaryRow }) {
  return (
    <p className="text-xs text-ink-500">
      Source: {r.source_url ? <a className="underline" href={r.source_url} target="_blank" rel="noreferrer">{r.source_name}</a> : r.source_name}
      {r.reference_year ? `, ${r.reference_year} data` : ""}{r.last_verified ? `, verified ${r.last_verified}` : ""}
    </p>
  );
}

export default function CareerInsights() {
  const { slug = "" } = useParams();
  const d = useApi<Detail>(`/careers/${slug}?track=true`);
  const jobs = useApi<Jobs>(`/careers/${slug}/job-market`);
  const [fit, setFit] = useState<Fit | null>(null);
  const [fitLoading, setFitLoading] = useState(false);
  const [fitError, setFitError] = useState<string | null>(null);
  const [saved, setSaved] = useState<boolean | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [nav, setNav] = useState<{ id: string; label: string }[]>([]);
  const [active, setActive] = useState("");

  const c = d.data;

  // Generate the Gemini summary once (server caches it); never blocks the page.
  useEffect(() => {
    if (!c || c.ai_summary || !c.ai_available) return;
    setAiBusy(true);
    request<{ ai_summary: Detail["ai_summary"] }>(`/careers/${slug}/ai-summary`, { method: "POST" })
      .then((r) => d.setData((cur) => (cur ? { ...cur, ai_summary: r.ai_summary } : cur)))
      .catch(() => undefined)
      .finally(() => setAiBusy(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [c?.id]);

  // Scroll reveal for every card + a sticky section nav with scroll-spy.
  useEffect(() => {
    if (!c) return;
    const cards = Array.from(document.querySelectorAll<HTMLElement>("main .card, main .card-interactive"));
    cards.forEach((el, i) => { el.classList.add("cv-rev"); el.style.transitionDelay = `${Math.min(i, 3) * 60}ms`; });
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("cv-rev-in"); io.unobserve(e.target); } }), { rootMargin: "0px 0px -6% 0px", threshold: 0.05 });
    cards.forEach((el) => io.observe(el));
    const heads = Array.from(document.querySelectorAll<HTMLElement>("main h2")).filter((h) => h.closest(".card") && !h.querySelector(".cv-gradient-text"));
    heads.forEach((h, i) => { h.id = h.id || `sec-${i}`; (h.closest(".card") as HTMLElement).style.scrollMarginTop = "90px"; });
    setNav(heads.map((h) => ({ id: h.id, label: (h.textContent ?? "").replace(/Career Fit Score/, "Fit score").replace(/Profession overview/, "Overview").replace(/Salary intelligence/, "Salary").replace(/Company intelligence/, "Companies").replace(/Career trajectory/, "Trajectory").replace(/Skills and qualifications/, "Skills").replace(/Industry outlook/, "Outlook").replace(/Exit opportunities/, "Exits") })));
    const spy = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) setActive(e.target.id); }), { rootMargin: "-20% 0px -70% 0px" });
    heads.forEach((h) => spy.observe(h));
    return () => { io.disconnect(); spy.disconnect(); };
  }, [c?.id]);

  async function runFit() {
    setFitLoading(true);
    setFitError(null);
    try {
      setFit(await request<Fit>(`/career-fit/${slug}`, { method: "POST" }));
    } catch (e) {
      setFitError((e as Error).message);
    } finally {
      setFitLoading(false);
    }
  }

  async function toggleSave() {
    const next = !saved;
    try {
      await request(`/careers/${slug}/saved`, { method: "PUT", body: { saved: next } });
      setSaved(next);
    } catch { /* leave unchanged */ }
  }

  const us = c?.salary.us.rows ?? [];
  const chartRows = us.filter((r) => r.amount != null).map((r) => ({ name: r.level_label.replace(/ \(.*\)/, ""), amount: r.amount as number }));

  return (
    <AppShell title={c?.title ?? "Career Insights"} subtitle="Career Insights: data, sources and what the path looks like"
      actions={<Link to="/app/careerverse"><Button variant="outline" size="sm" icon={<ArrowLeft size={14} />}>All professions</Button></Link>}>
      <div className="mx-auto max-w-7xl space-y-6">
        {d.loading && !c ? <LoadingBlock label="Loading career insights" rows={5} /> : null}
        {d.error ? <ErrorState message={d.error} onRetry={d.reload} /> : null}
        {c && nav.length ? (
          <nav aria-label="Sections" className="sticky top-0 z-20 -mx-1 flex gap-1.5 overflow-x-auto rounded-2xl bg-surface-sunken/85 px-1 py-2.5 backdrop-blur-md [scrollbar-width:none]">
            {nav.map((n) => (
              <button key={n.id} onClick={() => document.getElementById(n.id)?.scrollIntoView({ behavior: "smooth", block: "start" })}
                className={cn("shrink-0 rounded-full border px-3.5 py-1.5 text-xs font-bold transition-all", active === n.id ? "scale-105 border-forest-800 bg-forest-800 text-white shadow" : "border-line-strong bg-white text-ink-600 hover:border-brand-400")}>{n.label}</button>
            ))}
          </nav>
        ) : null}
        {c ? (
          <>
            <Card className="relative overflow-hidden !rounded-[28px] bg-gradient-to-br from-forest-900 via-forest-800 to-[#12305A] p-0">
              <Aurora />
              <div className="cv-rise relative space-y-3 px-6 py-8 text-white sm:px-10">
                <Chip tone="brand">{c.industry}</Chip>
                <h2 className="font-display text-4xl font-extrabold"><span className="cv-gradient-text">{c.title}</span></h2>
                <p className="max-w-3xl text-white/80">{c.ai_summary?.headline ?? c.short_description}</p>
                <div className="flex flex-wrap gap-2 pt-1">
                  <Link to={`/app/careerverse/${c.slug}/story`}><Button variant="secondary" size="sm" icon={<BookOpen size={14} />}>Read the career story</Button></Link>
                  <Link to={`/app/careerverse/compare?ids=${c.id}`}><Button variant="secondary" size="sm" icon={<GitCompare size={14} />}>Compare</Button></Link>
                  <Button variant="secondary" size="sm" onClick={toggleSave} icon={saved ? <BookmarkCheck size={14} /> : <Bookmark size={14} />}>{saved ? "Saved" : "Save"}</Button>
                </div>
              </div>
            </Card>

            {/* Career Fit */}
            <Card className="space-y-4 p-6 sm:p-8">
              <SectionHeader icon={<Target size={18} />} title="Career Fit Score" description="Compares your profile and resume with this role's requirements. An alignment indicator, not a hiring probability." />
              {!fit ? (
                <Button onClick={runFit} loading={fitLoading} icon={<Sparkles size={16} />}>Analyse my fit</Button>
              ) : !fit.profile_ready ? (
                <InlineNote tone="warn">{fit.message} <Link className="font-semibold underline" to="/app/settings">Update your profile</Link></InlineNote>
              ) : (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-5">
                    <div className="grid h-24 w-24 place-items-center rounded-full border-8 border-brand-500/80 text-center">
                      <span className="text-2xl font-extrabold leading-none">{Math.round(fit.score ?? 0)}<span className="block text-[10px] font-semibold text-ink-400">/ 100</span></span>
                    </div>
                    <p className="min-w-[240px] flex-1 text-sm text-ink-600">{fit.explanation} <span className="text-xs text-ink-400">({fit.explanation_source === "gemini" ? "explained by Gemini" : "rule-based explanation"})</span></p>
                  </div>
                  <FitRadar components={fit.components as any} />
                  <div className="grid gap-2 sm:grid-cols-2">
                    {Object.entries(fit.components ?? {}).map(([k, v]) => (
                      <div key={k}>
                        <div className="flex justify-between text-xs font-medium text-ink-600"><span>{v.label} <span className="text-ink-400">({Math.round(v.weight * 100)}%)</span></span><span>{v.has_data ? `${Math.round(v.value ?? 0)}` : "no data"}</span></div>
                        <div className="mt-1 h-2 rounded-full bg-sage-200"><div className="h-2 rounded-full bg-brand-500" style={{ width: `${v.has_data ? v.value : 0}%` }} /></div>
                      </div>
                    ))}
                  </div>
                  <div className="grid gap-4 md:grid-cols-3">
                    {([["Strengths", fit.strengths], ["Gaps", fit.gaps], ["Recommendations", fit.recommendations]] as const).map(([t, list]) => (
                      <div key={t} className="rounded-xl bg-sage-50 p-4"><h4 className="text-sm font-bold text-forest-800">{t}</h4><ul className="mt-1.5 list-disc space-y-1 pl-4 text-sm text-ink-600">{(list ?? []).map((x) => <li key={x}>{x}</li>)}</ul></div>
                    ))}
                  </div>
                  <p className="text-xs text-ink-500">{fit.disclaimer}</p>
                </div>
              )}
              {fitError ? <ErrorState message={fitError} onRetry={runFit} /> : null}
            </Card>

            {/* A. Overview */}
            <Card className="space-y-4 p-6 sm:p-8">
              <SectionHeader icon={<Briefcase size={18} />} title="Profession overview" />
              <p className="max-w-4xl text-[17px] leading-8 text-ink-700">{c.ai_summary?.what_it_is ?? c.overview.description}</p>
              {c.ai_summary?.a_typical_week ? <p className="text-sm text-ink-600">{c.ai_summary.a_typical_week}</p> : aiBusy ? <p className="text-xs text-ink-400">Gemini is writing a plain-language summary...</p> : null}
              <div className="grid gap-5 lg:grid-cols-2">
                <div className="rounded-2xl bg-sage-50 p-5"><h4 className="text-sm font-extrabold text-forest-800">Daily responsibilities</h4><ul className="mt-2.5 list-disc space-y-1.5 pl-5 text-[15px] leading-6 text-ink-600">{c.overview.responsibilities.map((r) => <li key={r}>{r}</li>)}</ul></div>
                <div className="space-y-4">
                  <div className="rounded-2xl bg-sage-50 p-5"><h4 className="text-sm font-extrabold text-forest-800">Industries</h4><div className="mt-2.5 flex flex-wrap gap-2">{c.overview.industries.map((i) => <Chip key={i}>{i}</Chip>)}</div></div>
                  <div className="rounded-2xl bg-sage-50 p-5"><h4 className="text-sm font-extrabold text-forest-800">Work environment</h4><p className="mt-2 text-[15px] leading-6 text-ink-600">{c.overview.work_environment}</p></div>
                </div>
              </div>
              {c.ai_summary?.things_to_know?.length ? <InlineNote tone="brand"><ul className="list-disc pl-4">{c.ai_summary.things_to_know.map((t) => <li key={t}>{t}</li>)}</ul></InlineNote> : null}
            </Card>

            {/* B. Salary */}
            <Card className="space-y-4 p-6 sm:p-8">
              <SectionHeader icon={<TrendingUp size={18} />} title="Salary intelligence" description="Only sourced figures are shown. India and US data are kept separate and never converted." />
              <div className="space-y-6">
                <div className="space-y-3">
                  <div className="flex items-center gap-2"><h4 className="text-lg font-extrabold">United States</h4><Badge tone="info">US data only</Badge>{us[0]?.is_estimate ? <Badge tone="warn"><Info size={12} /> Estimate</Badge> : <Badge tone="brand">BLS sourced</Badge>}</div>
                  {us.length ? (
                    <>
                      <div className="h-48"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartRows}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" fontSize={12} /><YAxis fontSize={12} tickFormatter={(v) => `$${Math.round(v / 1000)}k`} width={48} /><Tooltip formatter={(v: number) => fmt(v, "USD")} /><Bar dataKey="amount" fill="#229A63" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>
                      <div className="grid grid-cols-3 gap-2">{us.map((r) => <div key={r.level} className="rounded-xl bg-sage-50 p-3"><p className="text-xs text-ink-500">{r.level_label}</p><p className="text-lg font-extrabold">{r.amount != null ? <CountUp value={r.amount} format={(v) => fmt(v, r.currency)} /> : "n/a"}</p></div>)}</div>
                      <SourceLine r={us[0]} />
                    </>
                  ) : <EmptyState title="No US wage data yet" description={c.salary.us.note ?? undefined} />}
                  {c.outlook.us_employment ? <p className="text-xs text-ink-500">US employment: {c.outlook.us_employment.value.toLocaleString("en-US")} jobs ({c.outlook.us_employment.year}, {c.outlook.us_employment.source}).</p> : null}
                </div>
                <SalaryExplorer salary={c.salary as any} />
              </div>
              {c.salary.compensation_split.length || c.salary.experience_wise.length || c.salary.location_wise.length ? null : (
                <p className="text-xs text-ink-500">Experience-wise, location-wise and base-versus-total-compensation breakdowns appear automatically when sourced data is added to the curated benchmark file.</p>
              )}
              <p className="text-xs text-ink-500">{c.salary.comparison_note}</p>
            </Card>

            {/* C. Companies */}
            <Card className="space-y-4 p-6 sm:p-8">
              <SectionHeader icon={<Building2 size={18} />} title="Company intelligence" description={c.companies.disclaimer} />
              <CompanyExplorer companies={c.companies.companies} />
              {jobs.data?.available && jobs.data.listings?.length ? (
                <div className="rounded-2xl bg-sage-50 p-5"><h4 className="text-sm font-extrabold text-forest-800">Live openings ({jobs.data.total?.toLocaleString()} found)</h4>
                  <ul className="mt-1.5 space-y-1 text-sm">{jobs.data.listings.map((j) => <li key={j.url}><a className="inline-flex items-center gap-1 underline" href={j.url} target="_blank" rel="noreferrer">{j.title} <ExternalLink size={12} /></a> <span className="text-ink-500">at {j.company}, {j.location}</span></li>)}</ul>
                  <p className="mt-1 text-xs text-ink-400">{jobs.data.attribution}</p></div>
              ) : null}
            </Card>

            {/* D. Trajectory */}
            <Card className="space-y-4 p-6 sm:p-8">
              <SectionHeader icon={<TrendingUp size={18} />} title="Career trajectory" />
              <ol className="grid gap-3 md:grid-cols-4">
                {c.trajectory.stages.map((s, i) => (
                  <li key={s.stage} className="relative rounded-xl border border-line p-4" style={{ background: `rgba(34,154,99,${0.04 + i * 0.05})` }}>
                    <p className="text-xs font-bold uppercase tracking-wide text-brand-700">{s.level}</p>
                    <p className="mt-1 font-semibold leading-snug">{s.designation}</p>
                    <p className="mt-1 text-xs text-ink-500">{years(s.experience_min_years, s.experience_max_years)}</p>
                  </li>
                ))}
              </ol>
            </Card>

            {/* E. WLB */}
            <Card className="space-y-4 p-6 sm:p-8">
              <SectionHeader title="Work-life balance" description={String(c.work_life_balance.basis)} />
              <div className="grid gap-3 md:grid-cols-2">
                <div className="flex items-center justify-between rounded-xl bg-sage-50 p-3"><span className="text-sm font-semibold">Work pressure</span><Meter value={Number(c.work_life_balance.pressure)} /></div>
                {([["hours", "Typical working hours"], ["weekend", "Weekend workload"], ["remote", "Remote / hybrid"], ["travel", "Travel"], ["client", "Client interaction"], ["flexibility", "Job flexibility"]] as const).map(([k, l]) => (
                  <div key={k} className="rounded-xl bg-sage-50 p-3"><p className="text-xs font-semibold text-ink-500">{l}</p><p className="text-sm text-ink-700">{String(c.work_life_balance[k])}</p></div>
                ))}
              </div>
            </Card>

            {/* F. Skills */}
            <Card className="space-y-4 p-6 sm:p-8">
              <SectionHeader title="Skills and qualifications" />
              <SkillMix technical={c.skills.technical_skills} tools={c.skills.tools} knowledge={c.skills.industry_knowledge} soft={c.skills.soft_skills} />
              <div className="grid gap-5 lg:grid-cols-2">
                {([["Technical skills", c.skills.technical_skills], ["Tools", c.skills.tools], ["Industry knowledge", c.skills.industry_knowledge], ["Soft skills", c.skills.soft_skills], ["Required degrees", c.skills.degrees], ["Relevant certifications", c.skills.certifications]] as const).map(([t, list]) => (
                  <div key={t}><h4 className="text-sm font-bold text-forest-800">{t}</h4><div className="mt-2.5 flex flex-wrap gap-2">{list.map((s) => <Chip key={s} tone={t === "Tools" ? "brand" : "sage"}>{s}</Chip>)}</div></div>
                ))}
              </div>
            </Card>

            {/* G. Outlook */}
            <Card className="space-y-3 p-6 sm:p-8">
              <SectionHeader title="Industry outlook" description="Qualitative editorial view. Quantitative growth is shown only where a cited source exists." />
              <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
                {(c.outlook as any).demand_rating ? <DemandGauge rating={(c.outlook as any).demand_rating} basis={(c.outlook as any).demand_rating_basis} /> : null}
                <p className="self-center text-[16px] leading-7 text-ink-700">{c.outlook.current_demand}</p>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl bg-sage-50 p-5"><h4 className="text-sm font-extrabold text-forest-800">Growth drivers</h4><ul className="mt-1 list-disc pl-5 text-sm text-ink-600">{c.outlook.growth_drivers.map((x) => <li key={x}>{x}</li>)}</ul></div>
                <div className="rounded-2xl bg-sage-50 p-5"><h4 className="text-sm font-extrabold text-forest-800">Emerging technologies</h4><ul className="mt-1 list-disc pl-5 text-sm text-ink-600">{c.outlook.emerging_technologies.map((x) => <li key={x}>{x}</li>)}</ul></div>
                <div className="rounded-2xl bg-sage-50 p-5"><h4 className="text-sm font-extrabold text-forest-800">Geographic demand</h4><div className="mt-2.5 flex flex-wrap gap-2">{c.outlook.geographic_demand.map((x) => <Chip key={x}>{x}</Chip>)}</div></div>
              </div>
              <p className="text-xs text-ink-500">{c.outlook.employment_growth_note}</p>
            </Card>

            {/* H. Exits */}
            <Card className="space-y-4 p-6 sm:p-8">
              <SectionHeader title="Exit opportunities" />
              <div className="grid items-start gap-4 md:grid-cols-[1fr_auto_1fr]">
                <div className="space-y-2"><h4 className="text-sm font-bold text-forest-800">Roles you can move into</h4>{c.exits.roles.map((r) => <div key={r} className="rounded-lg border border-line bg-white px-3 py-2 text-sm">{r}</div>)}</div>
                <div className="hidden self-center rounded-2xl bg-forest-800 px-4 py-6 text-center text-sm font-bold text-white md:block">{c.title}</div>
                <div className="space-y-2"><h4 className="text-sm font-bold text-forest-800">Industries to transition into</h4>{c.exits.industries.map((r) => <div key={r} className="rounded-lg border border-line bg-white px-3 py-2 text-sm">{r}</div>)}</div>
              </div>
              <p className="text-sm text-ink-600"><span className="font-semibold">Additional qualification:</span> {c.exits.qualifications.join("; ")}</p>
            </Card>

            {/* I. Pros / cons */}
            <div className="grid gap-4 md:grid-cols-2">
              <Card className="space-y-3 p-6 sm:p-8"><h3 className="flex items-center gap-2 font-bold text-brand-700"><ThumbsUp size={16} /> Advantages</h3>{c.advantages.map((a) => <p key={a.aspect} className="text-sm"><span className="font-semibold">{a.aspect}. </span>{a.note}</p>)}</Card>
              <Card className="space-y-3 p-6 sm:p-8"><h3 className="flex items-center gap-2 font-bold text-warn-700"><ThumbsDown size={16} /> Disadvantages</h3>{c.disadvantages.map((a) => <p key={a.aspect} className="text-sm"><span className="font-semibold">{a.aspect}. </span>{a.note}</p>)}</Card>
            </div>

            <Card className="space-y-2 p-6 sm:p-8">
              <h3 className="text-sm font-bold text-forest-800">Sources and data freshness</h3>
              <ul className="space-y-1 text-xs text-ink-500">{c.sources.map((s) => <li key={s.name}>{s.url ? <a className="underline" href={s.url} target="_blank" rel="noreferrer">{s.name}</a> : s.name}: {s.covers}{s.last_verified ? ` (verified ${s.last_verified})` : " (reference link, not yet imported)"}</li>)}</ul>
              <p className="text-xs text-ink-400">Dataset last updated {c.last_updated}.</p>
            </Card>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
