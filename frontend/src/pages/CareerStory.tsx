/** Career Stories: a cinematic, one-scene-at-a-time day in the life. Next / Previous only. */
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, BarChart3, Clock, Globe2, Moon, RotateCcw, Sun, Sunrise, Sunset, Wrench } from "lucide-react";
import { AppShell } from "../components/layout";
import { Button, EmptyState, ErrorState, LoadingBlock } from "../components/ui";
import { Chip, SceneArt, useApi } from "../components/careerverse";
import { SceneAnimation, ROLES, seedOf } from "../components/SceneAnimation";
import { Aurora, useTypewriter } from "../components/fx";
import { request } from "../lib/api";
import { cn } from "../lib/utils";

type Overview = {
  career: { id: number; slug: string; title: string; industry: string; visual_theme: string };
  title: string;
  summary: string | null;
  source: string;
  scene_count: number;
  scenes: { scene_number: number; heading: string; time_of_day: string; visual_key: string }[];
  progress: { last_scene_number: number; completed: boolean; resume_scene: number; can_resume: boolean };
};
type Scene = {
  scene_number: number; total_scenes: number; time_of_day: string; heading: string; narrative: string;
  activities: string[]; tools: string[]; responsibilities: string[]; industry_context: string | null; environment: string | null;
  visual_key: string; previous_scene: number | null; next_scene: number | null;
};

const THEME: Record<string, [string, string]> = {
  finance: ["#0C3326", "#2B6B4E"], consulting: ["#13324A", "#2F6F8F"], tech: ["#1B2B4B", "#3F63A8"], data: ["#2A2150", "#6247AA"],
  product: ["#4A2340", "#A04A86"], business: ["#4A3216", "#B07A2B"], security: ["#3A1818", "#A33B3B"], invest: ["#12383A", "#2E8C86"], office: ["#26382E", "#5F8F76"],
};

/** "09:30 AM" -> 24h hour (fractional). */
function hourOf(t: string): number {
  const m = /(\d{1,2}):(\d{2})\s*(AM|PM)?/i.exec(t);
  if (!m) return 12;
  let h = Number(m[1]) % 12;
  if (/pm/i.test(m[3] ?? "") || (!m[3] && Number(m[1]) >= 12)) h += 12;
  return h + Number(m[2]) / 60;
}

function skyFor(h: number): { overlay: string; label: string; icon: React.ReactNode } {
  if (h < 9.5) return { overlay: "linear-gradient(180deg, rgba(255,170,90,.38), rgba(255,120,150,.12) 60%, transparent)", label: "Morning", icon: <Sunrise size={14} /> };
  if (h < 16.5) return { overlay: "linear-gradient(180deg, rgba(120,200,255,.20), transparent 70%)", label: "Daytime", icon: <Sun size={14} /> };
  if (h < 18.75) return { overlay: "linear-gradient(180deg, rgba(255,140,70,.40), rgba(160,70,150,.15) 65%, transparent)", label: "Evening", icon: <Sunset size={14} /> };
  return { overlay: "linear-gradient(180deg, rgba(8,12,50,.62), rgba(20,20,80,.25) 70%, transparent)", label: "Night", icon: <Moon size={14} /> };
}

export default function CareerStory() {
  const { slug = "" } = useParams();
  const overview = useApi<Overview>(`/career-stories/${slug}`);
  const [n, setN] = useState<number | null>(null);
  const [scene, setScene] = useState<Scene | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [dir, setDir] = useState<"next" | "prev">("next");

  const load = useCallback(
    async (num: number) => {
      setLoading(true);
      setError(null);
      try {
        const next = await request<Scene>(`/career-stories/${slug}/scenes/${num}`);
        setDir(n !== null && num < n ? "prev" : "next");
        setScene(next);
        setN(num);
        window.scrollTo({ top: 0, behavior: "smooth" });
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [slug, n]
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!scene || loading) return;
      if (e.key === "ArrowRight" && scene.next_scene) load(scene.next_scene);
      if (e.key === "ArrowLeft" && scene.previous_scene) load(scene.previous_scene);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [scene, loading, load]);

  const o = overview.data;
  const typed = useTypewriter(scene?.narrative ?? "", scene?.scene_number, 11);
  const sky = scene ? skyFor(hourOf(scene.time_of_day)) : null;
  const [ca, cb] = THEME[o?.career.visual_theme ?? "office"] ?? THEME.office;

  return (
    <AppShell title={o?.career.title ?? "Career Story"} subtitle="Career Stories: a day in the life"
      actions={<Link to="/app/careerverse"><Button variant="outline" size="sm" icon={<ArrowLeft size={14} />}>All professions</Button></Link>}>
      <div className="mx-auto max-w-6xl space-y-5">
        {overview.loading ? <LoadingBlock label="Loading story" rows={4} /> : null}
        {overview.error ? <ErrorState message={overview.error} onRetry={overview.reload} /> : null}

        {/* ---------------- cover ---------------- */}
        {o && n === null ? (
          <div className="cv-rise overflow-hidden rounded-[28px] bg-forest-900 text-white shadow-2xl">
            <div className="relative aspect-video max-h-[460px] w-full" style={{ background: `linear-gradient(135deg, ${ca}, ${cb})` }}>
              <Aurora />
              <SceneAnimation visual="arrival" role={slug} seed={seedOf(slug + "cover")} className="absolute inset-0 h-full w-full" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
              <div className="absolute inset-x-0 bottom-0 p-6 sm:p-8">
                <Chip tone="brand">{o.career.industry}</Chip>
                <h2 className="mt-3 font-display text-3xl font-extrabold leading-tight !text-white drop-shadow-lg sm:text-5xl">{o.title}</h2>
              </div>
            </div>
            <div className="space-y-5 p-6 sm:p-8">
              <p className="max-w-2xl text-white/80">{o.summary}</p>
              <div className="flex flex-wrap gap-2 text-xs text-white/70">
                {["No questions", "No choices", "Just Next and Previous", `${o.scene_count} scenes`].map((t) => <span key={t} className="rounded-full border border-white/20 px-3 py-1">{t}</span>)}
              </div>
              <div className="flex flex-wrap gap-3">
                <Button size="lg" className="cv-pulse-ring" onClick={() => load(1)} icon={<ArrowRight size={16} />}>{o.progress.can_resume ? "Start from the beginning" : o.progress.completed ? "Watch again" : "Begin the story"}</Button>
                {o.progress.can_resume ? <Button size="lg" variant="outline" className="!bg-white/10 !text-white !border-white/30" icon={<RotateCcw size={16} />} onClick={() => load(o.progress.resume_scene)}>Resume at scene {o.progress.resume_scene}</Button> : null}
              </div>
              <p className="text-xs text-white/50">{o.source === "gemini" ? "Narrated by Gemini from the profession dataset." : "Built from the profession's documented workflow."}</p>
            </div>
          </div>
        ) : null}

        {o && !overview.error && !o.scenes.length ? <EmptyState title="No scenes yet" /> : null}
        {error ? <ErrorState message={error} onRetry={n ? () => load(n) : undefined} /> : null}

        {/* ---------------- stage ---------------- */}
        {o && scene && n !== null && sky ? (
          <>
            {/* filmstrip */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 [scrollbar-width:none]" role="progressbar" aria-valuemin={1} aria-valuemax={scene.total_scenes} aria-valuenow={scene.scene_number} aria-label={`Scene ${scene.scene_number} of ${scene.total_scenes}`}>
              {o.scenes.map((s) => {
                const active = s.scene_number === scene.scene_number;
                const done = s.scene_number < scene.scene_number;
                return (
                  <button key={s.scene_number} onClick={() => load(s.scene_number)} title={`${s.scene_number}. ${s.heading} (${s.time_of_day})`} aria-label={`Go to scene ${s.scene_number}: ${s.heading}`}
                    className={cn("group relative h-11 shrink-0 overflow-hidden rounded-xl border-2 transition-all duration-300", active ? "w-28 border-brand-500 shadow-lg" : done ? "w-14 border-brand-300 opacity-90 hover:w-20" : "w-14 border-line opacity-60 hover:w-20 hover:opacity-100")}>
                    <SceneArt theme={o.career.visual_theme} visual={s.visual_key} size="sm" className="absolute inset-0" />
                    <span className="absolute inset-0 grid place-items-center bg-black/25 text-xs font-extrabold text-white">{s.scene_number}</span>
                    {active ? <span className="absolute inset-x-0 bottom-0 h-1 bg-brand-400" /> : null}
                  </button>
                );
              })}
            </div>

            {/* the scene */}
            <div key={scene.scene_number} className={cn(ROLES[slug] ? `cv-tr-${ROLES[slug].tr}` : dir === "next" ? "cv-slide-next" : "cv-slide-prev", "overflow-hidden rounded-[28px] border border-line bg-white shadow-xl", loading && "opacity-70")}>
              <div className="relative aspect-video w-full" style={{ background: `linear-gradient(135deg, ${ca}, ${cb})` }}>
                <SceneAnimation visual={scene.visual_key} role={slug} seed={seedOf(`${slug}-${scene.scene_number}`)} className="absolute inset-0 h-full w-full" />
                <div className="pointer-events-none absolute inset-0 transition-opacity duration-700" style={{ background: sky.overlay }} />
                <span aria-hidden className="pointer-events-none absolute -bottom-6 -left-2 select-none font-display text-[9rem] font-black leading-none text-white/10 sm:text-[12rem]">{String(scene.scene_number).padStart(2, "0")}</span>
                <div className="absolute left-4 top-4 flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-black/40 px-3 py-1.5 text-sm font-bold text-white backdrop-blur"><Clock size={14} /> {scene.time_of_day}</span>
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-white/20 px-3 py-1.5 text-xs font-semibold text-white backdrop-blur">{sky.icon} {sky.label}</span>
                </div>
                <span className="absolute right-4 top-4 rounded-full bg-white/90 px-3 py-1.5 text-xs font-extrabold text-forest-800">Scene {scene.scene_number} / {scene.total_scenes}</span>
              </div>
              <div className="h-1 bg-sage-200"><div className="h-full bg-gradient-to-r from-brand-500 to-emerald-300 transition-all duration-700" style={{ width: `${(scene.scene_number / scene.total_scenes) * 100}%` }} /></div>

              <div className="grid gap-6 p-6 sm:p-8 lg:grid-cols-[1.4fr_1fr]">
                <div className="space-y-4">
                  <h2 className="font-display text-2xl font-extrabold leading-tight sm:text-3xl">{scene.heading}</h2>
                  <p className={cn("min-h-[7.5rem] text-[16px] leading-8 text-ink-700", typed.length < scene.narrative.length && "cv-caret")} aria-label={scene.narrative}>{typed}</p>
                  {scene.activities.length ? (
                    <ul className="space-y-1.5">
                      {scene.activities.map((a, i) => (
                        <li key={a} className="cv-rise flex gap-2.5 text-sm text-ink-600" style={{ animationDelay: `${0.35 + i * 0.12}s` }}>
                          <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand-500" />{a}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>

                <aside className="space-y-4">
                  {scene.tools.length ? (
                    <div className="rounded-2xl bg-sage-50 p-4">
                      <h3 className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wide text-forest-700"><Wrench size={13} /> Tools and software</h3>
                      <div className="mt-2.5 flex flex-wrap gap-1.5">{scene.tools.map((t, i) => <span key={t} className="cv-pop" style={{ animationDelay: `${0.2 + i * 0.1}s` }}><Chip tone="brand">{t}</Chip></span>)}</div>
                    </div>
                  ) : null}
                  {scene.responsibilities.length ? (
                    <div className="rounded-2xl bg-sage-50 p-4">
                      <h3 className="text-xs font-extrabold uppercase tracking-wide text-forest-700">Professional responsibility</h3>
                      <ul className="mt-2 space-y-1.5 text-sm text-ink-600">{scene.responsibilities.map((r) => <li key={r}>{r}</li>)}</ul>
                    </div>
                  ) : null}
                  {scene.environment || scene.industry_context ? (
                    <div className="space-y-2 rounded-2xl border border-line p-4 text-sm text-ink-600">
                      {scene.environment ? <p><span className="font-bold text-forest-800">Workplace. </span>{scene.environment}</p> : null}
                      {scene.industry_context ? <p className="flex gap-1.5"><Globe2 size={14} className="mt-1 shrink-0 text-brand-600" /><span>{scene.industry_context.replace(/^Industry context:\s*/, "")}</span></p> : null}
                    </div>
                  ) : null}
                </aside>
              </div>
            </div>

            {/* navigation */}
            <div className="sticky bottom-3 z-10 flex items-center justify-between gap-3 rounded-2xl border border-line bg-white/90 p-2.5 shadow-lg backdrop-blur-md">
              <Button variant="outline" size="lg" icon={<ArrowLeft size={16} />} disabled={!scene.previous_scene || loading} onClick={() => scene.previous_scene && load(scene.previous_scene)}>Previous</Button>
              <p className="hidden text-xs text-ink-400 sm:block">Tip: use the <kbd className="rounded border border-line px-1.5">←</kbd> <kbd className="rounded border border-line px-1.5">→</kbd> keys</p>
              {scene.next_scene ? (
                <Button size="lg" disabled={loading} onClick={() => load(scene.next_scene!)}>Next <ArrowRight size={16} className="cv-nudge ml-1" /></Button>
              ) : (
                <Link to={`/app/careerverse/${slug}/insights`}><Button size="lg" variant="forest" icon={<BarChart3 size={16} />}>Finish: see the career data</Button></Link>
              )}
            </div>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
