/** Interactive charts for Career Insights (Recharts). */
import { lazy, Suspense, useMemo, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, RadialBar, RadialBarChart, ResponsiveContainer, Sector, Tooltip, XAxis, YAxis } from "recharts";
import { Info } from "lucide-react";
import { Badge } from "./ui";
import { CountUp } from "./fx";
import { cn } from "../lib/utils";

const PALETTE = ["#229A63", "#3F63A8", "#F2B35E", "#A04A86", "#2E8C86", "#E25555", "#6247AA", "#8D5A3B"];
const SalaryRange = lazy(() => import("./SalaryRange"));
const lpa = (n: number) => `₹${(n / 100000).toFixed(n >= 1e7 ? 0 : 1)} LPA`;

type Row = { level: string; salary_type: string; amount: number | null; range_low: number | null; range_high: number | null; location: string | null; experience_min_years: number | null; experience_max_years: number | null; currency: string; is_estimate?: boolean; source_name: string };
export type SalaryData = { india: { rows: Row[] }; us: { rows: Row[] } };

function ActiveSlice(props: any) {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
  return (
    <g>
      <Sector cx={cx} cy={cy} innerRadius={innerRadius - 3} outerRadius={outerRadius + 10} startAngle={startAngle} endAngle={endAngle} fill={fill} style={{ filter: "drop-shadow(0 6px 10px rgba(0,0,0,.25))", transition: "all .25s" }} />
    </g>
  );
}

function Box({ title, hint, children, className }: { title: string; hint?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("rounded-2xl border border-line bg-white p-5 shadow-sm", className)}>
      <h4 className="font-extrabold text-forest-800">{title}</h4>
      {hint ? <p className="mb-2 text-xs text-ink-500">{hint}</p> : null}
      {children}
    </div>
  );
}

/** India salary explorer: level tabs, base-vs-variable donut, experience curve, city bars. */
export function SalaryExplorer({ salary }: { salary: SalaryData }) {
  const rows = salary.india.rows;
  const [level, setLevel] = useState<"entry" | "mid" | "senior">("mid");
  const [slice, setSlice] = useState(0);
  const [city, setCity] = useState<string | null>(null);

  const base = (l: string) => rows.find((r) => r.level === l && r.salary_type === "base" && !r.location);
  const total = (l: string) => rows.find((r) => r.level === l && r.salary_type === "total_compensation");
  const estimate = rows.some((r) => r.is_estimate);

  const curve = (["entry", "mid", "senior"] as const).map((l) => {
    const b = base(l), t = total(l);
    return { name: l === "entry" ? "Entry" : l === "mid" ? "Mid" : "Senior", years: b?.experience_min_years != null ? `${b.experience_min_years}-${b.experience_max_years ?? "+"} yrs` : "", base: b?.amount ?? 0, total: t?.amount ?? 0, low: b?.range_low ?? 0, high: t?.range_high ?? b?.range_high ?? 0, key: l };
  });
  const b = base(level), t = total(level);
  const donut = b && t ? [{ name: "Base pay", value: b.amount! }, { name: "Bonus, variable and equity", value: Math.max(0, t.amount! - b.amount!) }] : [];
  const cities = rows.filter((r) => r.location && r.salary_type === "base").map((r) => ({ name: r.location!, v: r.amount!, lo: r.range_low!, hi: r.range_high! })).sort((a, z) => z.v - a.v);
  const pickedCity = cities.find((c) => c.name === city) ?? cities[0];

  if (!rows.length) return null;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="text-lg font-extrabold">India</h4>
        {estimate ? <Badge tone="warn"><Info size={12} /> Estimate: illustrative ranges, not survey data</Badge> : <Badge tone="brand">Sourced benchmarks</Badge>}
        <div className="ml-auto inline-flex rounded-xl bg-sage-100 p-1" role="tablist" aria-label="Experience level">
          {(["entry", "mid", "senior"] as const).map((l) => (
            <button key={l} role="tab" aria-selected={level === l} onClick={() => setLevel(l)} className={cn("rounded-lg px-4 py-1.5 text-sm font-bold capitalize transition-all", level === l ? "bg-white text-forest-800 shadow" : "text-ink-500 hover:text-ink-800")}>{l}</button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Box title="Where the money comes from" hint={`${level[0].toUpperCase() + level.slice(1)} level. Hover a slice.`}>
          {donut.length ? (
            <div className="relative h-60">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={donut} dataKey="value" innerRadius={62} outerRadius={88} paddingAngle={3} activeIndex={slice} activeShape={ActiveSlice} onMouseEnter={(_, i) => setSlice(i)} stroke="none">
                    {donut.map((_, i) => <Cell key={i} fill={PALETTE[i]} />)}
                  </Pie>
                  <Tooltip formatter={(v: number) => lpa(v)} />
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
                <div><p className="text-[11px] font-semibold text-ink-500">{donut[slice]?.name}</p><p className="text-xl font-extrabold"><CountUp key={`${level}${slice}`} value={donut[slice]?.value ?? 0} format={lpa} /></p></div>
              </div>
            </div>
          ) : <p className="text-sm text-ink-500">No breakdown for this level.</p>}
          <div className="mt-1 flex flex-wrap gap-3 text-xs">{donut.map((d, i) => <span key={d.name} className="inline-flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full" style={{ background: PALETTE[i] }} />{d.name}</span>)}</div>
        </Box>

        <Box title="Pay growth with experience" hint="Click a point to switch level. Band shows the range.">
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={curve} margin={{ left: -10, right: 8, top: 8 }} onClick={(e: any) => e?.activePayload && setLevel(e.activePayload[0].payload.key)}>
                <defs>
                  <linearGradient id="gBase" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#229A63" stopOpacity={0.55} /><stop offset="100%" stopColor="#229A63" stopOpacity={0.05} /></linearGradient>
                  <linearGradient id="gTot" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#3F63A8" stopOpacity={0.4} /><stop offset="100%" stopColor="#3F63A8" stopOpacity={0.03} /></linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" fontSize={12} />
                <YAxis fontSize={11} tickFormatter={(v) => `${Math.round(v / 100000)}L`} width={42} />
                <Tooltip formatter={(v: number, n: string) => [lpa(v), n]} labelFormatter={(l, p) => `${l} ${p?.[0]?.payload?.years ?? ""}`} />
                <Area type="monotone" dataKey="total" name="Total compensation" stroke="#3F63A8" strokeWidth={2.5} fill="url(#gTot)" activeDot={{ r: 7 }} />
                <Area type="monotone" dataKey="base" name="Base pay" stroke="#229A63" strokeWidth={2.5} fill="url(#gBase)" activeDot={{ r: 7 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Box>

        <Box title="Mid-level pay by city" hint="Click a bar to see its range.">
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={cities} layout="vertical" margin={{ left: 12, right: 12 }} onClick={(e: any) => e?.activeLabel && setCity(e.activeLabel)}>
                <XAxis type="number" hide domain={[0, "dataMax"]} />
                <YAxis type="category" dataKey="name" width={78} fontSize={12} axisLine={false} tickLine={false} />
                <Tooltip formatter={(v: number) => lpa(v)} cursor={{ fill: "rgba(34,154,99,.08)" }} />
                <Bar dataKey="v" radius={[0, 8, 8, 0]} animationDuration={900}>
                  {cities.map((c) => <Cell key={c.name} fill={c.name === pickedCity?.name ? "#229A63" : "#A8D5BD"} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          {pickedCity ? <p className="mt-2 rounded-xl bg-sage-50 px-3 py-2 text-sm"><b>{pickedCity.name}</b>: {lpa(pickedCity.v)} typical, range {lpa(pickedCity.lo)} to {lpa(pickedCity.hi)}</p> : null}
        </Box>
      </div>
      {curve.some((c) => c.high > 0) ? (
        <Box title="Pay range by level" hint="Bars show the typical range; lines show base and total compensation.">
          <Suspense fallback={<div className="h-[300px] animate-pulse rounded-xl bg-sage-100" />}>
            <SalaryRange data={curve.filter((c) => c.high > 0).map((c) => ({ name: c.name, low: c.low || c.base, high: c.high, base: c.base, total: c.total || undefined }))} fmt={lpa} />
          </Suspense>
        </Box>
      ) : null}
      {estimate ? <p className="text-xs text-ink-500">Estimates are editorial planning ranges for fresh-to-senior base pay in India. For real offers, check current salary surveys and company bands. Replace any row with a sourced benchmark in <code>india_salary_benchmarks.json</code>.</p> : null}
    </div>
  );
}

/** Employers by industry: click a slice to filter the company list. */
export function CompanyExplorer({ companies }: { companies: { name: string; industry: string; job_titles: string[]; regions: string[] }[] }) {
  const [pick, setPick] = useState<string | null>(null);
  const [hover, setHover] = useState<number | undefined>(undefined);
  const groups = useMemo(() => {
    const m = new Map<string, number>();
    companies.forEach((c) => m.set(c.industry, (m.get(c.industry) ?? 0) + 1));
    return [...m].map(([name, value]) => ({ name, value }));
  }, [companies]);
  const shown = pick ? companies.filter((c) => c.industry === pick) : companies;
  return (
    <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
      <Box title="Employers by industry" hint="Click a slice to filter. Click again to clear.">
        <div className="h-60">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={groups} dataKey="value" innerRadius={52} outerRadius={86} paddingAngle={2} stroke="none" activeIndex={hover ?? (pick ? groups.findIndex((g) => g.name === pick) : undefined)} activeShape={ActiveSlice}
                onMouseEnter={(_, i) => setHover(i)} onMouseLeave={() => setHover(undefined)} onClick={(d: any) => setPick((p) => (p === d.name ? null : d.name))}>
                {groups.map((g, i) => <Cell key={g.name} fill={PALETTE[i % PALETTE.length]} opacity={pick && pick !== g.name ? 0.35 : 1} style={{ cursor: "pointer" }} />)}
              </Pie>
              <Tooltip formatter={(v: number, n: string) => [`${v} employer${v > 1 ? "s" : ""}`, n]} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">{groups.map((g, i) => <button key={g.name} onClick={() => setPick((p) => (p === g.name ? null : g.name))} className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 transition", pick === g.name ? "border-forest-800 bg-forest-800 text-white" : "border-line hover:border-brand-400")}><i className="h-2 w-2 rounded-full" style={{ background: PALETTE[i % PALETTE.length] }} />{g.name}</button>)}</div>
      </Box>
      <div className="grid content-start gap-3 sm:grid-cols-2">
        {shown.map((co) => (
          <div key={co.name} className="rounded-2xl border border-line bg-white p-4 transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-md">
            <p className="font-bold">{co.name}</p><p className="text-xs text-ink-500">{co.industry}</p>
            <p className="mt-2 text-xs text-ink-600"><b>Relevant titles:</b> {co.job_titles.join(", ")}</p>
            <p className="mt-1 text-xs text-ink-600"><b>Presence:</b> {co.regions.join(", ")}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Skill mix donut + balance radar. */
export function SkillMix({ technical, tools, knowledge, soft }: { technical: string[]; tools: string[]; knowledge: string[]; soft: string[] }) {
  const data = [{ name: "Technical", value: technical.length }, { name: "Tools", value: tools.length }, { name: "Knowledge", value: knowledge.length }, { name: "Soft skills", value: soft.length }];
  const [i, setI] = useState(0);
  const lists = [technical, tools, knowledge, soft];
  return (
    <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
      <Box title="Skill mix" hint="Hover a slice to list its skills.">
        <div className="relative h-56">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" innerRadius={55} outerRadius={82} paddingAngle={3} stroke="none" activeIndex={i} activeShape={ActiveSlice} onMouseEnter={(_, k) => setI(k)}>
                {data.map((_, k) => <Cell key={k} fill={PALETTE[k]} />)}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 grid place-items-center text-center"><div><p className="text-3xl font-extrabold">{data[i].value}</p><p className="text-xs text-ink-500">{data[i].name}</p></div></div>
        </div>
      </Box>
      <Box title={data[i].name} hint="What the profession asks for in this area">
        <div className="flex flex-wrap gap-2">{lists[i].map((s, k) => <span key={s} className="cv-pop rounded-full px-3 py-1.5 text-sm font-medium text-white" style={{ background: PALETTE[i], animationDelay: `${k * 50}ms` }}>{s}</span>)}</div>
      </Box>
    </div>
  );
}

export function DemandGauge({ rating, basis }: { rating: number; basis?: string }) {
  const labels = ["", "Low", "Modest", "Steady", "High", "Very high"];
  return (
    <Box title="Hiring demand" hint={basis}>
      <div className="relative h-44">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart innerRadius="70%" outerRadius="100%" data={[{ v: rating }]} startAngle={210} endAngle={-30}>
            <PolarAngleAxis type="number" domain={[0, 5]} tick={false} />
            <RadialBar dataKey="v" cornerRadius={14} background={{ fill: "#E1EAE4" }} fill="#229A63" animationDuration={1200} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 grid place-items-center text-center"><div><p className="text-2xl font-extrabold text-brand-700">{labels[rating]}</p><p className="text-xs text-ink-500">{rating} / 5</p></div></div>
      </div>
    </Box>
  );
}

export function FitRadar({ components }: { components: Record<string, { label: string; value: number | null }> }) {
  const data = Object.values(components).map((c) => ({ axis: c.label.replace(" alignment", "").replace(" relevance", ""), v: c.value ?? 0 }));
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke="#CBDAD1" /><PolarAngleAxis dataKey="axis" fontSize={11} /><PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
          <Radar dataKey="v" name="Your alignment" stroke="#229A63" strokeWidth={2.5} fill="#229A63" fillOpacity={0.35} animationDuration={900} />
          <Tooltip formatter={(v: number) => `${Math.round(v)}/100`} /><Legend />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
