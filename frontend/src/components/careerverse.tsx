/** CareerVerse shared helpers: data hook, locally rendered scene artwork, chips. */
import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  Building2,
  Code2,
  FileText,
  Factory,
  LineChart,
  MessageSquare,
  Monitor,
  Moon,
  PenTool,
  Presentation,
  ShieldCheck,
  Users,
} from "lucide-react";
import { request } from "../lib/api";
import { SceneAnimation } from "./SceneAnimation";
import { cn } from "../lib/utils";

export function useApi<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!!path);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!path) return;
    const ctrl = new AbortController();
    setLoading(true);
    setError(null);
    request<T>(path, { signal: ctrl.signal })
      .then((d) => setData(d))
      .catch((e) => {
        if (e?.name !== "AbortError") setError(e?.message ?? "Request failed");
      })
      .finally(() => !ctrl.signal.aborted && setLoading(false));
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, tick, ...deps]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload, setData };
}

const THEME: Record<string, [string, string]> = {
  finance: ["#0C3326", "#2B6B4E"],
  consulting: ["#13324A", "#2F6F8F"],
  tech: ["#1B2B4B", "#3F63A8"],
  data: ["#2A2150", "#6247AA"],
  product: ["#4A2340", "#A04A86"],
  business: ["#4A3216", "#B07A2B"],
  security: ["#3A1818", "#A33B3B"],
  invest: ["#12383A", "#2E8C86"],
  office: ["#26382E", "#5F8F76"],
};

const EMOJI: Record<string, string> = {
  arrival: "🏢", desk: "💻", analysis: "📊", code: "👨‍💻", meeting: "🤝", presentation: "📽️",
  document: "📝", design: "🎨", security: "🛡️", field: "🏭", review: "💬", wrapup: "🌆",
};
// Secondary emojis scattered around the main one, by visual theme.
const THEME_EMOJI: Record<string, string[]> = {
  finance: ["💹", "🏦", "💰"], consulting: ["🧭", "📈", "🗂️"], tech: ["⚙️", "🖥️", "🚀"], data: ["🔍", "📉", "🧮"],
  product: ["💡", "🧩", "📱"], business: ["📞", "📦", "🤝"], security: ["🔒", "🕵️", "🚨"], invest: ["🌱", "📊", "💼"], office: ["📁", "☕", "🗓️"],
};

const PERSON: Record<string, string> = {
  arrival: "🚶", desk: "🧑‍💼", analysis: "🧑‍💼", code: "🧑‍💻", meeting: "🧑‍🤝‍🧑", presentation: "🧑‍🏫",
  document: "🧑‍💼", design: "🧑‍🎨", security: "🕵️", field: "👷", review: "👥", wrapup: "🧑‍💼",
};
// Place the person sits in / at, per scene type.
const SETTING: Record<string, string> = {
  arrival: "🏢", desk: "🪑🖥️", analysis: "🪑🖥️", code: "🪑💻", meeting: "🪑🪑", presentation: "📽️",
  document: "🪑🖥️", design: "🪑🖥️", security: "🖥️🖥️", field: "📦", review: "🪑💻", wrapup: "🌇",
};
const TOOL_EMOJI: [RegExp, string][] = [
  [/excel|sheet|spreadsheet|model/i, "📊"], [/bloomberg|capiq|factset|market|terminal/i, "📈"], [/outlook|email|gmail/i, "📧"],
  [/powerpoint|slides|deck|pitch|think-cell/i, "📽️"], [/word|memo|docs?|report/i, "📝"], [/sql|database|postgres|warehouse|snowflake|bigquery/i, "🗄️"],
  [/python|r|jupyter|pandas|code|vs ?code|git|github|ide/i, "⌨️"], [/figma|sketch|illustrator|photoshop|canva/i, "🎨"], [/zoom|teams|meet|call|phone/i, "🎥"],
  [/slack/i, "💬"], [/tableau|power ?bi|looker|dashboard|grafana/i, "📉"], [/jira|confluence|notion|tracker|roadmap/i, "🗂️"], [/docker|kubernetes|terraform|ci\/cd/i, "🐳"],
  [/aws|azure|gcp|cloud/i, "☁️"], [/siem|splunk|edr|crowdstrike|wireshark|nessus|scan/i, "🛡️"], [/erp|sap|oracle|ledger/i, "🧾"], [/crm|salesforce|hubspot/i, "👥"],
  [/lab|instrument/i, "🔬"], [/contract|agreement|legal|manupatra/i, "⚖️"],
];
function propsFor(tools: string[] = []): string[] {
  const out: string[] = [];
  for (const t of tools) {
    const hit = TOOL_EMOJI.find(([re]) => re.test(t));
    if (hit && !out.includes(hit[1])) out.push(hit[1]);
  }
  return out.slice(0, 4);
}

const ICONS: Record<string, ReactNode> = {
  arrival: <Building2 />,
  desk: <Monitor />,
  analysis: <LineChart />,
  code: <Code2 />,
  meeting: <Users />,
  presentation: <Presentation />,
  document: <FileText />,
  design: <PenTool />,
  security: <ShieldCheck />,
  field: <Factory />,
  review: <MessageSquare />,
  wrapup: <Moon />,
};

/** Locally rendered illustration. No network images, so nothing to license or load. */
export function SceneArt({
  theme,
  visual,
  label,
  className,
  size = "lg",
  tools,
}: {
  theme: string;
  visual: string;
  label?: string;
  className?: string;
  size?: "sm" | "lg";
  tools?: string[];
}) {
  const [a, b] = THEME[theme] ?? THEME.office;
  const big = size === "lg";
  // Pre-generated local image (scripts/generate_scene_images.py); falls back to the drawn art.
  const [imgOk, setImgOk] = useState(true);
  const src = `/careerverse/${theme}/${visual}.png`;
  useEffect(() => setImgOk(true), [src]);
  if (size === "lg") {
    return (
      <div role="img" aria-label={label ?? `${visual} scene`} className={cn("relative overflow-hidden", className)} style={{ background: `linear-gradient(135deg, ${a}, ${b})` }}>
        <SceneAnimation visual={visual} className="absolute inset-0 h-full w-full" />
      </div>
    );
  }
  if (imgOk) {
    return (
      <div className={cn("relative overflow-hidden bg-sage-200", className)} style={{ background: `linear-gradient(135deg, ${a}, ${b})` }}>
        <img src={src} alt={label ?? `${visual} scene`} loading="lazy" onError={() => setImgOk(false)} className="h-full w-full object-cover" />
      </div>
    );
  }
  return (
    <div
      role="img"
      aria-label={label ?? `${visual} scene`}
      className={cn("relative overflow-hidden", className)}
      style={{ background: `linear-gradient(135deg, ${a}, ${b})` }}
    >
      <svg className="absolute inset-0 h-full w-full opacity-25" viewBox="0 0 400 225" preserveAspectRatio="xMidYMid slice" aria-hidden>
        <circle className="cv-drift" cx="330" cy="40" r="90" fill="white" opacity="0.15" />
        <circle className="cv-drift" style={{ animationDelay: "-3s" }} cx="60" cy="210" r="110" fill="white" opacity="0.12" />
        <path d="M0 170 Q100 120 200 160 T400 130 V225 H0Z" fill="white" opacity="0.1" />
        {[0, 1, 2, 3, 4].map((i) => (
          <rect key={i} x={250 + i * 24} y={150 - ((i * 37) % 60)} width="14" height={60 + ((i * 37) % 60)} rx="3" fill="white" opacity="0.18" />
        ))}
      </svg>
      <div className="relative grid h-full w-full place-items-center text-white">
        <div aria-hidden className="flex flex-col items-center gap-1">
          <div className={cn("flex items-end", big ? "gap-3" : "gap-1")}>
            <span className={cn(visual === "code" || visual === "analysis" || visual === "document" ? "cv-type" : "cv-bob", big ? "text-7xl" : "text-4xl")}>{PERSON[visual] ?? PERSON.desk}</span>
            <span className={cn("rounded-2xl bg-white/15 px-2 ring-1 ring-white/25 backdrop-blur-sm", big ? "text-5xl" : "text-2xl")}>{SETTING[visual] ?? SETTING.desk}</span>
          </div>
          <div className={cn("flex items-center", big ? "mt-3 gap-3 text-3xl" : "mt-1 gap-1.5 text-lg")}>
            {(propsFor(tools).length ? propsFor(tools) : (THEME_EMOJI[theme] ?? THEME_EMOJI.office)).map((e, i) => <span key={e} className="cv-pop rounded-xl bg-white/15 px-2 py-1" style={{ animationDelay: `${0.25 + i * 0.18}s` }}>{e}</span>)}
          </div>
        </div>
      </div>
    </div>
  );
}

export function Chip({ children, tone = "sage" }: { children: ReactNode; tone?: "sage" | "brand" | "warn" }) {
  const tones = { sage: "bg-sage-100 text-forest-800", brand: "bg-brand-50 text-brand-700", warn: "bg-warn-50 text-warn-700" };
  return <span className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium", tones[tone])}>{children}</span>;
}

export type CareerCard = {
  id: number;
  slug: string;
  title: string;
  industry: string;
  short_description: string;
  visual_theme: string;
  scene_count: number;
  story_last_scene: number;
  story_completed: boolean;
  insights_viewed: boolean;
  is_saved: boolean;
};
