/**
 * Animated flat-illustration scenes drawn in SVG (no external assets).
 *
 * "work" scenes loop a mini story: the professional sits on a chair typing at
 * a computer, stands up, walks over and shakes hands with a client.
 * Other scene types animate their own action (meeting, presenting, arriving,
 * leaving). All motion is CSS, and is switched off for reduced-motion users.
 */
import type { ReactNode } from "react";
import { L } from "./look";
import { Outfit, ROLES, RoleDecor, type RoleCfg } from "./RoleArt";

let ROLE: RoleCfg | undefined;

// Look of the current scene. Re-derived from a seed on every render so each
// scene gets different people, outfits and surroundings.

const SKINS = ["#F2C29B", "#E3A987", "#C98B63", "#8D5A3B", "#F6D3B3"];
const HAIRS = ["#2B2220", "#4A2F1D", "#111", "#8A5A2B", "#A8A8A8"];
const SHIRTS = ["#F4F7F5", "#CFE8FF", "#FFD9C7", "#D8F0DC", "#E7D9FF"];
const PANTSS = ["#1F2A44", "#2F3B4F", "#3B2F3F", "#27403A"];
const CSHIRTS = ["#F2B35E", "#E86F6F", "#6FB6E8", "#9B7BE0", "#5BC0A0"];
const TIES = ["#229A63", "#E25555", "#3F63A8", "#F2B35E"];
function pick<T>(arr: T[], n: number): T { return arr[Math.abs(n) % arr.length]; }
function applyLook(seed: number) {
  L.skin = pick(SKINS, seed); L.hair = pick(HAIRS, seed >> 2); L.shirt = pick(SHIRTS, seed >> 3); L.pants = pick(PANTSS, seed >> 4);
  L.cShirt = pick(CSHIRTS, seed >> 1); L.cPants = pick(PANTSS, (seed >> 5) + 1); L.cHair = pick(HAIRS, (seed >> 6) + 2); L.cSkin = pick(SKINS, (seed >> 7) + 3); L.tie = pick(TIES, seed >> 5);
}

const WORK = new Set(["desk", "analysis", "code", "document", "design", "security"]);
const TALK = new Set(["meeting", "review", "presentation"]);

function Arm({ side, shirt, className, style }: { side: -1 | 1; shirt: string; className?: string; style?: React.CSSProperties }) {
  return (
    <g transform={`translate(${side * 14},-74)`}>
      <g className={className} style={{ transformBox: "fill-box", transformOrigin: "50% 0", ...style }}>
        <rect x="-3.5" y="0" width="7" height="28" rx="3.5" fill={shirt} />
        <circle cx="0" cy="29" r="4.2" fill={L.skin} />
      </g>
    </g>
  );
}

function Leg({ x, className, pants, delay }: { x: number; className?: string; pants: string; delay?: string }) {
  return (
    <g transform={`translate(${x},-36)`}>
      <g className={className} style={{ transformBox: "fill-box", transformOrigin: "50% 0", animationDelay: delay }}>
        <rect x="-4.5" y="0" width="9" height="36" rx="4" fill={pants} />
        <rect x="-5" y="33" width="14" height="5" rx="2.5" fill="#101522" />
      </g>
    </g>
  );
}

/** Standing person, feet at (0,0). */
function Standing({
  shirt = L.shirt, pants = L.pants, walk, armR, armL, hair = L.hair, tie,
}: { shirt?: string; pants?: string; walk?: boolean; armR?: string; armL?: string; hair?: string; tie?: boolean }) {
  return (
    <g>
      <Leg x={-6} pants={pants} className={walk ? "cv-legA" : undefined} />
      <Leg x={6} pants={pants} className={walk ? "cv-legB" : undefined} />
      <rect x="-14" y="-80" width="28" height="46" rx="9" fill={shirt} />
      {tie && L.suit ? <path d="M-2 -78 L2 -78 L3 -56 L0 -52 L-3 -56Z" fill="#229A63" /> : null}
      <Arm side={-1} shirt={shirt} className={armL} />
      <Arm side={1} shirt={shirt} className={armR} />
      <rect x="-3" y="-87" width="6" height="8" fill={L.skin} />
      <circle cx="0" cy="-95" r="12" fill={L.skin} />
      <path d="M-12 -96 Q-10 -110 0 -108 Q11 -109 12 -96 Q6 -102 -12 -96Z" fill={hair} />
      <Outfit />
    </g>
  );
}

function Chair() {
  return (
    <g>
      <rect x="-30" y="-42" width="7" height="46" rx="3" fill="#2E3A59" />
      <rect x="-26" y="2" width="44" height="8" rx="4" fill="#3B4A72" />
      <rect x="-6" y="10" width="5" height="21" fill="#2A3350" />
      <rect x="-24" y="30" width="40" height="5" rx="2.5" fill="#2A3350" />
    </g>
  );
}

/** Seated person, hip at (0,0), facing right. */
function Sitting({ typing }: { typing?: boolean }) {
  return (
    <g>
      <rect x="-6" y="-8" width="42" height="13" rx="6" fill={L.pants} />
      <rect x="28" y="-3" width="11" height="38" rx="5" fill={L.pants} />
      <rect x="26" y="31" width="18" height="5" rx="2.5" fill="#101522" />
      <rect x="-14" y="-46" width="28" height="46" rx="9" fill={L.shirt} />
      {L.suit ? <path d="M2 -44 L6 -44 L6 -26 L4 -22 L2 -26Z" fill={L.tie} /> : null}
      <rect x="-3" y="-53" width="6" height="8" fill={L.skin} />
      <circle cx="3" cy="-62" r="12" fill={L.skin} />
      <path d="M-9 -63 Q-7 -77 4 -75 Q15 -76 15 -63 Q9 -69 -9 -63Z" fill={L.hair} />
      <Outfit sit />
      <g className={typing ? "cv-typearm" : undefined}>
        <path d="M4 -38 L50 -14" stroke={L.shirt} strokeWidth="8" strokeLinecap="round" />
        <circle cx="52" cy="-13" r="4.2" fill={L.skin} />
      </g>
    </g>
  );
}

function Screen({ visual }: { visual: string }) {
  const bars = [14, 24, 18, 30, 22];
  return (
    <g>
      <rect x="0" y="0" width="52" height="38" rx="3" fill="#0F1B2D" stroke="#CBD5E1" strokeWidth="2" />
      {visual === "code" ? [8, 16, 24, 32].map((y, i) => <rect key={y} x={6 + (i % 2) * 6} y={y - 3} width={28 + ((i * 9) % 14)} height="3" rx="1.5" fill={["#7EE0B0", "#7FB0FF", "#F2B35E", "#C79BFF"][i]} />) : null}
      {visual === "document" ? [8, 14, 20, 26, 32].map((y) => <rect key={y} x="8" y={y - 3} width={y === 32 ? 20 : 36} height="2.5" rx="1" fill="#E5ECE8" />) : null}
      {visual === "design" ? <><circle cx="17" cy="19" r="9" fill="#C79BFF" /><rect x="29" y="11" width="16" height="16" rx="3" fill="#F2B35E" /></> : null}
      {visual === "security" ? <path d="M26 6 L42 12 V22 C42 30 34 33 26 36 C18 33 10 30 10 22 V12Z" fill="#229A63" opacity="0.9" /> : null}
      {(visual === "analysis" || visual === "desk") ? bars.map((h, i) => <rect key={i} className="cv-bar" style={{ animationDelay: `${i * 0.15}s`, transformBox: "fill-box", transformOrigin: "50% 100%" }} x={7 + i * 8.5} y={33 - h} width="6" height={h} rx="1.5" fill="#7EE0B0" />) : null}
    </g>
  );
}

function Floor() {
  return <rect x="0" y="195" width="400" height="30" fill="#000" opacity="0.18" />;
}

let DECOR = 0;
function Decor({ variant }: { variant: number }) {
  if (variant === 1)
    return (<g>
      <g transform="translate(20,40)"><rect width="70" height="100" rx="3" fill="#6B4A32" opacity="0.85" />{[0, 1, 2, 3].map((r) => <g key={r}><rect x="6" y={8 + r * 23} width="58" height="3" fill="#3E2A1C" />{[0, 1, 2, 3, 4].map((c) => <rect key={c} x={8 + c * 11} y={r * 23 - 4 + 12} width="8" height={14 - (c % 3) * 2} fill={["#E86F6F", "#6FB6E8", "#F2B35E", "#9B7BE0", "#5BC0A0"][(c + r) % 5]} />)}</g>)}</g>
      <g transform="translate(330,50)"><circle r="22" fill="#fff" opacity="0.9" /><path d="M0 0 V-14 M0 0 L10 6" stroke="#1F2A44" strokeWidth="3" strokeLinecap="round" className="cv-clock" /></g>
    </g>);
  if (variant === 2)
    return (<g>
      <rect x="16" y="26" width="110" height="86" rx="4" fill="#0F1B2D" opacity="0.55" />
      {[0, 1, 2, 3, 4, 5].map((i) => <rect key={i} x={24 + i * 16} y={112 - (20 + ((i * 29) % 50))} width="10" height={20 + ((i * 29) % 50)} fill="#F2B35E" opacity="0.8" />)}
      <g transform="translate(350,195)"><rect x="-2" y="-70" width="4" height="70" fill="#CBD5E1" /><path d="M-18 -70 L18 -70 L10 -92 L-10 -92Z" fill="#F2B35E" /></g>
    </g>);
  return (<g>
    <rect x="18" y="34" width="62" height="70" rx="4" fill="#fff" opacity="0.14" />
    <path d="M49 34 V104 M18 69 H80" stroke="#fff" strokeWidth="2" opacity="0.4" />
    <g transform="translate(364,195)"><rect x="-4" y="-34" width="8" height="34" fill="#6B4A32" /><circle cx="0" cy="-48" r="22" fill="#229A63" opacity="0.8" /></g>
  </g>);
}

function WorkScene({ visual }: { visual: string }) {
  return (
    <>
      <Floor />
      {ROLE ? <RoleDecor kind={ROLE.decor} /> : <Decor variant={DECOR} />}
      {/* desk, keyboard, monitor */}
      <rect x="78" y="150" width="108" height="7" rx="3" fill="#9A6B45" />
      <rect x="84" y="157" width="6" height="38" fill="#7A5336" />
      <rect x="174" y="157" width="6" height="38" fill="#7A5336" />
      <rect x="98" y="146" width="32" height="4" rx="2" fill="#CBD5E1" />
      <rect x="150" y="136" width="6" height="14" fill="#94A3B8" />
      <g transform="translate(127,100)"><Screen visual={ROLE?.screen && ["desk", "analysis"].includes(visual) ? ROLE.screen : visual} /></g>
      {/* seated, then standing and meeting the client (10s loop) */}
      <g transform="translate(62,160)" className="cv-seq-sit"><Chair /><Sitting typing /></g>
      <g transform="translate(62,195)" className="cv-seq-standvis">
        <g className="cv-seq-move">
          <Standing tie armR="cv-seq-shake" />
        </g>
      </g>
      <g transform="translate(300,195)" className="cv-seq-client">
        <g className="cv-seq-clientmove"><g transform="scale(-1,1)"><Standing shirt={L.cShirt} pants={L.cPants} hair={L.cHair} armR="cv-seq-shake" /></g></g>
      </g>
    </>
  );
}

function Bubble({ x, y, cls }: { x: number; y: number; cls: string }) {
  return (
    <g transform={`translate(${x},${y})`} className={cls}>
      <rect x="0" y="0" width="34" height="20" rx="10" fill="#fff" />
      <circle cx="10" cy="10" r="2.2" fill="#94A3B8" /><circle cx="17" cy="10" r="2.2" fill="#94A3B8" /><circle cx="24" cy="10" r="2.2" fill="#94A3B8" />
    </g>
  );
}

function TalkScene({ visual }: { visual: string }) {
  const board = visual === "presentation";
  return (
    <>
      <Floor />
      {ROLE && !board ? <g opacity="0.8"><RoleDecor kind={ROLE.decor} /></g> : null}
      {board ? (
        <g transform="translate(215,60)">
          <rect width="150" height="94" rx="6" fill="#F4F7F5" /><rect x="6" y="6" width="138" height="82" rx="4" fill="#E8F0EC" />
          {[26, 42, 34, 58, 48].map((h, i) => <rect key={i} className="cv-bar" style={{ animationDelay: `${i * 0.2}s`, transformBox: "fill-box", transformOrigin: "50% 100%" }} x={18 + i * 24} y={80 - h} width="14" height={h} rx="3" fill="#229A63" />)}
        </g>
      ) : visual === "review" ? (
        <g transform="translate(160,90)"><rect x="0" y="0" width="80" height="52" rx="4" fill="#0F1B2D" stroke="#CBD5E1" strokeWidth="2" />{[14, 24, 34].map((y) => <rect key={y} x="10" y={y} width={50 + (y % 3) * 6} height="4" rx="2" fill="#7EE0B0" />)}<rect x="36" y="52" width="8" height="18" fill="#94A3B8" /></g>
      ) : (
        <g transform="translate(150,150)"><ellipse cx="50" cy="0" rx="62" ry="12" fill="#9A6B45" /><rect x="46" y="0" width="8" height="45" fill="#7A5336" /></g>
      )}
      <g transform={`translate(${board ? 90 : 120},195)`}><g className="cv-nod"><Standing tie armR="cv-gesture" /></g></g>
      <g transform={`translate(${board ? 190 : 280},195)`}><g transform="scale(-1,1)"><Standing shirt={L.cShirt} pants={L.cPants} hair={L.cHair} armR="cv-gesture2" /></g></g>
      <Bubble x={board ? 80 : 108} y={70} cls="cv-say-a" />
      <Bubble x={board ? 160 : 248} y={70} cls="cv-say-b" />
    </>
  );
}

function CallScene() {
  return (
    <>
      <Floor />
      {ROLE ? <g opacity="0.8"><RoleDecor kind={ROLE.decor} /></g> : null}
      <rect x="40" y="40" width="130" height="95" rx="4" fill="#fff" opacity="0.14" />
      <circle cx="105" cy="88" r="26" fill="none" stroke="#fff" strokeWidth="2" opacity="0.5" /><path d="M79 88 H131 M105 62 Q92 88 105 114 M105 62 Q118 88 105 114" stroke="#fff" strokeWidth="1.5" fill="none" opacity="0.5" />
      <g transform="translate(250,195)"><g className="cv-nod"><Standing tie armR="cv-phone" /></g></g>
      <Bubble x={282} y={52} cls="cv-say-a" /><Bubble x={300} y={30} cls="cv-say-b" />
    </>
  );
}

function BoardScene() {
  return (
    <>
      <Floor />
      <g transform="translate(150,40)"><rect width="200" height="115" rx="6" fill="#F4F7F5" />
        <path className="cv-scribble" d="M20 80 L55 55 L90 70 L130 35 L175 48" stroke="#229A63" strokeWidth="4" fill="none" strokeLinecap="round" />
        <rect x="20" y="20" width="60" height="6" rx="3" fill="#94A3B8" /><rect x="20" y="32" width="40" height="6" rx="3" fill="#CBD5E1" />
        <circle cx="175" cy="48" r="7" fill="#F2B35E" className="cv-pop" /></g>
      <g transform="translate(110,195)"><Standing tie armR="cv-draw" /></g>
      <g transform="translate(370,195)"><g transform="scale(-1,1)"><Standing shirt={L.cShirt} pants={L.cPants} hair={L.cHair} armR="cv-gesture2" /></g></g>
    </>
  );
}

function CoffeeScene() {
  return (
    <>
      <Floor />
      {ROLE ? <g opacity="0.7"><RoleDecor kind={ROLE.decor} /></g> : null}
      <rect x="120" y="140" width="160" height="10" rx="4" fill="#9A6B45" /><rect x="128" y="150" width="8" height="45" fill="#7A5336" /><rect x="264" y="150" width="8" height="45" fill="#7A5336" />
      <g transform="translate(160,128)"><rect width="14" height="12" rx="3" fill="#fff" /><path className="cv-steam" d="M4 -2 Q0 -10 5 -16" stroke="#fff" strokeWidth="2" fill="none" /></g>
      <g transform="translate(222,128)"><rect width="14" height="12" rx="3" fill="#fff" /><path className="cv-steam" style={{ animationDelay: "0.6s" }} d="M4 -2 Q0 -10 5 -16" stroke="#fff" strokeWidth="2" fill="none" /></g>
      <g transform="translate(125,195)"><g className="cv-nod"><Standing tie armR="cv-gesture" /></g></g>
      <g transform="translate(275,195)"><g transform="scale(-1,1)"><Standing shirt={L.cShirt} pants={L.cPants} hair={L.cHair} armR="cv-gesture2" /></g></g>
      <Bubble x={112} y={62} cls="cv-say-a" /><Bubble x={252} y={62} cls="cv-say-b" />
    </>
  );
}

function WalkScene({ visual }: { visual: string }) {
  const out = visual === "wrapup";
  const field = visual === "field";
  return (
    <>
      <Floor />
      {out ? (
        <><circle cx="318" cy="150" r="46" fill="#F2B35E" opacity="0.9" /><rect x="0" y="150" width="400" height="45" fill="#0F1B2D" opacity="0.25" />
          {[40, 90, 150, 210].map((x, i) => <rect key={x} x={x} y={90 - i * 12} width="26" height={105 + i * 12} fill="#fff" opacity="0.1" />)}</>
      ) : field ? (
        <>{[40, 150, 260].map((x) => <g key={x} transform={`translate(${x},95)`}><rect width="70" height="100" fill="#7A5336" opacity="0.85" />{[0, 1, 2].map((r) => <g key={r}><rect x="5" y={8 + r * 32} width="26" height="20" fill="#F2B35E" /><rect x="38" y={14 + r * 32} width="24" height="14" fill="#94A3B8" /></g>)}</g>)}</>
      ) : (
        <><g transform="translate(270,50)"><rect width="110" height="145" fill="#fff" opacity="0.18" />{[0, 1, 2].map((r) => [0, 1, 2].map((c) => <rect key={`${r}${c}`} x={12 + c * 32} y={12 + r * 26} width="20" height="16" fill="#fff" opacity="0.35" />))}<rect x="40" y="100" width="34" height="45" rx="3" fill="#2E3A59" /></g></>
      )}
      <g transform={`translate(${out ? 40 : 20},195)`} className={out ? "cv-walk cv-walk-out" : "cv-walk"}>
        <Standing tie walk armR="cv-swingA" armL="cv-swingB" />
        {out ? <g transform="translate(18,-50)"><rect width="22" height="26" rx="4" fill="#8A5A3C" /></g> : null}
      </g>
    </>
  );
}

export function SceneAnimation({ visual, seed = 0, role, className }: { visual: string; seed?: number; role?: string; className?: string }): ReactNode {
  applyLook(seed);
  ROLE = role ? ROLES[role] : undefined;
  L.outfit = ROLE?.outfit ?? "suit";
  L.suit = ROLE ? ROLE.suit : true;
  DECOR = Math.abs(seed >> 1) % 3;
  const mirror = seed % 2 === 1 && !WORK.has(visual);
  return (
    <svg className={className} viewBox="0 0 400 225" preserveAspectRatio="xMidYMid meet" role="img" aria-hidden>
      <g transform={mirror ? "translate(400,0) scale(-1,1)" : undefined}>
        {WORK.has(visual) ? <WorkScene visual={visual} />
          : visual === "call" ? <CallScene />
          : visual === "whiteboard" ? <BoardScene />
          : visual === "coffee" ? <CoffeeScene />
          : TALK.has(visual) ? <TalkScene visual={visual} />
          : <WalkScene visual={visual} />}
      </g>
    </svg>
  );
}

/** Stable numeric seed from any string (career slug + scene number). */
export { ROLES };
export function seedOf(text: string): number {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619);
  return h >>> 0;
}
