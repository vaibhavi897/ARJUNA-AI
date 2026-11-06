/** Motion toolkit: scroll reveal, count-up, tilt/spotlight, typewriter, aurora. No dependencies. */
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { cn } from "../lib/utils";

const reduced = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export function useInView<T extends Element>(once = true, margin = "0px 0px -8% 0px") {
  const ref = useRef<T | null>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (reduced() || typeof IntersectionObserver === "undefined") return setSeen(true);
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setSeen(true);
          if (once) io.disconnect();
        } else if (!once) setSeen(false);
      },
      { rootMargin: margin, threshold: 0.08 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [once, margin]);
  return [ref, seen] as const;
}

export function Reveal({ children, delay = 0, y = 22, className, as: Tag = "div" }: { children: ReactNode; delay?: number; y?: number; className?: string; as?: any }) {
  const [ref, seen] = useInView<HTMLDivElement>();
  return (
    <Tag
      ref={ref}
      className={className}
      style={{ opacity: seen ? 1 : 0, transform: seen ? "none" : `translateY(${y}px) scale(0.985)`, transition: `opacity .7s cubic-bezier(.2,.7,.2,1) ${delay}ms, transform .7s cubic-bezier(.2,.7,.2,1) ${delay}ms` }}
    >
      {children}
    </Tag>
  );
}

export function useCountUp(target: number, active = true, duration = 1200) {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!active) return;
    if (reduced()) return setV(target);
    let raf = 0;
    const t0 = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / duration);
      setV(target * (1 - Math.pow(1 - p, 4)));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, active, duration]);
  return v;
}

export function CountUp({ value, format, className }: { value: number; format?: (n: number) => string; className?: string }) {
  const [ref, seen] = useInView<HTMLSpanElement>();
  const v = useCountUp(value, seen);
  return <span ref={ref} className={className}>{format ? format(v) : Math.round(v).toLocaleString()}</span>;
}

/** 3D tilt + cursor spotlight. Pure CSS variables, so no re-renders on mouse move. */
export function TiltCard({ children, className, style }: { children: ReactNode; className?: string; style?: CSSProperties }) {
  const ref = useRef<HTMLDivElement>(null);
  const move = (e: React.PointerEvent) => {
    const el = ref.current;
    if (!el || reduced() || e.pointerType === "touch") return;
    const r = el.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width;
    const y = (e.clientY - r.top) / r.height;
    el.style.setProperty("--rx", `${(0.5 - y) * 9}deg`);
    el.style.setProperty("--ry", `${(x - 0.5) * 11}deg`);
    el.style.setProperty("--mx", `${x * 100}%`);
    el.style.setProperty("--my", `${y * 100}%`);
  };
  const leave = () => {
    const el = ref.current;
    if (!el) return;
    el.style.setProperty("--rx", "0deg");
    el.style.setProperty("--ry", "0deg");
  };
  return (
    <div ref={ref} onPointerMove={move} onPointerLeave={leave} className={cn("cv-tilt group relative", className)} style={style}>
      {children}
      <span aria-hidden className="cv-spot pointer-events-none absolute inset-0 rounded-[inherit] opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
    </div>
  );
}

export function useTypewriter(text: string, key: unknown, speed = 14) {
  const [out, setOut] = useState(text);
  useEffect(() => {
    if (reduced()) return setOut(text);
    setOut("");
    let i = 0;
    const id = window.setInterval(() => {
      i += 2;
      setOut(text.slice(0, i));
      if (i >= text.length) window.clearInterval(id);
    }, speed);
    return () => window.clearInterval(id);
  }, [text, key, speed]);
  return out;
}

/** Slowly morphing colour blobs. */
export function Aurora({ className }: { className?: string }) {
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}>
      <span className="cv-blob" style={{ left: "-8%", top: "-30%", width: 420, height: 420, background: "#34D399" }} />
      <span className="cv-blob" style={{ right: "-6%", top: "-20%", width: 380, height: 380, background: "#38BDF8", animationDelay: "-6s" }} />
      <span className="cv-blob" style={{ left: "38%", bottom: "-50%", width: 460, height: 460, background: "#A78BFA", animationDelay: "-12s" }} />
      <span className="absolute inset-0 opacity-[0.07]" style={{ backgroundImage: "linear-gradient(#fff 1px,transparent 1px),linear-gradient(90deg,#fff 1px,transparent 1px)", backgroundSize: "36px 36px" }} />
    </div>
  );
}

export function Marquee({ items }: { items: string[] }) {
  const row = [...items, ...items];
  return (
    <div className="relative overflow-hidden [mask-image:linear-gradient(90deg,transparent,#000_10%,#000_90%,transparent)]">
      <div className="cv-marquee flex w-max gap-3">
        {row.map((t, i) => (
          <span key={i} className="whitespace-nowrap rounded-full border border-white/15 bg-white/10 px-3.5 py-1.5 text-xs font-medium text-white/85 backdrop-blur">{t}</span>
        ))}
      </div>
    </div>
  );
}
