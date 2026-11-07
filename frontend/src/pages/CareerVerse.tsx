/** CareerVerse landing: cinematic hero, live filters, tilt cards, compare tray. */
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, BarChart3, BookOpen, Bookmark, BookmarkCheck, GitCompare, Search, Sparkles, X } from "lucide-react";
import { AppShell } from "../components/layout";
import { Button, EmptyState, ErrorState, InlineNote } from "../components/ui";
import { SceneArt, useApi, type CareerCard } from "../components/careerverse";
import { Aurora, CountUp, Marquee, Reveal, TiltCard } from "../components/fx";
import { request } from "../lib/api";
import { useToast } from "../lib/auth";
import { cn } from "../lib/utils";

type Listing = { items: CareerCard[]; total: number; industries: { industry: string; count: number }[] };
type Recs = {
  profile_ready: boolean;
  scores: Record<string, number>;
  top: { career_id: number; slug: string; title: string; industry: string; score: number; matched_skills: string[] }[];
  disclaimer?: string;
};

const THEME_EMOJI: Record<string, string> = { finance: "💹", consulting: "🧭", tech: "🚀", data: "🔮", product: "💡", business: "🤝", security: "🛡️", invest: "🌱", office: "📁" };

function AlignmentRing({ score }: { score: number }) {
  const r = 17, c = 2 * Math.PI * r;
  return (
    <div className="relative grid h-11 w-11 place-items-center" title={`${Math.round(score)}/100 alignment with your profile`}>
      <svg viewBox="0 0 44 44" className="absolute inset-0 -rotate-90">
        <circle cx="22" cy="22" r={r} fill="none" stroke="rgba(255,255,255,.3)" strokeWidth="4" />
        <circle cx="22" cy="22" r={r} fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - score / 100)} style={{ transition: "stroke-dashoffset 1s ease" }} />
      </svg>
      <span className="text-[11px] font-extrabold text-white">{Math.round(score)}</span>
    </div>
  );
}

export default function CareerVerse() {
  const navigate = useNavigate();
  const { push } = useToast();
  const [q, setQ] = useState("");
  const [industry, setIndustry] = useState("");
  const [mode, setMode] = useState<"stories" | "insights">("stories");
  const [savedOnly, setSavedOnly] = useState(false);
  const [compare, setCompare] = useState<CareerCard[]>([]);

  const path = `/careers?${new URLSearchParams({ ...(q.trim() ? { q: q.trim() } : {}), ...(industry ? { industry } : {}) })}`;
  const list = useApi<Listing>(path);
  const all = useApi<Listing>("/careers");
  const recs = useApi<Recs>("/career-fit");

  const items = useMemo(() => {
    let rows = list.data?.items ?? [];
    if (savedOnly) rows = rows.filter((c) => c.is_saved);
    const s = recs.data?.scores;
    if (s && Object.keys(s).length) rows = [...rows].sort((a, b) => (s[String(b.id)] ?? 0) - (s[String(a.id)] ?? 0));
    return rows;
  }, [list.data, savedOnly, recs.data]);

  const titles = useMemo(() => (all.data?.items ?? []).map((c) => c.title), [all.data]);

  async function toggleSave(c: CareerCard) {
    try {
      await request(`/careers/${c.id}/saved`, { method: "PUT", body: { saved: !c.is_saved } });
      list.setData((d) => (d ? { ...d, items: d.items.map((x) => (x.id === c.id ? { ...x, is_saved: !x.is_saved } : x)) } : d));
    } catch (e) {
      push({ title: "Could not save", description: (e as Error).message, variant: "error" });
    }
  }

  function toggleCompare(c: CareerCard) {
    setCompare((cur) => {
      if (cur.some((x) => x.id === c.id)) return cur.filter((x) => x.id !== c.id);
      if (cur.length >= 3) {
        push({ title: "You can compare up to three professions", variant: "info" });
        return cur;
      }
      return [...cur, c];
    });
  }

  const total = all.data?.total ?? 50;
  const industries = all.data?.industries ?? [];

  return (
    <AppShell title="CareerVerse" subtitle="Live a day in the role, then study the career in depth">
      <div className="mx-auto max-w-6xl space-y-8 pb-28">
        {/* ---------------- hero ---------------- */}
        <section className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-forest-900 via-forest-800 to-[#12305A] p-6 text-white shadow-xl sm:p-10">
          <Aurora />
          <div className="relative grid items-center gap-8 lg:grid-cols-[1.25fr_1fr]">
            <div className="cv-rise">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold backdrop-blur">
                <Sparkles size={13} className="text-emerald-300" /> CareerVerse
              </span>
              <h1 className="mt-4 font-display !text-white text-4xl font-extrabold leading-[1.05] sm:text-5xl">
                Step into a career <span className="cv-gradient-text">before you choose it.</span>
              </h1>
              <p className="mt-4 max-w-xl text-[15px] leading-7 text-white/75">
                Walk through a real working day, then open the data behind the profession: sourced pay, employers, growth path, lifestyle and the skills it takes.
              </p>

              <div role="tablist" aria-label="CareerVerse module" className="relative mt-6 inline-grid grid-cols-2 rounded-2xl border border-white/15 bg-white/10 p-1 backdrop-blur">
                <span aria-hidden className="absolute inset-y-1 left-1 w-[calc(50%-4px)] rounded-xl bg-white shadow-lg transition-transform duration-300 ease-out" style={{ transform: mode === "stories" ? "translateX(0)" : "translateX(100%)" }} />
                {(["stories", "insights"] as const).map((m) => (
                  <button key={m} role="tab" aria-selected={mode === m} onClick={() => setMode(m)}
                    className={cn("relative z-10 flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-bold transition-colors", mode === m ? "text-forest-800" : "text-white/80 hover:text-white")}>
                    {m === "stories" ? <BookOpen size={16} /> : <BarChart3 size={16} />}
                    {m === "stories" ? "Career Stories" : "Career Insights"}
                  </button>
                ))}
              </div>
              <p className="mt-3 h-5 text-xs text-white/60">
                {mode === "stories" ? "A chapter-by-chapter day in the life. Just press Next." : "Salary sources, companies, trajectory, lifestyle, skills and outlook."}
              </p>
            </div>

            <div className="grid grid-cols-3 gap-3 lg:grid-cols-1">
              {[
                { n: total, l: "Professions", e: "🧑‍💼" },
                { n: industries.length || 9, l: "Industries", e: "🏙️" },
                { n: 2, l: "Ways to explore", e: "🎬" },
              ].map((s, i) => (
                <div key={s.l} className="cv-float flex items-center gap-3 rounded-2xl border border-white/15 bg-white/10 p-3 backdrop-blur sm:p-4" style={{ animationDelay: `${-i * 1.4}s` }}>
                  <span className="text-3xl">{s.e}</span>
                  <div><p className="text-2xl font-extrabold leading-none"><CountUp value={s.n} /></p><p className="mt-1 text-xs text-white/65">{s.l}</p></div>
                </div>
              ))}
            </div>
          </div>
          {titles.length ? <div className="relative mt-8"><Marquee items={titles} /></div> : null}
        </section>

        {/* ---------------- recommendations ---------------- */}
        {recs.data?.profile_ready && recs.data.top.length ? (
          <section aria-labelledby="rec-h" className="space-y-3">
            <h2 id="rec-h" className="flex items-center gap-2 text-lg font-extrabold"><Sparkles size={18} className="text-brand-600" /> Picked from your profile</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {recs.data.top.slice(0, 4).map((r, i) => (
                <Reveal key={r.career_id} delay={i * 80}>
                  <Link to={`/app/careerverse/${r.slug}/insights`} className="group block rounded-2xl border border-line bg-white p-4 transition hover:-translate-y-1 hover:border-brand-300 hover:shadow-lg">
                    <p className="text-xs font-medium text-ink-500">{r.industry}</p>
                    <p className="mt-0.5 font-bold">{r.title}</p>
                    {r.matched_skills?.length ? <p className="mt-2 line-clamp-2 text-xs text-ink-500">Matches your {r.matched_skills.slice(0, 3).join(", ")}</p> : null}
                    <p className="mt-1.5 flex items-center justify-end text-xs"><ArrowRight size={14} className="text-ink-300 transition group-hover:translate-x-1 group-hover:text-brand-600" /></p>
                  </Link>
                </Reveal>
              ))}
            </div>
            <p className="text-xs text-ink-500">{recs.data.disclaimer}</p>
          </section>
        ) : recs.data && !recs.data.profile_ready ? (
          <InlineNote tone="brand">Personalised picks appear once your profile has skills, projects or a parsed resume. Every profession is open to explore meanwhile.</InlineNote>
        ) : null}

        {/* ---------------- search + filters ---------------- */}
        <section className="sticky top-0 z-20 -mx-1 space-y-3 rounded-2xl bg-surface-sunken/85 px-1 py-3 backdrop-blur-md">
          <div className="flex flex-wrap items-center gap-3">
            <label className="relative min-w-[240px] flex-1">
              <Search size={17} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-ink-400" />
              <input aria-label="Search professions" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search: banker, data, design, security..."
                className="h-12 w-full rounded-2xl border border-line-strong bg-white pl-11 pr-10 text-sm shadow-sm outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-100" />
              {q ? <button aria-label="Clear search" onClick={() => setQ("")} className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-ink-400 hover:bg-sage-100"><X size={15} /></button> : null}
            </label>
            <button onClick={() => setSavedOnly((v) => !v)} aria-pressed={savedOnly}
              className={cn("flex h-12 items-center gap-2 rounded-2xl border px-4 text-sm font-bold transition", savedOnly ? "border-brand-500 bg-brand-600 text-white" : "border-line-strong bg-white text-ink-700 hover:border-brand-400")}>
              <BookmarkCheck size={16} /> Saved
            </button>
          </div>
          <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 [scrollbar-width:none]" role="tablist" aria-label="Industry filter">
            {[{ industry: "", count: total }, ...industries].map((i) => (
              <button key={i.industry || "all"} role="tab" aria-selected={industry === i.industry} onClick={() => setIndustry(i.industry)}
                className={cn("shrink-0 rounded-full border px-4 py-1.5 text-sm font-semibold transition-all", industry === i.industry ? "scale-105 border-forest-800 bg-forest-800 text-white shadow-md" : "border-line-strong bg-white text-ink-600 hover:border-brand-400 hover:text-brand-700")}>
                {i.industry || "All"} <span className={cn("ml-1 text-xs", industry === i.industry ? "text-white/60" : "text-ink-400")}>{i.count}</span>
              </button>
            ))}
          </div>
        </section>

        {list.error ? <ErrorState message={list.error} onRetry={list.reload} /> : null}
        {list.loading && !list.data ? (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{Array.from({ length: 6 }, (_, i) => <div key={i} className="h-72 animate-pulse rounded-3xl bg-sage-100" />)}</div>
        ) : null}
        {list.data && !items.length ? <EmptyState icon={<Search size={20} />} title={savedOnly ? "No saved professions yet" : "No professions match"} description={savedOnly ? "Tap the bookmark on a card to keep it here." : "Try another search or pick a different industry."} /> : null}

        {/* ---------------- cards ---------------- */}
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((c, idx) => {
            const score = recs.data?.scores?.[String(c.id)];
            const selected = compare.some((x) => x.id === c.id);
            const pct = c.scene_count ? Math.round((c.story_last_scene / c.scene_count) * 100) : 0;
            return (
              <Reveal key={c.id} delay={(idx % 6) * 60}>
                <TiltCard className={cn("overflow-hidden rounded-3xl border bg-white shadow-sm", selected ? "border-brand-500 ring-2 ring-brand-300" : "border-line")}>
                  <div className="relative">
                    <SceneArt theme={c.visual_theme} visual="desk" size="sm" className="h-32" label={`${c.title} illustration`} />
                    <span aria-hidden className="absolute -bottom-3 right-4 text-6xl opacity-90 drop-shadow-lg transition-transform duration-300 group-hover:-translate-y-2 group-hover:scale-110">{THEME_EMOJI[c.visual_theme] ?? "📁"}</span>
                    <div className="absolute left-3 top-3 flex items-center gap-2">
                      <span className="rounded-full bg-black/30 px-2.5 py-1 text-[11px] font-bold text-white backdrop-blur">{c.industry}</span>
                    </div>
                    <div className="absolute right-3 top-3 flex items-center gap-1.5">
                      
                      <button onClick={() => toggleSave(c)} aria-label={c.is_saved ? "Remove from saved" : "Save profession"} className="grid h-9 w-9 place-items-center rounded-full bg-white/20 text-white backdrop-blur transition hover:scale-110 hover:bg-white/35 active:scale-90">
                        {c.is_saved ? <BookmarkCheck size={17} className="cv-pop" /> : <Bookmark size={17} />}
                      </button>
                    </div>
                  </div>
                  <div className="space-y-3 p-5 pt-6">
                    <div>
                      <h3 className="text-lg font-extrabold leading-snug">{c.title}</h3>
                      <p className="mt-1 line-clamp-2 text-sm leading-6 text-ink-500">{c.short_description}</p>
                    </div>
                    {c.story_last_scene > 0 ? (
                      <div>
                        <div className="flex justify-between text-[11px] font-semibold text-ink-500"><span>{c.story_completed ? "Story finished" : `Scene ${c.story_last_scene} of ${c.scene_count}`}</span><span>{pct}%</span></div>
                        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-sage-200"><div className="cv-grow h-full rounded-full bg-brand-500" style={{ width: `${pct}%` }} /></div>
                      </div>
                    ) : null}
                    <div className="grid grid-cols-2 gap-2">
                      <Link to={`/app/careerverse/${c.slug}/story`} className="block">
                        <Button fullWidth size="sm" variant={mode === "stories" ? "primary" : "outline"} icon={<BookOpen size={14} />} className={mode === "stories" ? "cv-pulse-ring" : ""}>{c.story_last_scene > 0 && !c.story_completed ? "Resume story" : "Explore story"}</Button>
                      </Link>
                      <Link to={`/app/careerverse/${c.slug}/insights`} className="block">
                        <Button fullWidth size="sm" variant={mode === "insights" ? "primary" : "outline"} icon={<BarChart3 size={14} />} className={mode === "insights" ? "cv-pulse-ring" : ""}>Insights</Button>
                      </Link>
                    </div>
                    <button onClick={() => toggleCompare(c)} className={cn("flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed py-1.5 text-xs font-semibold transition", selected ? "border-brand-500 bg-brand-50 text-brand-700" : "border-line-strong text-ink-500 hover:border-brand-400 hover:text-brand-700")}>
                      <GitCompare size={13} /> {selected ? "Added to comparison" : "Add to comparison"}
                    </button>
                  </div>
                </TiltCard>
              </Reveal>
            );
          })}
        </div>
      </div>

      {/* ---------------- compare tray ---------------- */}
      <div className={cn("fixed inset-x-0 bottom-4 z-30 flex justify-center px-4 transition-all duration-500", compare.length ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-24 opacity-0")}>
        <div className="flex max-w-full items-center gap-3 rounded-2xl border border-white/20 bg-forest-900/95 p-2.5 pl-4 text-white shadow-2xl backdrop-blur-xl">
          <GitCompare size={18} className="shrink-0 text-emerald-300" />
          <div className="flex min-w-0 gap-1.5 overflow-x-auto">
            {compare.map((c) => (
              <button key={c.id} onClick={() => toggleCompare(c)} className="flex shrink-0 items-center gap-1 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold transition hover:bg-white/25">{c.title} <X size={12} /></button>
            ))}
          </div>
          <Button size="sm" disabled={compare.length < 2} onClick={() => navigate(`/app/careerverse/compare?ids=${compare.map((c) => c.id).join(",")}`)}>
            {compare.length < 2 ? "Pick one more" : "Compare now"}
          </Button>
        </div>
      </div>
    </AppShell>
  );
}
