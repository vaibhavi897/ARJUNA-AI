/** ARJUNA AI opening screen: a high-end Manhattan law-firm atmosphere for ambitious people. */
import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { ArrowRight, ChevronDown, Crosshair, Gauge, Layers } from "lucide-react";
import { useAuth } from "../lib/auth";
import { useCinematic } from "../components/Cinematic";
import { GoldButton, QuoteRotator, SuitsScene, Wordmark, Words } from "../components/suits";
import { CountUp, Reveal } from "../components/fx";

const STANDARD = [
  { n: "01", icon: <Gauge size={22} />, title: "Know exactly where you stand", text: "A readiness score for every role you target, traced to your own data. No flattery, no guesswork." },
  { n: "02", icon: <Crosshair size={22} />, title: "Walk in prepared", text: "See the gaps before the room does. A roadmap ordered by the points at stake, so every hour moves the needle." },
  { n: "03", icon: <Layers size={22} />, title: "Step into the career first", text: "Live a day in 50+ professions, study the real pay, employers and path, then choose with your eyes open." },
];

export default function Landing() {
  const { user, loading } = useAuth();
  const { go } = useCinematic();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);

  if (!loading && user) return <Navigate to={user.onboarding_completed ? "/app/dashboard" : "/onboarding"} replace />;

  return (
    <div className="su-dark min-h-screen bg-[#05070B] font-sans text-white selection:bg-[#E6C878] selection:text-black">
      {/* nav */}
      <header className={"fixed inset-x-0 top-0 z-50 transition-all duration-500 " + (scrolled ? "border-b border-white/10 bg-black/70 py-3 backdrop-blur-xl" : "py-6")}>
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6">
          <Wordmark />
          <nav className="flex items-center gap-3 sm:gap-5">
            <button onClick={() => go("/login")} className="text-xs font-bold uppercase tracking-[0.22em] text-white/80 transition hover:text-[#E6C878]">Login</button>
            <GoldButton onClick={() => go("/register")} className="!px-5 !py-2.5 !text-xs">Register</GoldButton>
          </nav>
        </div>
      </header>

      {/* hero */}
      <section className="relative isolate flex min-h-screen items-center overflow-hidden">
        <SuitsScene />
        <div className="relative mx-auto w-full max-w-7xl px-6 pb-24 pt-32">
          <p className="su-fade mb-6 flex items-center gap-3 text-[11px] font-bold uppercase tracking-[0.5em] text-[#E6C878]" style={{ animationDelay: "200ms" }}>
            <span className="h-px w-12 bg-[#E6C878]" /> For the ambitious
          </p>
          <h1 className="font-suits text-5xl font-bold leading-[1.02] tracking-tight sm:text-7xl lg:text-[5.6rem]">
            <Words text="Winners don't make excuses." delay={350} step={120} />
            <br />
            <Words wordClass="su-gold-text" text="They make moves." delay={1300} step={150} />
          </h1>
          <p className="su-rise mt-8 max-w-xl text-lg leading-8 text-white/70" style={{ animationDelay: "1900ms" }}>
            ARJUNA AI is where ambition gets a system. Measure your readiness, close the gaps, and walk into every room already prepared.
          </p>
          <div className="su-rise mt-10 flex flex-wrap items-center gap-4" style={{ animationDelay: "2200ms" }}>
            <GoldButton onClick={() => go("/register")}>Register <ArrowRight size={16} /></GoldButton>
            <GoldButton variant="ghost" onClick={() => go("/login")}>Login</GoldButton>
          </div>
          <div className="su-fade mt-16 max-w-2xl border-l-2 border-[#E6C878]/70 pl-6" style={{ animationDelay: "2800ms" }}>
            <QuoteRotator className="min-h-[96px] text-xl leading-8 text-white/85 sm:text-2xl" start={1} />
          </div>
        </div>
        <a href="#standard" aria-label="Scroll" className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce text-white/50 hover:text-[#E6C878]"><ChevronDown /></a>
      </section>

      {/* the standard */}
      <section id="standard" className="relative bg-[#07090D] px-6 py-28">
        <div className="mx-auto max-w-7xl">
          <Reveal>
            <p className="text-[11px] font-bold uppercase tracking-[0.5em] text-[#E6C878]">The standard</p>
            <h2 className="mt-4 max-w-3xl font-suits text-4xl font-bold leading-tight sm:text-5xl">This is not another student platform. It is where your ambition <span className="su-gold-text">starts to compound.</span></h2>
          </Reveal>
          <div className="mt-14 grid gap-6 md:grid-cols-3">
            {STANDARD.map((s, i) => (
              <Reveal key={s.n} delay={i * 120}>
                <div className="su-glass su-card h-full rounded-sm p-8">
                  <div className="flex items-center justify-between"><span className="grid h-12 w-12 place-items-center border border-[#E6C878]/40 text-[#E6C878]">{s.icon}</span><span className="font-suits text-5xl font-bold text-white/10">{s.n}</span></div>
                  <h3 className="mt-6 font-suits text-2xl font-bold leading-snug">{s.title}</h3>
                  <p className="mt-3 leading-7 text-white/60">{s.text}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* quote band */}
      <section className="relative isolate overflow-hidden px-6 py-32">
        <SuitsScene dim />
        <div className="relative mx-auto max-w-5xl text-center">
          <Reveal><p className="font-suits text-3xl font-semibold italic leading-snug sm:text-5xl">&ldquo;The world doesn&rsquo;t reward potential. It rewards <span className="su-gold-text not-italic">execution.</span>&rdquo;</p></Reveal>
          <div className="mt-14 grid grid-cols-3 gap-4">
            {[{ n: 50, s: "+", l: "Professions to explore" }, { n: 9, s: "", l: "Industries" }, { n: 100, s: "%", l: "Traceable scoring" }].map((x) => (
              <Reveal key={x.l}><div className="su-glass rounded-sm px-4 py-6"><p className="font-suits text-4xl font-bold text-[#E6C878] sm:text-5xl"><CountUp value={x.n} />{x.s}</p><p className="mt-2 text-xs uppercase tracking-[0.2em] text-white/60">{x.l}</p></div></Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* final call */}
      <section className="bg-[#05070B] px-6 py-28 text-center">
        <Reveal>
          <p className="font-suits text-4xl font-bold sm:text-6xl">Your move.</p>
          <p className="mx-auto mt-5 max-w-xl text-white/60">Be so prepared that opportunity feels like an appointment.</p>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <GoldButton onClick={() => go("/register")}>Create your account <ArrowRight size={16} /></GoldButton>
            <GoldButton variant="ghost" onClick={() => go("/login")}>I already have one</GoldButton>
          </div>
        </Reveal>
        <p className="mt-24 text-[11px] uppercase tracking-[0.4em] text-white/30">Arjuna AI &middot; Built for people who intend to win</p>
      </section>
    </div>
  );
}
