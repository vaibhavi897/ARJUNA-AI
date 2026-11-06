/** Shared helpers for the AI Learning Hub. */
import { Fragment, useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "../../lib/utils";
import type { Category } from "../../lib/learning";

export function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const run = useCallback(() => {
    setLoading(true);
    setError(null);
    fnRef.current().then(setData).catch((e) => setError(e?.message ?? "Something went wrong")).finally(() => setLoading(false));
  }, []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(run, deps);
  return { data, error, loading, reload: run, setData };
}

export const CAT: Record<Category, { label: string; chip: string; dot: string; soft: string; text: string }> = {
  learn: { label: "Learn", chip: "bg-emerald-100 text-emerald-800", dot: "bg-emerald-500", soft: "bg-emerald-50 border-emerald-200", text: "text-emerald-700" },
  practice: { label: "Practice", chip: "bg-sky-100 text-sky-800", dot: "bg-sky-500", soft: "bg-sky-50 border-sky-200", text: "text-sky-700" },
  project: { label: "Project", chip: "bg-violet-100 text-violet-800", dot: "bg-violet-500", soft: "bg-violet-50 border-violet-200", text: "text-violet-700" },
  revision: { label: "Revision", chip: "bg-amber-100 text-amber-800", dot: "bg-amber-500", soft: "bg-amber-50 border-amber-200", text: "text-amber-700" },
  assessment: { label: "Assessment", chip: "bg-rose-100 text-rose-800", dot: "bg-rose-500", soft: "bg-rose-50 border-rose-200", text: "text-rose-700" },
  milestone: { label: "Milestone", chip: "bg-fuchsia-100 text-fuchsia-800", dot: "bg-fuchsia-500", soft: "bg-fuchsia-50 border-fuchsia-200", text: "text-fuchsia-700" },
  rest: { label: "Rest", chip: "bg-slate-100 text-slate-600", dot: "bg-slate-300", soft: "bg-slate-50 border-slate-200", text: "text-slate-500" },
};

export const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
export const parse = (s: string) => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
export const addDays = (d: Date, n: number) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
export const startOfWeek = (d: Date) => addDays(d, -((d.getDay() + 6) % 7)); // Monday
export const fmtLong = (s: string) => parse(s).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
export const fmtShort = (s: string) => parse(s).toLocaleDateString(undefined, { day: "numeric", month: "short" });
export const hm = (min: number) => (min >= 60 ? `${Math.floor(min / 60)}h${min % 60 ? ` ${min % 60}m` : ""}` : `${min}m`);
export const todayIso = () => iso(new Date());

/** Tiny markdown renderer: headings, bullets, numbered lists, code fences, bold/italic/inline code. No HTML is ever injected. */
export function Markdown({ text, className }: { text: string; className?: string }) {
  const blocks: ReactNode[] = [];
  const lines = text.split("\n");
  let i = 0, k = 0;
  const inline = (s: string): ReactNode =>
    s.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g).map((p, n) =>
      p.startsWith("**") && p.endsWith("**") && p.length > 4 ? <strong key={n}>{p.slice(2, -2)}</strong>
      : p.startsWith("`") && p.endsWith("`") && p.length > 2 ? <code key={n} className="rounded bg-sage-100 px-1 py-0.5 font-mono text-[0.85em] text-forest-800">{p.slice(1, -1)}</code>
      : p.startsWith("*") && p.endsWith("*") && p.length > 2 ? <em key={n}>{p.slice(1, -1)}</em> : <Fragment key={n}>{p}</Fragment>);
  while (i < lines.length) {
    const l = lines[i];
    if (l.startsWith("```")) {
      const lang = l.slice(3).trim(); const buf: string[] = []; i++;
      while (i < lines.length && !lines[i].startsWith("```")) buf.push(lines[i++]);
      i++;
      blocks.push(<pre key={k++} className="my-3 overflow-x-auto rounded-xl bg-[#0F1B2D] p-4 text-[13px] leading-6 text-emerald-100"><code>{lang ? <span className="mb-1 block text-[10px] uppercase tracking-wide text-white/40">{lang}</span> : null}{buf.join("\n")}</code></pre>);
    } else if (/^#{1,4}\s/.test(l)) {
      const lvl = l.match(/^#+/)![0].length;
      const Tag = (`h${Math.min(lvl + 1, 5)}`) as "h2";
      blocks.push(<Tag key={k++} className={cn("mt-5 font-bold text-forest-900", lvl === 1 ? "text-2xl" : lvl === 2 ? "text-xl" : "text-base")}>{inline(l.replace(/^#+\s/, ""))}</Tag>); i++;
    } else if (/^\s*[-*]\s/.test(l)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s/.test(lines[i])) items.push(lines[i++].replace(/^\s*[-*]\s/, ""));
      blocks.push(<ul key={k++} className="my-2 list-disc space-y-1 pl-6">{items.map((t, n) => <li key={n}>{inline(t)}</li>)}</ul>);
    } else if (/^\s*\d+\.\s/.test(l)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s/.test(lines[i])) items.push(lines[i++].replace(/^\s*\d+\.\s/, ""));
      blocks.push(<ol key={k++} className="my-2 list-decimal space-y-1 pl-6">{items.map((t, n) => <li key={n}>{inline(t)}</li>)}</ol>);
    } else if (l.trim() === "") { i++; }
    else {
      const buf = [l]; i++;
      while (i < lines.length && lines[i].trim() && !/^(```|#|\s*[-*]\s|\s*\d+\.\s)/.test(lines[i])) buf.push(lines[i++]);
      blocks.push(<p key={k++} className="my-2">{inline(buf.join(" "))}</p>);
    }
  }
  return <div className={cn("text-[15px] leading-7 text-ink-700", className)}>{blocks}</div>;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-xl bg-sage-100", className)} />;
}

export function Stat({ label, value, sub, icon, tone = "brand" }: { label: string; value: ReactNode; sub?: ReactNode; icon?: ReactNode; tone?: "brand" | "amber" | "sky" | "rose" | "violet" }) {
  const tones = { brand: "from-emerald-50 to-white text-emerald-700", amber: "from-amber-50 to-white text-amber-700", sky: "from-sky-50 to-white text-sky-700", rose: "from-rose-50 to-white text-rose-700", violet: "from-violet-50 to-white text-violet-700" };
  return (
    <div className={cn("rounded-2xl border border-line bg-gradient-to-br p-4 shadow-sm", tones[tone])}>
      <div className="flex items-center justify-between"><p className="text-xs font-bold uppercase tracking-wide text-ink-500">{label}</p>{icon}</div>
      <p className="mt-1.5 text-3xl font-extrabold text-ink-900">{value}</p>
      {sub ? <p className="mt-0.5 text-xs text-ink-500">{sub}</p> : null}
    </div>
  );
}

export const STATUS_STYLE: Record<string, string> = {
  not_started: "bg-slate-100 text-slate-600", learning: "bg-sky-100 text-sky-800", developing: "bg-amber-100 text-amber-800",
  needs_revision: "bg-rose-100 text-rose-800", strong: "bg-emerald-100 text-emerald-800", mastered: "bg-violet-100 text-violet-800",
};
