/** Dark, cinematic "Manhattan law firm" kit: skyline through glass, text reveals, quote rotator. */
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { cn } from "../lib/utils";

export const QUOTES = [
  "Winners don't make excuses. They make moves.",
  "The world doesn't reward potential. It rewards execution.",
  "Be so prepared that opportunity feels like an appointment.",
  "You don't wait for your moment. You make everyone notice when it arrives.",
  "Confidence is just preparation that learned to walk into a room.",
  "Average people ask for a chance. Serious people build the case.",
  "Don't compete for a seat. Make the room rearrange itself.",
  "Ambition is a promise. Discipline is the signature.",
];

const reduced = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

function rng(seed: number) {
  let s = seed;
  return () => ((s = (s * 1664525 + 1013904223) % 4294967296) / 4294967296);
}

/** Night skyline seen through a glass wall, with mouse parallax. */
export function SuitsScene({ className, dim = false }: { className?: string; dim?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const layers = useMemo(() => {
    const r = rng(7);
    return [
      { depth: 6, color: "#0E131C", h: [34, 62], w: [28, 56], count: 18, lit: 0.18 },
      { depth: 14, color: "#0A0E15", h: [48, 88], w: [34, 70], count: 14, lit: 0.3 },
      { depth: 26, color: "#06080D", h: [60, 120], w: [40, 86], count: 11, lit: 0.42 },
    ].map((L) => {
      let x = -20;
      const buildings = Array.from({ length: L.count }, () => {
        const w = L.w[0] + r() * (L.w[1] - L.w[0]);
        const h = L.h[0] + r() * (L.h[1] - L.h[0]);
        const b = { x, w, h, wins: [] as { x: number; y: number; on: boolean; d: number }[] };
        for (let wy = 6; wy < h - 4; wy += 7) for (let wx = 4; wx < w - 4; wx += 6) if (r() < 0.8) b.wins.push({ x: wx, y: wy, on: r() < L.lit, d: r() * 6 });
        x += w + r() * 6;
        return b;
      });
      return { ...L, buildings };
    });
  }, []);

  const move = (e: React.PointerEvent) => {
    const el = ref.current;
    if (!el || reduced()) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--px", String((e.clientX - r.left) / r.width - 0.5));
    el.style.setProperty("--py", String((e.clientY - r.top) / r.height - 0.5));
  };

  return (
    <div ref={ref} onPointerMove={move} aria-hidden className={cn("absolute inset-0 overflow-hidden bg-[#05070B]", className)}>
      <div className="absolute inset-0" style={{ background: "radial-gradient(120% 80% at 70% 20%, #1C2433 0%, #0A0E16 55%, #05070B 100%)" }} />
      <div className="absolute left-[62%] top-[14%] h-40 w-40 rounded-full bg-[#E6C878]/10 blur-3xl" />
      {layers.map((L, i) => (
        <svg key={i} className="absolute bottom-0 left-0 w-full" viewBox="0 0 400 140" preserveAspectRatio="xMidYMax slice"
          style={{ height: `${58 + i * 12}%`, transform: `translate(calc(var(--px, 0) * ${-L.depth}px), calc(var(--py, 0) * ${-L.depth / 2}px))`, transition: "transform .25s ease-out" }}>
          {L.buildings.map((b, k) => (
            <g key={k} transform={`translate(${b.x},${140 - b.h})`}>
              <rect width={b.w} height={b.h} fill={L.color} />
              {b.wins.map((w, j) => (
                <rect key={j} x={w.x} y={w.y} width="2.6" height="3.4" fill={w.on ? "#F3D48A" : "#1B2231"} opacity={w.on ? 0.85 : 0.6} className={w.on ? "su-twinkle" : undefined} style={w.on ? { animationDelay: `${w.d}s` } : undefined} />
              ))}
            </g>
          ))}
        </svg>
      ))}
      {/* the glass wall: mullions, transom, sweeping reflection */}
      <div className="pointer-events-none absolute inset-0" style={{ backgroundImage: "repeating-linear-gradient(90deg, transparent 0, transparent calc(20% - 2px), rgba(255,255,255,.07) calc(20% - 2px), rgba(255,255,255,.07) 20%)" }} />
      <div className="pointer-events-none absolute inset-x-0 top-[18%] h-[2px] bg-white/10" />
      <div className="pointer-events-none absolute inset-0 su-sweep" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-black via-black/60 to-transparent" />
      <div className={cn("pointer-events-none absolute inset-0 bg-black transition-opacity", dim ? "opacity-60" : "opacity-25")} />
      <div className="pointer-events-none absolute inset-0 su-vignette" />
    </div>
  );
}

/** Dramatic word-by-word reveal. */
export function Words({ text, className, wordClass, delay = 0, step = 90 }: { text: string; className?: string; wordClass?: string; delay?: number; step?: number }) {
  return (
    <span className={className} aria-label={text}>
      {text.split(" ").map((w, i) => (
        <span key={i} aria-hidden className="inline-block overflow-hidden align-bottom pb-[0.22em] -mb-[0.1em]">
          <span className={cn("su-word inline-block", wordClass)} style={{ animationDelay: `${delay + i * step}ms` }}>{w}&nbsp;</span>
        </span>
      ))}
    </span>
  );
}

/** Cycles through one-liners with a fade/slide, never the same twice in a row. */
export function QuoteRotator({ className, interval = 5200, start = 0 }: { className?: string; interval?: number; start?: number }) {
  const [i, setI] = useState(start % QUOTES.length);
  useEffect(() => {
    if (reduced()) return;
    const id = window.setInterval(() => setI((c) => (c + 1) % QUOTES.length), interval);
    return () => window.clearInterval(id);
  }, [interval]);
  return (
    <div className={cn("relative", className)} aria-live="off">
      <p key={i} className="su-quote font-suits italic">&ldquo;{QUOTES[i]}&rdquo;</p>
      <div className="mt-4 flex gap-1.5">
        {QUOTES.map((_, k) => <span key={k} className={cn("h-[3px] rounded-full transition-all duration-500", k === i ? "w-8 bg-[#E6C878]" : "w-3 bg-white/20")} />)}
      </div>
    </div>
  );
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-baseline gap-2 font-suits", className)}>
      <span className="text-xl font-bold tracking-[0.34em] text-white">ARJUNA</span>
      <span className="rounded-sm border border-[#E6C878]/60 px-1.5 py-0.5 text-[10px] font-bold tracking-[0.3em] text-[#E6C878]">AI</span>
    </span>
  );
}

export function GoldButton({ children, onClick, variant = "solid", className, type = "button" }: { children: ReactNode; onClick?: () => void; variant?: "solid" | "ghost"; className?: string; type?: "button" | "submit" }) {
  return (
    <button type={type} onClick={onClick}
      className={cn("group relative inline-flex items-center justify-center gap-2 overflow-hidden px-8 py-3.5 text-sm font-bold uppercase tracking-[0.18em] transition-all duration-300",
        variant === "solid" ? "bg-gradient-to-b from-[#F0D58C] to-[#C9A24B] text-[#14100A] shadow-[0_10px_40px_-10px_rgba(230,200,120,.7)] hover:-translate-y-0.5 hover:shadow-[0_16px_50px_-8px_rgba(230,200,120,.9)]" : "border border-white/25 text-white hover:border-[#E6C878] hover:text-[#E6C878]", className)}>
      <span className="absolute inset-0 -translate-x-full bg-white/30 skew-x-12 transition-transform duration-700 group-hover:translate-x-full" />
      <span className="relative inline-flex items-center gap-2">{children}</span>
    </button>
  );
}
