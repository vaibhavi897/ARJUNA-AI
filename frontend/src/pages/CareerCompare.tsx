/** Compare two or three professions side by side. */
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { AppShell } from "../components/layout";
import { Button, Card, EmptyState, ErrorState, InlineNote, LoadingBlock } from "../components/ui";
import { Chip, useApi, type CareerCard } from "../components/careerverse";
import { request } from "../lib/api";

type Col = {
  id: number; slug: string; title: string; industry: string; responsibilities: string[];
  salary: { us_median: { amount: number; currency: string; reference_year: number } | null; india_available: boolean; india_rows: { level_label: string; amount: number | null; currency: string }[]; note: string | null };
  skills: { technical: string[]; tools: string[]; soft: string[] };
  growth: { current_demand: string; emerging_technologies: string[]; us_employment: { value: number; year: number } | null };
  lifestyle: Record<string, string | number | null>;
  opportunities: { trajectory: string[]; exit_roles: string[]; entry_requirements: string[] };
};
type Result = {
  careers: Col[];
  ai_explanation: { summary?: string; key_differences?: string[]; choose_first_if?: Record<string, string> } | null;
  rule_based_differences: string[];
};

export default function CareerCompare() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const ids = useMemo(() => (params.get("ids") ?? "").split(",").map(Number).filter(Boolean).slice(0, 3), [params]);
  const list = useApi<{ items: CareerCard[] }>("/careers");
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (ids.length < 2) { setResult(null); return; }
    setLoading(true); setError(null);
    request<Result>("/career-comparison", { method: "POST", body: { career_ids: ids } })
      .then(setResult).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [ids.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  function setIds(next: number[]) { navigate(`/app/careerverse/compare?ids=${next.join(",")}`, { replace: true }); }

  const rows: [string, (c: Col) => React.ReactNode][] = [
    ["Responsibilities", (c) => <ul className="list-disc space-y-1 pl-4">{c.responsibilities.map((r) => <li key={r}>{r}</li>)}</ul>],
    ["Salary (sourced only)", (c) => (
      <div className="space-y-1">
        <p>{c.salary.us_median ? `US median ${new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(c.salary.us_median.amount)} (BLS ${c.salary.us_median.reference_year}, US only)` : "No US data"}</p>
        <p className="text-ink-500">{c.salary.india_available ? c.salary.india_rows.map((r) => r.level_label).join(", ") + " (India)" : "No verified India benchmark yet"}</p>
      </div>) ],
    ["Skills", (c) => <div className="flex flex-wrap gap-1">{[...c.skills.technical.slice(0, 4), ...c.skills.tools.slice(0, 2)].map((s) => <Chip key={s}>{s}</Chip>)}</div>],
    ["Growth outlook", (c) => <div className="space-y-1"><p>{c.growth.current_demand}</p><p className="text-ink-500">Emerging: {c.growth.emerging_technologies.join(", ")}</p></div>],
    ["Lifestyle", (c) => <div className="space-y-1"><p>{c.lifestyle.hours}</p><p>Pressure: {c.lifestyle.pressure}/5. {c.lifestyle.remote}</p><p>Travel: {c.lifestyle.travel}. Flexibility: {c.lifestyle.flexibility}</p></div>],
    ["Career ladder", (c) => <p>{c.opportunities.trajectory.join(" > ")}</p>],
    ["Opportunities after", (c) => <p>{c.opportunities.exit_roles.join(", ")}</p>],
    ["Entry requirements", (c) => <p>{c.opportunities.entry_requirements.join("; ")}</p>],
  ];

  return (
    <AppShell title="Compare professions" subtitle="Two or three side by side, using the verified dataset"
      actions={<Link to="/app/careerverse"><Button variant="outline" size="sm" icon={<ArrowLeft size={14} />}>CareerVerse</Button></Link>}>
      <div className="mx-auto max-w-7xl space-y-5">
        <Card className="space-y-3 p-6">
          <p className="text-sm font-semibold">Selected ({ids.length}/3)</p>
          <div className="flex flex-wrap gap-2">
            {ids.map((id) => {
              const c = list.data?.items.find((x) => x.id === id);
              return <button key={id} onClick={() => setIds(ids.filter((x) => x !== id))} className="rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700 hover:bg-brand-100" aria-label={`Remove ${c?.title ?? id}`}>{c?.title ?? `#${id}`} ✕</button>;
            })}
          </div>
          {ids.length < 3 ? (
            <select aria-label="Add a profession" className="input-base max-w-sm" value="" onChange={(e) => e.target.value && setIds([...ids, Number(e.target.value)])}>
              <option value="">Add a profession...</option>
              {list.data?.items.filter((c) => !ids.includes(c.id)).map((c) => <option key={c.id} value={c.id}>{c.title} ({c.industry})</option>)}
            </select>
          ) : null}
        </Card>

        {ids.length < 2 ? <EmptyState title="Choose at least two professions" description="Select them above or tick 'Add to comparison' on the CareerVerse cards." /> : null}
        {loading ? <LoadingBlock label="Comparing" rows={4} /> : null}
        {error ? <ErrorState message={error} /> : null}

        {result && !loading ? (
          <>
            {result.ai_explanation?.summary ? (
              <InlineNote tone="brand">
                <p className="font-semibold">{result.ai_explanation.summary}</p>
                <ul className="mt-1 list-disc pl-4">{result.ai_explanation.key_differences?.map((d) => <li key={d}>{d}</li>)}</ul>
                {result.ai_explanation.choose_first_if ? <ul className="mt-2 space-y-0.5">{Object.entries(result.ai_explanation.choose_first_if).map(([k, v]) => <li key={k}><span className="font-semibold">{k}:</span> {v}</li>)}</ul> : null}
                <p className="mt-1 text-xs opacity-70">Explained by Gemini from the stored data.</p>
              </InlineNote>
            ) : (
              <InlineNote><ul className="list-disc pl-4">{result.rule_based_differences.map((d) => <li key={d}>{d}</li>)}</ul></InlineNote>
            )}
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] table-fixed border-separate border-spacing-0 text-sm">
                <thead>
                  <tr><th className="w-36" />{result.careers.map((c) => (
                    <th key={c.id} className="border-b border-line p-3 text-left align-bottom"><p className="text-xs font-medium text-ink-500">{c.industry}</p><p className="text-base font-bold">{c.title}</p>
                      <Link className="text-xs font-semibold text-brand-700 underline" to={`/app/careerverse/${c.slug}/insights`}>Full insights</Link></th>))}</tr>
                </thead>
                <tbody>
                  {rows.map(([label, render]) => (
                    <tr key={label}><th scope="row" className="border-b border-line p-3 text-left align-top text-xs font-bold uppercase tracking-wide text-forest-700">{label}</th>
                      {result.careers.map((c) => <td key={c.id} className="border-b border-line p-3 align-top text-ink-700">{render(c)}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
