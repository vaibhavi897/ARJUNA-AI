/**
 * Cinematic route transition.
 * Glass shutters sweep shut -> three one-liners flash by (each with a light
 * flash and a progress line) -> the route changes behind the curtain ->
 * shutters sweep open on the new page.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { QUOTES, Words } from "./suits";

type Phase = "idle" | "closing" | "quote" | "opening";
const Ctx = createContext<{ go: (path: string) => void } | null>(null);
const SHUTTERS = 9;
const CLOSE_MS = 1300;
const QUOTE_MS = 1900;
const COUNT = 3;
const OPEN_MS = 1500;

function pickQuotes(): string[] {
  const pool = [...QUOTES].sort(() => Math.random() - 0.5);
  return pool.slice(0, COUNT);
}

export function CinematicProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<Phase>("idle");
  const [quotes, setQuotes] = useState<string[]>(() => pickQuotes());
  const [qi, setQi] = useState(0);
  const busy = useRef(false);
  const timers = useRef<number[]>([]);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const go = useCallback(
    (path: string) => {
      if (busy.current) return;
      if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return navigate(path);
      busy.current = true;
      setQuotes(pickQuotes());
      setQi(0);
      setPhase("closing");
      const at = (ms: number, fn: () => void) => timers.current.push(window.setTimeout(fn, ms));
      at(CLOSE_MS, () => setPhase("quote"));
      for (let i = 1; i < COUNT; i++) at(CLOSE_MS + i * QUOTE_MS, () => setQi(i));
      const navAt = CLOSE_MS + COUNT * QUOTE_MS;
      at(navAt, () => { navigate(path); setPhase("opening"); });
      at(navAt + OPEN_MS + 400, () => { setPhase("idle"); busy.current = false; });
    },
    [navigate]
  );

  const value = useMemo(() => ({ go }), [go]);
  return (
    <Ctx.Provider value={value}>
      {children}
      {phase !== "idle" ? (
        <div className="fixed inset-0 z-[100]" aria-hidden role="presentation">
          <div className="absolute inset-0 flex">
            {Array.from({ length: SHUTTERS }, (_, i) => (
              <div key={i} className="relative h-full flex-1 overflow-hidden">
                <div className={`su-shutter ${phase === "opening" ? "su-shutter-open" : "su-shutter-close"}`} style={{ animationDelay: `${(phase === "opening" ? SHUTTERS - 1 - i : i) * 120}ms` }} />
              </div>
            ))}
          </div>

          {phase === "quote" ? (
            <>
              <div key={`flash${qi}`} className="su-flash pointer-events-none absolute inset-0" />
              <div className="absolute inset-0 grid place-items-center px-6 text-center">
                <div key={qi} className="su-qwrap max-w-4xl" style={{ ["--qms" as any]: `${QUOTE_MS}ms` }}>
                  <span className="su-rule mx-auto mb-7 block h-px bg-[#E6C878]" />
                  <p className="font-suits text-3xl font-semibold leading-tight text-white sm:text-5xl lg:text-6xl"><Words text={quotes[qi]} step={70} /></p>
                  <p className="mt-7 text-[11px] font-bold uppercase tracking-[0.5em] text-[#E6C878]">0{qi + 1} <span className="text-white/30">/ 0{COUNT}</span></p>
                </div>
              </div>
              <div className="absolute inset-x-0 bottom-0 h-[3px] bg-white/10">
                <div className="su-progress h-full bg-gradient-to-r from-[#C9A24B] to-[#F6E3A8]" style={{ ["--total" as any]: `${COUNT * QUOTE_MS}ms` }} />
              </div>
            </>
          ) : null}
        </div>
      ) : null}
    </Ctx.Provider>
  );
}

export function useCinematic() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useCinematic must be used inside CinematicProvider");
  return c;
}
