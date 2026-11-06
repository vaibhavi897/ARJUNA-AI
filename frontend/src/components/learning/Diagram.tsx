/** Renders a Gemini-produced node/edge diagram as layered SVG. No diagram library needed. */
import { useMemo } from "react";

type N = { id: string; label: string };
type E = { source?: string; target?: string; from?: string; to?: string; label?: string };

function wrap(label: string, max = 16): string[] {
  const words = label.split(" ");
  const lines: string[] = [];
  let cur = "";
  for (const w of words) {
    if ((cur + " " + w).trim().length > max && cur) { lines.push(cur); cur = w; } else cur = (cur + " " + w).trim();
  }
  if (cur) lines.push(cur);
  return lines.slice(0, 3);
}

export function Diagram({ nodes, edges, title }: { nodes: N[]; edges: E[]; title?: string }) {
  const layout = useMemo(() => {
    const ids = new Set(nodes.map((n) => n.id));
    const es = edges.map((e) => ({ a: e.source ?? e.from ?? "", b: e.target ?? e.to ?? "", label: e.label ?? "" })).filter((e) => ids.has(e.a) && ids.has(e.b) && e.a !== e.b);
    const level: Record<string, number> = {};
    const incoming = new Map<string, number>();
    nodes.forEach((n) => incoming.set(n.id, 0));
    es.forEach((e) => incoming.set(e.b, (incoming.get(e.b) ?? 0) + 1));
    const queue = nodes.filter((n) => !incoming.get(n.id)).map((n) => n.id);
    if (!queue.length) queue.push(nodes[0].id);
    queue.forEach((id) => (level[id] = 0));
    for (let guard = 0; guard < nodes.length * 4 && queue.length; guard++) {
      const id = queue.shift()!;
      es.filter((e) => e.a === id).forEach((e) => {
        if (level[e.b] === undefined || level[e.b] < level[id] + 1) { if (level[id] + 1 <= nodes.length) { level[e.b] = level[id] + 1; queue.push(e.b); } }
      });
    }
    nodes.forEach((n) => { if (level[n.id] === undefined) level[n.id] = 0; });
    const cols: string[][] = [];
    nodes.forEach((n) => { (cols[level[n.id]] ||= []).push(n.id); });
    const W = 150, H = 56, GX = 70, GY = 28;
    const pos: Record<string, { x: number; y: number }> = {};
    const maxRows = Math.max(...cols.filter(Boolean).map((c) => c.length));
    cols.forEach((c, ci) => c?.forEach((id, ri) => (pos[id] = { x: 20 + ci * (W + GX), y: 20 + ri * (H + GY) + ((maxRows - c.length) * (H + GY)) / 2 })));
    return { es, pos, W, H, width: 40 + cols.length * (W + GX) - GX, height: 40 + maxRows * (H + GY) - GY };
  }, [nodes, edges]);

  const colors = ["#229A63", "#3F63A8", "#A04A86", "#B07A2B", "#2E8C86", "#6247AA"];
  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-white p-3">
      <svg viewBox={`0 0 ${layout.width} ${layout.height}`} style={{ minWidth: Math.min(layout.width, 900), width: "100%" }} role="img" aria-label={title ?? "Concept diagram"}>
        <defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#94A3B8" /></marker></defs>
        {layout.es.map((e, i) => {
          const a = layout.pos[e.a], b = layout.pos[e.b];
          const forward = b.x > a.x;
          const x1 = forward ? a.x + layout.W : a.x + layout.W / 2, y1 = forward ? a.y + layout.H / 2 : b.y > a.y ? a.y + layout.H : a.y;
          const x2 = forward ? b.x : b.x + layout.W / 2, y2 = forward ? b.y + layout.H / 2 : b.y > a.y ? b.y : b.y + layout.H;
          const mx = (x1 + x2) / 2;
          const d = forward ? `M${x1} ${y1} C${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}` : `M${x1} ${y1} L${x2} ${y2}`;
          return <g key={i}><path d={d} fill="none" stroke="#94A3B8" strokeWidth="1.8" markerEnd="url(#arr)" className="cv-scribble" style={{ animationDuration: "1.2s", animationIterationCount: 1 }} />{e.label ? <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 5} textAnchor="middle" fontSize="10" fill="#5F736A" fontWeight="600">{e.label}</text> : null}</g>;
        })}
        {nodes.map((n, i) => {
          const p = layout.pos[n.id];
          const lines = wrap(n.label);
          return (
            <g key={n.id} className="cv-pop" style={{ animationDelay: `${i * 60}ms`, transformBox: "fill-box", transformOrigin: "center" }}>
              <rect x={p.x} y={p.y} width={layout.W} height={layout.H} rx="12" fill={colors[i % colors.length]} opacity="0.12" stroke={colors[i % colors.length]} strokeWidth="1.6" />
              {lines.map((l, k) => <text key={k} x={p.x + layout.W / 2} y={p.y + layout.H / 2 + (k - (lines.length - 1) / 2) * 14 + 4} textAnchor="middle" fontSize="12" fontWeight="700" fill="#13241C">{l}</text>)}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
