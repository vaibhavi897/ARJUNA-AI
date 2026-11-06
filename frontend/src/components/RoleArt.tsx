/** Role-specific workplaces, outfits and transitions for the 12 featured professions. */
import { L } from "./look";

export type RoleCfg = { decor: string; outfit: string; suit: boolean; tr: number; screen?: string };

export const ROLES: Record<string, RoleCfg> = {
  "investment-banker": { decor: "bank", outfit: "suit", suit: true, tr: 1, screen: "analysis" },
  "software-engineer": { decor: "code", outfit: "hoodie", suit: false, tr: 2, screen: "code" },
  "data-scientist": { decor: "data", outfit: "glasses", suit: false, tr: 3, screen: "analysis" },
  "cybersecurity-analyst": { decor: "soc", outfit: "headset", suit: false, tr: 4, screen: "security" },
  "ux-designer": { decor: "design", outfit: "cardigan", suit: false, tr: 5, screen: "design" },
  "product-manager": { decor: "kanban", outfit: "lanyard", suit: false, tr: 6, screen: "desk" },
  "management-consultant": { decor: "frame", outfit: "suit", suit: true, tr: 7, screen: "desk" },
  "corporate-lawyer": { decor: "law", outfit: "suit", suit: true, tr: 8, screen: "document" },
  "research-scientist": { decor: "lab", outfit: "labcoat", suit: false, tr: 9, screen: "analysis" },
  "supply-chain-manager": { decor: "warehouse", outfit: "vest", suit: false, tr: 10, screen: "desk" },
  "hr-manager": { decor: "hr", outfit: "blazer", suit: false, tr: 11, screen: "document" },
  actuary: { decor: "actuary", outfit: "sweater", suit: false, tr: 12, screen: "analysis" },
};

/** Clothing and accessories drawn over the base figure. */
export function Outfit({ sit }: { sit?: boolean }) {
  const hx = sit ? 3 : 0, hy = sit ? -62 : -95;
  const top = sit ? -46 : -80, bot = sit ? 0 : -34;
  const o = L.outfit;
  const specs = ["hoodie", "glasses", "labcoat", "sweater", "cardigan", "lanyard"].includes(o);
  return (
    <g>
      {o === "labcoat" ? <g><rect x="-15" y={top} width="30" height={bot - top + (sit ? 0 : 14)} rx="9" fill="#fff" opacity="0.96" /><path d={`M0 ${top} V${bot + (sit ? 0 : 10)}`} stroke="#CBD5E1" strokeWidth="1.5" /><rect x="5" y={top + 20} width="7" height="9" fill="#E2E8F0" /></g> : null}
      {o === "vest" ? <g><rect x="-14" y={top} width="28" height={bot - top} rx="9" fill="#F59E0B" opacity="0.95" /><rect x="-14" y={top + 18} width="28" height="4" fill="#FEF3C7" /><rect x="-14" y={top + 30} width="28" height="4" fill="#FEF3C7" /></g> : null}
      {o === "hoodie" ? <g><rect x="-14" y={top} width="28" height={bot - top} rx="9" fill="#3B4A72" opacity="0.92" /><path d={`M${hx - 15} ${hy + 12} Q${hx} ${hy + 30} ${hx + 15} ${hy + 12} L${hx + 15} ${hy + 20} Q${hx} ${hy + 38} ${hx - 15} ${hy + 20}Z`} fill="#3B4A72" /><path d={`M-3 ${top + 6} V${top + 18} M3 ${top + 6} V${top + 18}`} stroke="#fff" strokeWidth="1.4" /></g> : null}
      {o === "cardigan" ? <g><rect x="-14" y={top} width="28" height={bot - top} rx="9" fill="#A04A86" opacity="0.92" /><path d={`M0 ${top} V${bot}`} stroke="#6B2D5A" strokeWidth="1.5" /></g> : null}
      {o === "blazer" ? <g><rect x="-14" y={top} width="28" height={bot - top} rx="9" fill="#2F6F8F" opacity="0.95" /><path d={`M0 ${top} L-7 ${top + 18} M0 ${top} L7 ${top + 18}`} stroke="#fff" strokeWidth="2" /></g> : null}
      {o === "sweater" ? <g><rect x="-14" y={top} width="28" height={bot - top} rx="9" fill="#6247AA" opacity="0.92" /><rect x="-14" y={top} width="28" height="5" rx="2" fill="#C4B5FD" /></g> : null}
      {specs ? <g fill="none" stroke="#111" strokeWidth="1.6"><circle cx={hx - 4.5} cy={hy + 1} r="3.6" /><circle cx={hx + 4.5} cy={hy + 1} r="3.6" /><path d={`M${hx - 1} ${hy + 1} H${hx + 1}`} /></g> : null}
      {o === "vest" ? <g><path d={`M${hx - 14} ${hy - 4} Q${hx} ${hy - 22} ${hx + 14} ${hy - 4}Z`} fill="#FACC15" /><rect x={hx - 16} y={hy - 5} width="32" height="4" rx="2" fill="#EAB308" /></g> : null}
      {o === "headset" || o === "blazer" ? <g fill="none" stroke="#0F172A" strokeWidth="2.2" strokeLinecap="round"><path d={`M${hx - 12} ${hy} Q${hx - 12} ${hy - 16} ${hx} ${hy - 16} Q${hx + 12} ${hy - 16} ${hx + 12} ${hy}`} /><path d={`M${hx + 12} ${hy} Q${hx + 12} ${hy + 9} ${hx + 5} ${hy + 10}`} /><circle cx={hx - 12} cy={hy + 1} r="3" fill="#0F172A" /></g> : null}
      {o === "lanyard" ? <g><path d={`M${hx - 4} ${hy + 12} L0 ${top + 22} L${hx + 4} ${hy + 12}`} stroke="#229A63" strokeWidth="2" fill="none" /><rect x="-4" y={top + 22} width="8" height="10" rx="1" fill="#fff" /></g> : null}
      {o === "labcoat" ? <rect x={hx - 11} y={hy - 1} width="22" height="5" rx="2.5" fill="#7DD3FC" opacity="0.8" /> : null}
    </g>
  );
}

const bars = (n: number, x0: number, y0: number, w: number, hmax: number, colors: string[]) =>
  Array.from({ length: n }, (_, i) => {
    const h = hmax * (0.35 + ((i * 37) % 60) / 100);
    return <rect key={i} className="cv-bar" style={{ animationDelay: `${i * 0.13}s`, transformBox: "fill-box", transformOrigin: "50% 100%" }} x={x0 + i * (w + 3)} y={y0 - h} width={w} height={h} fill={colors[i % colors.length]} />;
  });

/** Distinct animated backdrop for each featured profession. */
export function RoleDecor({ kind }: { kind: string }) {
  switch (kind) {
    case "bank":
      return (<g><rect x="14" y="26" width="150" height="92" rx="4" fill="#06120D" opacity="0.85" />{[0, 1, 2, 3, 4].map((r) => <g key={r}><rect x="22" y={36 + r * 16} width="34" height="5" rx="2" fill="#CBD5E1" opacity="0.7" /><rect x={64} y={35 + r * 16} width={20 + ((r * 23) % 40)} height="6" rx="2" fill={r % 2 ? "#EF4444" : "#22C55E"} className="cv-bar" style={{ animationDelay: `${r * 0.2}s`, transformBox: "fill-box", transformOrigin: "0 50%" }} /></g>)}<path d="M100 108 L112 90 L124 98 L140 70 L156 78" stroke="#F2B35E" strokeWidth="2.5" fill="none" className="cv-scribble" /></g>);
    case "code":
      return (<g>{[0, 1].map((m) => <g key={m} transform={`translate(${16 + m * 78},28)`}><rect width="72" height="84" rx="4" fill="#0B1220" stroke="#334155" strokeWidth="2" />{[0, 1, 2, 3, 4, 5, 6].map((l) => <rect key={l} x={6 + (l % 3) * 5} y={8 + l * 11} width={22 + ((l * 17 + m * 9) % 36)} height="3.5" rx="1.5" fill={["#7EE0B0", "#7FB0FF", "#F2B35E", "#C79BFF"][(l + m) % 4]} className="su-twinkle" style={{ animationDelay: `${l * 0.4}s` }} />)}</g>)}</g>);
    case "data":
      return (<g><rect x="14" y="26" width="168" height="92" rx="5" fill="#0F1630" opacity="0.85" /><circle cx="56" cy="72" r="24" fill="none" stroke="#7EE0B0" strokeWidth="9" strokeDasharray="90 150" /><circle cx="56" cy="72" r="24" fill="none" stroke="#F2B35E" strokeWidth="9" strokeDasharray="40 150" strokeDashoffset="-90" /><circle cx="56" cy="72" r="24" fill="none" stroke="#C79BFF" strokeWidth="9" strokeDasharray="20 150" strokeDashoffset="-130" />{bars(6, 104, 108, 9, 60, ["#7EE0B0", "#7FB0FF"])}</g>);
    case "soc":
      return (<g>{[0, 1, 2].map((r) => <g key={r} transform={`translate(${16 + r * 40},34)`}><rect width="34" height="86" rx="3" fill="#0B1220" stroke="#334155" strokeWidth="2" />{[0, 1, 2, 3, 4, 5, 6].map((l) => <g key={l}><rect x="4" y={6 + l * 11} width="20" height="6" rx="1" fill="#1E293B" /><circle cx="29" cy={9 + l * 11} r="2" fill={(l + r) % 3 ? "#22C55E" : "#EF4444"} className="su-twinkle" style={{ animationDelay: `${(l + r) * 0.3}s` }} /></g>)}</g>)}<g transform="translate(150,34)"><rect width="110" height="76" rx="4" fill="#06120D" stroke="#1E293B" strokeWidth="2" /><path d="M10 60 Q30 20 50 44 T90 20" stroke="#22C55E" strokeWidth="2.5" fill="none" className="cv-scribble" /><circle cx="90" cy="20" r="4" fill="#EF4444" className="cv-pop" /></g></g>);
    case "design":
      return (<g>{[0, 1, 2].map((i) => <g key={i} transform={`translate(${16 + i * 52},32)`}><rect width="46" height="70" rx="4" fill="#fff" opacity="0.92" /><rect x="5" y="6" width="36" height="14" rx="2" fill={["#C79BFF", "#F2B35E", "#7EE0B0"][i]} /><rect x="5" y="26" width="22" height="4" rx="2" fill="#CBD5E1" /><rect x="5" y="34" width="36" height="22" rx="2" fill="#E2E8F0" /><rect x="5" y="60" width="16" height="5" rx="2.5" fill="#229A63" /></g>)}{["#E86F6F", "#F2B35E", "#7EE0B0", "#6FB6E8", "#9B7BE0"].map((c, i) => <circle key={c} cx={26 + i * 22} cy="122" r="8" fill={c} className="cv-pop" style={{ animationDelay: `${i * 0.15}s` }} />)}</g>);
    case "kanban":
      return (<g transform="translate(14,28)"><rect width="180" height="94" rx="5" fill="#fff" opacity="0.92" />{[0, 1, 2].map((c) => <g key={c} transform={`translate(${8 + c * 58},8)`}><rect width="52" height="78" rx="3" fill="#EEF2F6" /><rect x="4" y="4" width="26" height="4" rx="2" fill={["#F2B35E", "#6FB6E8", "#22C55E"][c]} />{Array.from({ length: c === 2 ? 2 : 3 }, (_, k) => <rect key={k} x="4" y={14 + k * 22} width="44" height="17" rx="3" fill="#fff" stroke="#CBD5E1" className={c === 1 && k === 0 ? "cv-float" : undefined} />)}</g>)}</g>);
    case "frame":
      return (<g transform="translate(14,26)"><rect width="170" height="98" rx="5" fill="#F4F7F5" /><path d="M85 8 V90 M12 49 H158" stroke="#94A3B8" strokeWidth="2" />{([[28, 22, "#22C55E"], [110, 22, "#F2B35E"], [28, 64, "#6FB6E8"], [110, 64, "#E86F6F"]] as [number, number, string][]).map(([x, y, c], i) => <circle key={i} cx={x} cy={y} r={9 + i * 2} fill={c} opacity="0.85" className="cv-pop" style={{ animationDelay: `${i * 0.2}s` }} />)}<path d="M40 40 L100 30 M45 78 L112 72" stroke="#1F2A44" strokeWidth="2" strokeDasharray="4 4" /></g>);
    case "law":
      return (<g><g transform="translate(14,34)"><rect width="150" height="92" rx="3" fill="#4A2F1D" />{[0, 1, 2].map((r) => <g key={r}><rect x="4" y={28 + r * 30} width="142" height="3" fill="#2A1A0E" />{Array.from({ length: 13 }, (_, i) => <rect key={i} x={6 + i * 11} y={r * 30 + 6 + ((i * 7) % 5)} width="8" height={22 - ((i * 7) % 5)} fill={["#7C2D12", "#1E3A5F", "#14532D", "#78350F", "#3F2A5E"][(i + r) % 5]} />)}</g>)}</g><g transform="translate(300,70)" className="cv-bob"><path d="M0 0 V50 M-26 8 H26 M-26 8 L-34 30 H-18Z M26 8 L18 30 H34Z" stroke="#E6C878" strokeWidth="2.5" fill="#E6C878" fillOpacity="0.25" /></g></g>);
    case "lab":
      return (<g><rect x="10" y="132" width="210" height="8" rx="3" fill="#475569" /><g transform="translate(24,92)"><path d="M10 0 H24 V20 L36 40 H-2 L10 20Z" fill="#7DD3FC" fillOpacity="0.6" stroke="#E2E8F0" strokeWidth="2" /><circle className="cv-steam" cx="17" cy="-6" r="3" fill="#fff" /></g><g transform="translate(80,86)"><path d="M10 0 H20 V18 L40 46 H-10 L10 18Z" fill="#86EFAC" fillOpacity="0.6" stroke="#E2E8F0" strokeWidth="2" /><circle className="cv-steam" style={{ animationDelay: "0.8s" }} cx="15" cy="-6" r="3" fill="#fff" /></g><g transform="translate(150,70)"><rect x="8" y="46" width="30" height="8" rx="2" fill="#94A3B8" /><path d="M23 46 V16 Q40 10 36 -4" stroke="#CBD5E1" strokeWidth="6" fill="none" /></g><g transform="translate(250,40)" fill="none" stroke="#7EE0B0" strokeWidth="2"><path d="M0 14 L12 0 L28 0 L40 14 L28 28 L12 28Z" className="cv-clock" style={{ transformOrigin: "20px 14px", animationDuration: "14s" }} /></g></g>);
    case "warehouse":
      return (<g>{[0, 1].map((b) => <g key={b} transform={`translate(${12 + b * 150},40)`}><rect width="138" height="96" fill="#7A5336" opacity="0.9" />{[0, 1, 2].map((r) => <g key={r}><rect x="0" y={r * 32 + 28} width="138" height="4" fill="#4A2F1D" />{Array.from({ length: 4 }, (_, i) => <rect key={i} x={6 + i * 33} y={r * 32 + 6 + ((i + r) % 2) * 4} width="26" height={22 - ((i + r) % 2) * 4} fill={["#F2B35E", "#E3A987", "#C98B63", "#D9A07A"][(i + r) % 4]} stroke="#8D5A3B" />)}</g>)}</g>)}</g>);
    case "hr":
      return (<g>{[0, 1, 2, 3].map((i) => <g key={i} transform={`translate(${16 + i * 44},36)`}><rect width="38" height="46" rx="3" fill="#fff" opacity="0.92" /><circle cx="19" cy="18" r="9" fill={["#E3A987", "#C98B63", "#F2C29B", "#8D5A3B"][i]} /><rect x="6" y="31" width="26" height="10" rx="4" fill={["#6FB6E8", "#E86F6F", "#9B7BE0", "#5BC0A0"][i]} /></g>)}<g transform="translate(20,102)">{[0, 1, 2].map((i) => <g key={i} transform={`translate(${i * 54},${i % 2 ? 4 : 0}) rotate(${i * 3 - 3})`}><rect width="44" height="30" fill="#fff" /><rect x="5" y="6" width="22" height="3" fill="#94A3B8" /><rect x="5" y="13" width="32" height="3" fill="#CBD5E1" /><rect x="5" y="20" width="26" height="3" fill="#CBD5E1" /></g>)}</g></g>);
    case "actuary":
      return (<g transform="translate(14,26)"><rect width="176" height="98" rx="5" fill="#F4F7F5" /><path d="M10 84 C40 84 50 18 88 18 C126 18 136 84 166 84" fill="#C4B5FD" fillOpacity="0.55" stroke="#6247AA" strokeWidth="3" className="cv-scribble" /><path d="M88 14 V88" stroke="#6247AA" strokeDasharray="4 4" /><path d="M10 88 H166" stroke="#94A3B8" strokeWidth="2" /></g>);
    default:
      return null;
  }
}
