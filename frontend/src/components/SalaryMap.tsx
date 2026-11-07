/** World salary map: pick a country on the map (or from the list) and see the average pay for this role there. */
import { useEffect, useMemo, useRef, useState } from "react";
import { geoNaturalEarth1, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import { Info, Minus, Plus, RotateCcw } from "lucide-react";
import { Badge } from "./ui";
import { request } from "../lib/api";
import { cn } from "../lib/utils";

type Levels = { entry: number | null; mid: number | null; senior: number | null };
type Country = { name: string; code: string; currency: string; kind: "us_data" | "india_data" | "modelled"; is_estimate: boolean; factor?: number; levels: Levels; source: string; source_url: string | null };
type World = { available: boolean; countries: Country[]; note: string };

const W = 960, H = 500;
const fmt = (c: Country, n: number | null) => {
  if (n == null) return "n/a";
  if (c.currency === "INR") return `₹${(n / 100000).toFixed(n >= 1e7 ? 0 : 1)} LPA`;
  return `$${Math.round(n).toLocaleString("en-US")}`;
};
const shade = (c: Country | undefined) => {
  if (!c) return "#E3EAE5";
  if (c.kind === "india_data") return "#187C4F";
  if (c.kind === "us_data") return "#0C3326";
  const f = c.factor ?? 0.3; // modelled: lighter for lower-pay markets
  return f >= 0.7 ? "#34A06C" : f >= 0.5 ? "#6CC29A" : f >= 0.25 ? "#A7DBC1" : "#CDEBDB";
};
const ALIAS: Record<string, string> = { "United States of America": "United States of America", "United Arab Emirates": "United Arab Emirates" };

export default function SalaryMap({ slug, role }: { slug: string; role: string }) {
  const [world, setWorld] = useState<World | null>(null);
  const [geo, setGeo] = useState<{ id: string; name: string; d: string }[]>([]);
  const [sel, setSel] = useState<string>("United States of America");
  const [hover, setHover] = useState<string | null>(null);
  const [view, setView] = useState({ k: 1, x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    request<World>(`/careers/${slug}/salary-world`).then((w) => live && setWorld(w)).catch((e) => live && setErr((e as Error).message));
    return () => { live = false; };
  }, [slug]);

  useEffect(() => {
    let live = true;
    Promise.all([import("world-atlas/countries-110m.json"), Promise.resolve()]).then(([topo]) => {
      if (!live) return;
      const t: any = (topo as any).default ?? topo;
      const fc: any = feature(t, t.objects.countries);
      const proj = geoNaturalEarth1().fitSize([W, H], fc);
      const path = geoPath(proj);
      setGeo(fc.features.map((f: any) => ({ id: String(f.id), name: f.properties.name as string, d: path(f) ?? "" })).filter((g: any) => g.d));
    }).catch(() => live && setErr("Could not load the map."));
    return () => { live = false; };
  }, []);

  const byName = useMemo(() => new Map((world?.countries ?? []).map((c) => [ALIAS[c.name] ?? c.name, c])), [world]);
  const chosen = byName.get(sel);
  const names = useMemo(() => (world?.countries ?? []).map((c) => c.name).sort((a, b) => a.localeCompare(b)), [world]);
  const us = byName.get("United States of America");

  if (err) return <p className="text-sm text-ink-500">{err}</p>;
  if (world && !world.available) return <p className="text-sm text-ink-500">No salary data for {role} yet, so there is nothing to show on the map.</p>;

  const zoom = (f: number) => setView((v) => { const k = Math.min(6, Math.max(1, v.k * f)); return { k, x: v.x * (k / v.k), y: v.y * (k / v.k) }; });

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
      <div className="relative overflow-hidden rounded-2xl border border-line bg-gradient-to-b from-sky-50 to-brand-50/60">
        <svg viewBox={`0 0 ${W} ${H}`} className="block w-full touch-none select-none" role="img" aria-label={`Map of average ${role} salary by country`}
          onPointerDown={(e) => { drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y }; (e.target as Element).setPointerCapture?.(e.pointerId); }}
          onPointerMove={(e) => { if (!drag.current) return; const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect(); const s = W / r.width; setView((v) => ({ ...v, x: drag.current!.vx + (e.clientX - drag.current!.x) * s, y: drag.current!.vy + (e.clientY - drag.current!.y) * s })); }}
          onPointerUp={() => { drag.current = null; }}
          onWheel={(e) => { e.preventDefault(); zoom(e.deltaY < 0 ? 1.2 : 1 / 1.2); }}>
          <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`} style={{ transformOrigin: "0 0" }}>
            {geo.map((g) => {
              const c = byName.get(g.name);
              const on = g.name === sel;
              return (
                <path key={g.id} d={g.d} fill={shade(c)} stroke={on ? "#E6A817" : "#fff"} strokeWidth={(on ? 1.8 : 0.5) / view.k}
                  className={c ? "cursor-pointer transition-opacity hover:opacity-80" : ""} opacity={hover && hover !== g.name && c ? 0.9 : 1}
                  onClick={() => { if (c) setSel(g.name); }} onMouseEnter={() => setHover(g.name)} onMouseLeave={() => setHover(null)}>
                  <title>{c ? `${g.name}: ${fmt(c, c.levels.mid)} (mid level)` : `${g.name}: no data`}</title>
                </path>
              );
            })}
          </g>
        </svg>
        <div className="absolute right-3 top-3 flex flex-col gap-1.5">
          <button aria-label="Zoom in" onClick={() => zoom(1.4)} className="grid h-8 w-8 place-items-center rounded-lg bg-white shadow hover:bg-brand-50"><Plus size={16} /></button>
          <button aria-label="Zoom out" onClick={() => zoom(1 / 1.4)} className="grid h-8 w-8 place-items-center rounded-lg bg-white shadow hover:bg-brand-50"><Minus size={16} /></button>
          <button aria-label="Reset map" onClick={() => setView({ k: 1, x: 0, y: 0 })} className="grid h-8 w-8 place-items-center rounded-lg bg-white shadow hover:bg-brand-50"><RotateCcw size={15} /></button>
        </div>
        <div className="absolute bottom-2 left-3 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg bg-white/85 px-2.5 py-1.5 text-[11px] font-semibold text-ink-600">
          <span className="flex items-center gap-1"><i className="h-2.5 w-2.5 rounded-sm" style={{ background: "#0C3326" }} />US data</span>
          <span className="flex items-center gap-1"><i className="h-2.5 w-2.5 rounded-sm" style={{ background: "#187C4F" }} />India data</span>
          <span className="flex items-center gap-1"><i className="h-2.5 w-2.5 rounded-sm" style={{ background: "#6CC29A" }} />Modelled estimate</span>
          <span className="flex items-center gap-1"><i className="h-2.5 w-2.5 rounded-sm" style={{ background: "#E3EAE5" }} />No data</span>
        </div>
        {!world ? <div className="absolute inset-0 grid place-items-center bg-white/60 text-sm font-semibold text-ink-500">Loading salaries…</div> : null}
      </div>

      <div className="space-y-3">
        <label className="block text-xs font-bold uppercase tracking-wide text-ink-500">Country
          <select value={sel} onChange={(e) => setSel(e.target.value)} className="input-base mt-1 normal-case">
            {names.map((n) => <option key={n} value={n}>{n === "United States of America" ? "United States" : n}</option>)}
          </select>
        </label>
        {chosen ? (
          <div className="rounded-2xl border border-line bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-lg font-extrabold text-forest-900">{chosen.name === "United States of America" ? "United States" : chosen.name}</h4>
              <Badge tone={chosen.kind === "modelled" || chosen.is_estimate ? "warn" : "brand"}>{chosen.kind === "modelled" ? "Modelled estimate" : chosen.is_estimate ? "Estimate" : "Sourced"}</Badge>
            </div>
            <p className="mt-0.5 text-xs text-ink-500">Average annual pay for {role}</p>
            <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
              {([["Entry", chosen.levels.entry], ["Mid", chosen.levels.mid], ["Senior", chosen.levels.senior]] as const).map(([l, v]) => (
                <div key={l} className="rounded-xl bg-brand-50 px-1 py-2.5"><dt className="text-[11px] font-semibold text-ink-500">{l}</dt><dd className="mt-0.5 text-sm font-extrabold text-brand-700">{fmt(chosen, v)}</dd></div>
              ))}
            </dl>
            {chosen.kind === "modelled" && us?.levels.mid && chosen.levels.mid ? (
              <p className="mt-3 text-xs text-ink-600">About {Math.round((100 * chosen.levels.mid) / us.levels.mid)}% of the US mid-level figure.</p>
            ) : null}
            <p className={cn("mt-3 flex gap-1.5 text-[11px] leading-relaxed text-ink-500")}><Info size={13} className="mt-0.5 shrink-0" />{chosen.source}</p>
          </div>
        ) : null}
        <p className="text-[11px] leading-relaxed text-ink-500">{world?.note}</p>
      </div>
    </div>
  );
}
