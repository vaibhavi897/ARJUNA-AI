/** Interactive skill-gap map (React Flow): the role at the centre, each gap orbiting it. Click a gap for the fix. */
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Background, Controls, Handle, Position, ReactFlow, type Edge, type Node, type NodeProps } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

type Gap = { skill_name: string; status: string; importance: string; expected_proficiency: string; student_proficiency: string | null; points_lost: number; recommendation: string | null };
const COLOR: Record<string, string> = { missing: "#DC2626", claimed_only: "#D97706" };

function GapNode({ data }: NodeProps) {
  const d = data as { label: string; lost: number; color: string; size: number; active: boolean };
  return (
    <div className="grid place-items-center text-center" style={{ width: d.size, height: d.size, borderRadius: 999, background: d.color, color: "#fff", boxShadow: d.active ? `0 0 0 5px ${d.color}44, 0 10px 24px -8px ${d.color}` : "0 4px 12px -6px rgba(0,0,0,.4)", transition: "all .25s", cursor: "pointer", opacity: d.active ? 1 : 0.85 }}>
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div><div style={{ fontSize: 12, fontWeight: 800 }}>-{d.lost}</div><div style={{ fontSize: 9, fontWeight: 700, lineHeight: 1.1, padding: "0 6px" }}>{d.label.length > 16 ? d.label.slice(0, 15) + "…" : d.label}</div></div>
    </div>
  );
}
function RoleNode({ data }: NodeProps) {
  return (
    <div className="grid h-24 w-24 place-items-center rounded-full text-center text-[11px] font-extrabold" style={{ background: "#0C3326", color: "#E6C878", boxShadow: "0 0 0 6px #E6C87833" }}>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />{String((data as any).label)}
    </div>
  );
}
const nodeTypes = { gap: GapNode, role: RoleNode };

export default function SkillMap({ gaps, role }: { gaps: Gap[]; role?: string }) {
  const list = gaps.slice(0, 8);
  const [sel, setSel] = useState(0);
  const { nodes, edges } = useMemo(() => {
    const max = Math.max(...list.map((g) => g.points_lost), 1), R = 150;
    const ns: Node[] = [{ id: "role", type: "role", position: { x: -48, y: -48 }, data: { label: (role || "Your role").slice(0, 16) }, draggable: false, selectable: false }];
    const es: Edge[] = [];
    list.forEach((g, i) => {
      const a = (i / list.length) * Math.PI * 2 - Math.PI / 2, size = 56 + (g.points_lost / max) * 28;
      ns.push({ id: `g${i}`, type: "gap", position: { x: R * 1.25 * Math.cos(a) - size / 2, y: R * Math.sin(a) - size / 2 }, data: { label: g.skill_name, lost: g.points_lost, color: COLOR[g.status] ?? "#64748B", size, active: i === sel } });
      es.push({ id: `e${i}`, source: "role", target: `g${i}`, animated: i === sel, style: { stroke: i === sel ? "#187C4F" : "#CBD5CF", strokeWidth: i === sel ? 2.5 : 1.2 } });
    });
    return { nodes: ns, edges: es };
  }, [list, sel, role]);
  if (list.length < 2) return null;
  const g = list[Math.min(sel, list.length - 1)];
  return (
    <div className="mt-3 grid gap-3 md:grid-cols-[1.2fr_1fr]">
      <div className="h-[340px] overflow-hidden rounded-xl border border-line bg-sage-50/50">
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.15 }} minZoom={0.5} maxZoom={1.6} nodesDraggable nodesConnectable={false} proOptions={{ hideAttribution: true }}
          onNodeClick={(_, n) => { if (n.id.startsWith("g")) setSel(Number(n.id.slice(1))); }} aria-label="Skill gap map">
          <Background gap={18} color="#D5DDD8" /><Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <div className="rounded-xl border border-line bg-white p-4">
        <p className="text-xs font-bold uppercase tracking-wide text-ink-400">Selected gap · click a bubble</p>
        <h4 className="mt-1 text-lg font-extrabold text-forest-900">{g.skill_name}</h4>
        <p className="mt-1 text-xs text-ink-500">Costs {g.points_lost} points · {g.importance} importance · you: {g.student_proficiency ?? "none"} · role expects: {g.expected_proficiency}</p>
        <p className="mt-3 text-sm leading-relaxed text-ink-700">{g.recommendation ?? "Add this skill with a project or certification to close the gap."}</p>
        <Link to="/app/learning/planner?new=1" className="mt-4 inline-flex items-center gap-1.5 text-sm font-bold text-brand-700 hover:text-brand-800">Plan time to close this <ArrowRight size={14} /></Link>
      </div>
    </div>
  );
}
