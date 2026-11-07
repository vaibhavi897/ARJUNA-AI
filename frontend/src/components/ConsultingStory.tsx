/**
 * The Consulting career story: a scene-by-scene, image-led walk through a real
 * consulting engagement.
 *
 * Presentation only — every fact comes from `lib/consultingStoryData.ts`, which
 * carries the source profile sentences verbatim. Progress is kept locally and
 * mirrored to the existing CareerVerse story endpoint on a best-effort basis so
 * the CareerVerse cards and dashboard keep working.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  Building2,
  ChevronDown,
  Lightbulb,
  MapPin,
  Milestone,
  Loader2,
  Pause,
  Quote,
  RotateCcw,
  Sparkles,
  Target,
  Volume2,
  VolumeX,
  Wrench,
} from "lucide-react";
import { AppShell } from "./layout";
import { Button } from "./ui";
import { request } from "../lib/api";
import { useNarration } from "../lib/narration";
import { cn } from "../lib/utils";
import {
  CONSULTING_GLOSSARY,
  CONSULTING_PROFILE,
  CONSULTING_SCENES,
  CONSULTING_SCENE_COUNT,
  type ConsultingScene,
} from "../lib/consultingStoryData";

const STORAGE_KEY = `arjuna.story.${CONSULTING_PROFILE.slug}`;

// --------------------------------------------------------------- local progress
function readProgress(): number {
  try {
    const n = Number(localStorage.getItem(STORAGE_KEY));
    return Number.isFinite(n) && n > 0 && n <= CONSULTING_SCENE_COUNT ? n : 0;
  } catch {
    return 0;
  }
}
function writeProgress(n: number) {
  try {
    localStorage.setItem(STORAGE_KEY, String(n));
  } catch {
    /* private mode — the story still works, it just will not resume */
  }
}

/**
 * Mirror the position onto the stored CareerVerse story so existing progress
 * surfaces keep updating. Entirely optional: failures are swallowed.
 */
function useBackendMirror() {
  const total = useRef<number | null>(null);
  useEffect(() => {
    let alive = true;
    request<{ scene_count: number }>(`/career-stories/${CONSULTING_PROFILE.slug}`)
      .then((d) => {
        if (alive) total.current = d?.scene_count ?? null;
      })
      .catch(() => {
        /* story not seeded for this career — nothing to mirror */
      });
    return () => {
      alive = false;
    };
  }, []);

  return useCallback((sceneNumber: number) => {
    const dbTotal = total.current;
    if (!dbTotal || dbTotal < 1) return;
    const mapped = Math.min(
      dbTotal,
      Math.max(1, Math.round((sceneNumber / CONSULTING_SCENE_COUNT) * dbTotal))
    );
    request(`/career-stories/${CONSULTING_PROFILE.slug}/scenes/${mapped}`).catch(() => {});
  }, []);
}

// --------------------------------------------------------------- term highlighting
const GLOSSARY_TERMS = Object.keys(CONSULTING_GLOSSARY).sort((a, b) => b.length - a.length);
const TERM_RE = new RegExp(
  `\\b(${GLOSSARY_TERMS.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})\\b`,
  "gi"
);
const TERM_LOOKUP = new Map(GLOSSARY_TERMS.map((t) => [t.toLowerCase(), CONSULTING_GLOSSARY[t]]));

/** Wraps known consulting vocabulary in an explained, hoverable mark. */
function Highlighted({ text }: { text: string }) {
  const parts = useMemo(() => text.split(TERM_RE), [text]);
  return (
    <>
      {parts.map((part, i) => {
        const def = TERM_LOOKUP.get(part.toLowerCase());
        if (!def) return <span key={i}>{part}</span>;
        return (
          <mark
            key={i}
            title={def}
            tabIndex={0}
            aria-label={`${part}: ${def}`}
            className="cs-term rounded bg-brand-50 px-1 font-semibold text-brand-700 decoration-brand-300 decoration-dotted underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-brand-400"
          >
            {part}
          </mark>
        );
      })}
    </>
  );
}

// --------------------------------------------------------------- small pieces
function Panel({
  icon,
  title,
  children,
  className,
}: {
  icon?: ReactNode;
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-2xl border border-line bg-surface-muted p-4", className)}>
      <h3 className="flex items-center gap-1.5 text-2xs font-extrabold uppercase tracking-[0.12em] text-forest-700">
        {icon}
        {title}
      </h3>
      <div className="mt-2.5">{children}</div>
    </section>
  );
}

function Pill({ children, tone = "sage" }: { children: ReactNode; tone?: "sage" | "brand" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold",
        tone === "brand" ? "bg-brand-50 text-brand-700" : "bg-sage-100 text-forest-800"
      )}
    >
      {children}
    </span>
  );
}

function Disclosure({
  icon,
  label,
  title,
  body,
  tone,
}: {
  icon: ReactNode;
  label: string;
  title: string;
  body: string;
  tone: "info" | "brand";
}) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className={cn(
        "overflow-hidden rounded-2xl border transition-colors",
        tone === "brand" ? "border-brand-200 bg-brand-50/50" : "border-line bg-white"
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-4 py-3 text-left"
      >
        <span className={cn("shrink-0", tone === "brand" ? "text-brand-600" : "text-info-500")}>{icon}</span>
        <span className="flex-1">
          <span className="block text-2xs font-extrabold uppercase tracking-[0.12em] text-ink-400">{label}</span>
          <span className="block text-sm font-bold text-forest-800">{title}</span>
        </span>
        <ChevronDown
          size={16}
          className={cn("shrink-0 text-ink-400 transition-transform duration-300", open && "rotate-180")}
        />
      </button>
      <div className={cn("grid transition-all duration-300 ease-smooth", open ? "grid-rows-[1fr]" : "grid-rows-[0fr]")}>
        <div className="overflow-hidden">
          <p className="px-4 pb-4 text-sm leading-7 text-ink-600">
            <Highlighted text={body} />
          </p>
        </div>
      </div>
    </div>
  );
}

function MetricStrip({ scene }: { scene: ConsultingScene }) {
  if (!scene.metrics?.length) return null;
  return (
    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
      {scene.metrics.map((m, i) => (
        <div
          key={m.label}
          className="cs-pop rounded-2xl border border-line bg-white p-3 shadow-sm"
          style={{ animationDelay: `${0.15 + i * 0.09}s` }}
        >
          <p className="font-display text-xl font-extrabold leading-tight text-forest-800 sm:text-2xl">{m.value}</p>
          <p className="mt-0.5 text-2xs font-medium leading-snug text-ink-500">{m.label}</p>
        </div>
      ))}
    </div>
  );
}

/** Scene image with a slow drift, pointer parallax and a load-in fade. */
function SceneImage({
  scene,
  className,
  priority,
}: {
  scene: ConsultingScene;
  className?: string;
  priority?: boolean;
}) {
  const [loaded, setLoaded] = useState(false);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  useEffect(() => setLoaded(false), [scene.image]);

  return (
    <div
      className={cn("group relative overflow-hidden bg-forest-900", className)}
      onPointerMove={(e) => {
        if (e.pointerType !== "mouse") return;
        const r = e.currentTarget.getBoundingClientRect();
        setOffset({ x: ((e.clientX - r.left) / r.width - 0.5) * -16, y: ((e.clientY - r.top) / r.height - 0.5) * -12 });
      }}
      onPointerLeave={() => setOffset({ x: 0, y: 0 })}
    >
      <div
        className="absolute inset-0 transition-transform duration-500 ease-smooth will-change-transform"
        style={{ transform: `translate3d(${offset.x}px, ${offset.y}px, 0)` }}
      >
        <img
          src={scene.image}
          alt={scene.imageAlt}
          loading={priority ? "eager" : "lazy"}
          decoding="async"
          onLoad={() => setLoaded(true)}
          onError={() => setLoaded(true)}
          style={{ objectPosition: scene.focus }}
          className={cn(
            "cs-ken h-full w-full scale-[1.08] object-cover transition-opacity duration-700",
            loaded ? "opacity-100" : "opacity-0"
          )}
        />
      </div>
      {!loaded ? (
        <div
          className="cs-shimmer absolute inset-0"
          style={{ background: `linear-gradient(135deg, ${scene.tone[0]}, ${scene.tone[1]})` }}
        />
      ) : null}
      {/* depth: a soft vignette so overlaid text stays readable */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_90%_at_50%_10%,transparent,rgba(5,16,12,0.45))]" />
    </div>
  );
}

// --------------------------------------------------------------- the story
export default function ConsultingStory() {
  const [n, setN] = useState<number | null>(null);
  const [dir, setDir] = useState<"next" | "prev">("next");
  const [resumeAt] = useState(readProgress);
  const mirror = useBackendMirror();
  const narration = useNarration();
  const stripRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);

  const scene = n ? CONSULTING_SCENES[n - 1] : null;
  const prev = n && n > 1 ? n - 1 : null;
  const next = n && n < CONSULTING_SCENE_COUNT ? n + 1 : null;

  const go = useCallback(
    (to: number, scroll = true) => {
      const target = Math.min(CONSULTING_SCENE_COUNT, Math.max(1, to));
      setDir((d) => (n === null ? "next" : target < n ? "prev" : target > n ? "next" : d));
      setN(target);
      writeProgress(target);
      mirror(target);
      if (scroll) {
        const top = stageRef.current ? stageRef.current.getBoundingClientRect().top + window.scrollY - 88 : 0;
        window.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
      }
    },
    [n, mirror]
  );

  // keyboard navigation
  useEffect(() => {
    if (n === null) return;
    const onKey = (e: KeyboardEvent) => {
      const el = document.activeElement;
      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) return;
      if (e.key === "ArrowRight" && next) {
        e.preventDefault();
        go(next);
      }
      if (e.key === "ArrowLeft" && prev) {
        e.preventDefault();
        go(prev);
      }
      if (e.key === "Home") go(1);
      if (e.key === "End") go(CONSULTING_SCENE_COUNT);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [n, next, prev, go]);

  // keep the active timeline chip in view
  useEffect(() => {
    if (n === null) return;
    stripRef.current?.querySelector<HTMLElement>(`[data-scene="${n}"]`)?.scrollIntoView({
      behavior: "smooth",
      inline: "center",
      block: "nearest",
    });
  }, [n]);

  // warm the neighbouring images so Next feels instant
  useEffect(() => {
    if (n === null) return;
    [n + 1, n - 1].forEach((i) => {
      const s = CONSULTING_SCENES[i - 1];
      if (s) {
        const img = new Image();
        img.src = s.image;
      }
    });
  }, [n]);

  // Narration follows the scene: stop whatever is playing, then read the new
  // scene aloud only if the student has switched auto-play on.
  const { available: canNarrate, autoplay, play: speak, stop: hush } = narration;
  useEffect(() => {
    hush();
    if (n === null || !canNarrate || !autoplay) return;
    const s = CONSULTING_SCENES[n - 1];
    if (s) speak(s.source);
  }, [n, canNarrate, autoplay, speak, hush]);

  // never keep talking after the student navigates away
  useEffect(() => () => hush(), [hush]);

  const pct = n ? (n / CONSULTING_SCENE_COUNT) * 100 : 0;
  const busy = narration.state === "loading";
  const speaking = narration.state === "playing";

  return (
    <AppShell
      title={`${CONSULTING_PROFILE.role} · ${CONSULTING_PROFILE.name}`}
      subtitle="Career Stories: inside a consulting engagement"
      actions={
        <Link to="/app/careerverse">
          <Button variant="outline" size="sm" icon={<ArrowLeft size={14} />}>
            All professions
          </Button>
        </Link>
      }
    >
      <div className="mx-auto max-w-6xl space-y-5">
        {/* ------------------------------------------------------------ cover */}
        {n === null ? (
          <div className="cs-rise overflow-hidden rounded-[28px] bg-forest-900 text-white shadow-2xl">
            <div className="relative h-[clamp(260px,46vw,480px)] w-full">
              <SceneImage scene={CONSULTING_SCENES[0]} className="absolute inset-0 h-full w-full" priority />
              <div className="absolute inset-0 bg-gradient-to-t from-forest-900 via-forest-900/55 to-transparent" />
              <div className="absolute inset-x-0 bottom-0 p-5 sm:p-8">
                <div className="flex flex-wrap items-center gap-2 text-2xs font-bold uppercase tracking-[0.18em] text-brand-200">
                  <span className="rounded-full border border-white/25 bg-black/25 px-3 py-1 backdrop-blur">
                    Management Consulting
                  </span>
                  <span className="inline-flex items-center gap-1.5 text-white/70">
                    <Building2 size={13} /> {CONSULTING_PROFILE.firm}
                  </span>
                  <span className="inline-flex items-center gap-1.5 text-white/70">
                    <MapPin size={13} /> {CONSULTING_PROFILE.location}
                  </span>
                </div>
                <h2 className="mt-3 font-display text-3xl font-extrabold leading-[1.05] !text-white drop-shadow-xl sm:text-5xl">
                  {CONSULTING_PROFILE.title}
                </h2>
                <p className="mt-2 max-w-xl text-sm text-white/80 sm:text-base">{CONSULTING_PROFILE.subtitle}</p>
              </div>
            </div>

            <div className="space-y-5 p-5 sm:p-8">
              <p className="max-w-3xl leading-8 text-white/80">
                <Highlighted text={CONSULTING_PROFILE.summary} />
              </p>
              <div className="flex flex-wrap gap-2 text-xs text-white/70">
                {["Original profile imagery", "Client: " + CONSULTING_PROFILE.client].map((t) => (
                  <span key={t} className="rounded-full border border-white/20 px-3 py-1">
                    {t}
                  </span>
                ))}
              </div>
              <div className="flex flex-wrap gap-3">
                <Button size="lg" className="cs-glow" onClick={() => go(1, false)} icon={<ArrowRight size={16} />}>
                  Begin the story
                </Button>
                {resumeAt > 0 && resumeAt < CONSULTING_SCENE_COUNT ? (
                  <Button
                    size="lg"
                    variant="outline"
                    className="!border-white/30 !bg-white/10 !text-white hover:!bg-white/20"
                    icon={<RotateCcw size={16} />}
                    onClick={() => go(resumeAt, false)}
                  >
                    Resume at scene {resumeAt}
                  </Button>
                ) : null}
              </div>
              <p className="max-w-3xl text-xs leading-6 text-white/45">{CONSULTING_PROFILE.sourceNote}</p>
            </div>
          </div>
        ) : null}

        {/* ------------------------------------------------------------ stage */}
        {scene && n !== null ? (
          <div ref={stageRef} className="space-y-4">
            {/* numbered timeline */}
            <div
              ref={stripRef}
              role="tablist"
              aria-label="Story scenes"
              className="flex items-center gap-1.5 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            >
              {CONSULTING_SCENES.map((s) => {
                const active = s.number === n;
                const done = s.number < n;
                return (
                  <button
                    key={s.number}
                    data-scene={s.number}
                    role="tab"
                    aria-selected={active}
                    onClick={() => go(s.number)}
                    title={`${s.number}. ${s.heading} · ${s.phase}`}
                    aria-label={`Scene ${s.number}: ${s.heading}`}
                    className={cn(
                      "group relative h-12 shrink-0 overflow-hidden rounded-xl border-2 transition-all duration-300",
                      active
                        ? "w-28 border-brand-500 shadow-lg sm:w-36"
                        : done
                          ? "w-12 border-brand-300 opacity-95 hover:w-20"
                          : "w-12 border-line opacity-55 hover:w-20 hover:opacity-100"
                    )}
                  >
                    <img
                      src={s.thumb}
                      alt=""
                      aria-hidden
                      width={288}
                      height={157}
                      loading="lazy"
                      decoding="async"
                      style={{ objectPosition: s.focus }}
                      className="absolute inset-0 h-full w-full object-cover"
                    />
                    <span className="absolute inset-0 grid place-items-center bg-forest-900/45 text-xs font-extrabold text-white">
                      {s.number}
                    </span>
                    {active ? <span className="absolute inset-x-0 bottom-0 h-1 bg-brand-400" /> : null}
                  </button>
                );
              })}
            </div>

            {/* progress */}
            <div className="flex items-center gap-3">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-sage-200">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-brand-600 to-brand-300 transition-all duration-700 ease-smooth"
                  style={{ width: `${pct}%` }}
                  role="progressbar"
                  aria-valuemin={1}
                  aria-valuemax={CONSULTING_SCENE_COUNT}
                  aria-valuenow={n}
                  aria-label={`Scene ${n} of ${CONSULTING_SCENE_COUNT}`}
                />
              </div>
              <span className="shrink-0 text-xs font-bold text-ink-500">
                Scene {n} / {CONSULTING_SCENE_COUNT}
              </span>
            </div>

            {/* the scene */}
            <article
              key={scene.number}
              className={cn(
                dir === "next" ? "cs-in-next" : "cs-in-prev",
                "overflow-hidden rounded-[28px] border border-line bg-white shadow-xl"
              )}
            >
              {scene.layout === "cinematic" ? (
                <header className="relative h-[clamp(240px,42vw,460px)] w-full">
                  <SceneImage scene={scene} className="absolute inset-0 h-full w-full" priority />
                  <div className="absolute inset-0 bg-gradient-to-t from-forest-900/92 via-forest-900/35 to-transparent" />
                  <span
                    aria-hidden
                    className="pointer-events-none absolute -bottom-7 right-3 select-none font-display text-[7rem] font-black leading-none text-white/10 sm:text-[11rem]"
                  >
                    {String(scene.number).padStart(2, "0")}
                  </span>
                  <SceneMeta scene={scene} overlay />
                  <div className="absolute inset-x-0 bottom-0 p-5 sm:p-8">
                    <p className="cs-fade text-2xs font-bold uppercase tracking-[0.18em] text-brand-200">
                      {scene.kicker}
                    </p>
                    <h2 className="cs-fade mt-1.5 max-w-3xl font-display text-2xl font-extrabold leading-tight !text-white drop-shadow-xl sm:text-4xl">
                      {scene.heading}
                    </h2>
                  </div>
                </header>
              ) : null}

              <div
                className={cn(
                  "grid gap-0",
                  scene.layout !== "cinematic" && "lg:grid-cols-2",
                  scene.layout === "split-right" && "lg:[&>figure]:order-2"
                )}
              >
                {scene.layout !== "cinematic" ? (
                  <figure className="relative h-[clamp(230px,48vw,420px)] w-full lg:h-auto lg:min-h-[460px]">
                    <SceneImage scene={scene} className="absolute inset-0 h-full w-full" priority />
                    <div className="absolute inset-0 bg-gradient-to-t from-forest-900/80 via-transparent to-forest-900/20 lg:bg-gradient-to-r lg:from-transparent lg:to-forest-900/25" />
                    <span
                      aria-hidden
                      className="pointer-events-none absolute bottom-1 left-3 select-none font-display text-[6rem] font-black leading-none text-white/15 sm:text-[8rem]"
                    >
                      {String(scene.number).padStart(2, "0")}
                    </span>
                    <SceneMeta scene={scene} overlay />
                  </figure>
                ) : null}

                <div className="space-y-5 p-5 sm:p-8">
                  {scene.layout !== "cinematic" ? (
                    <div>
                      <p className="text-2xs font-bold uppercase tracking-[0.18em] text-brand-600">{scene.kicker}</p>
                      <h2 className="mt-1.5 font-display text-2xl font-extrabold leading-tight text-forest-900 sm:text-3xl">
                        {scene.heading}
                      </h2>
                    </div>
                  ) : null}

                  <div className="space-y-3.5">
                    {scene.paragraphs.map((p, i) => (
                      <p
                        key={i}
                        className="cs-fade max-w-prose text-[16px] leading-8 text-ink-700"
                        style={{ animationDelay: `${0.1 + i * 0.1}s` }}
                      >
                        <Highlighted text={p} />
                      </p>
                    ))}
                  </div>

                  <MetricStrip scene={scene} />

                  <figure className="rounded-2xl border-l-4 border-brand-400 bg-sage-50 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <Quote size={14} className="mt-1 shrink-0 text-brand-500" />
                      {canNarrate ? (
                        <button
                          type="button"
                          onClick={() => (speaking || busy ? narration.stop() : narration.play(scene.source))}
                          aria-label={speaking || busy ? "Stop reading this aloud" : "Read this aloud"}
                          className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-brand-200 bg-white px-3 py-1.5 text-xs font-bold text-brand-700 transition-colors hover:bg-brand-50 disabled:opacity-60"
                        >
                          {busy ? (
                            <Loader2 size={13} className="animate-spin" />
                          ) : speaking ? (
                            <Pause size={13} />
                          ) : (
                            <Volume2 size={13} />
                          )}
                          {busy ? "Loading" : speaking ? "Stop" : "Listen"}
                        </button>
                      ) : null}
                    </div>
                    <blockquote
                      className={cn(
                        "mt-1.5 rounded-lg text-sm italic leading-7 text-forest-800 transition-colors",
                        speaking && "bg-brand-100/60 px-2 -mx-2"
                      )}
                    >
                      {scene.source}
                    </blockquote>
                    {narration.error ? (
                      <p className="mt-2 text-2xs font-medium text-danger-500">{narration.error}</p>
                    ) : null}
                  </figure>

                  <div className="grid gap-3 sm:grid-cols-2">
                    {scene.tools?.length ? (
                      <Panel icon={<Wrench size={12} />} title="Tools used here">
                        <div className="flex flex-wrap gap-1.5">
                          {scene.tools.map((t, i) => (
                            <span key={t} className="cs-pop" style={{ animationDelay: `${0.18 + i * 0.07}s` }}>
                              <Pill tone="brand">{t}</Pill>
                            </span>
                          ))}
                        </div>
                      </Panel>
                    ) : null}
                    {scene.skills?.length ? (
                      <Panel icon={<Target size={12} />} title="Consulting skills applied">
                        <div className="flex flex-wrap gap-1.5">
                          {scene.skills.map((s, i) => (
                            <span key={s} className="cs-pop" style={{ animationDelay: `${0.18 + i * 0.07}s` }}>
                              <Pill>{s}</Pill>
                            </span>
                          ))}
                        </div>
                      </Panel>
                    ) : null}
                  </div>

                  {scene.method ? (
                    <Disclosure
                      tone="info"
                      icon={<Sparkles size={16} />}
                      label="What is happening here?"
                      title={scene.method.title}
                      body={scene.method.body}
                    />
                  ) : null}
                  {scene.takeaway ? (
                    <div className="cs-fade flex items-start gap-3 rounded-2xl border border-brand-200 bg-brand-50/60 px-4 py-3.5">
                      <Lightbulb size={16} className="mt-0.5 shrink-0 text-brand-600" />
                      <p className="text-sm leading-7 text-forest-800">
                        <span className="mr-1.5 text-2xs font-extrabold uppercase tracking-[0.12em] text-brand-700">
                          Key takeaway
                        </span>
                        <Highlighted text={scene.takeaway} />
                      </p>
                    </div>
                  ) : null}
                </div>
              </div>
            </article>

            {/* navigation */}
            <nav className="sticky bottom-3 z-10 flex items-center justify-between gap-2 rounded-2xl border border-line bg-white/90 p-2.5 shadow-lg backdrop-blur-md">
              <Button
                variant="outline"
                size="lg"
                icon={<ArrowLeft size={16} />}
                disabled={!prev}
                onClick={() => prev && go(prev)}
              >
                <span className="hidden sm:inline">Previous</span>
              </Button>
              <div className="flex min-w-0 flex-1 items-center justify-center gap-3">
                <p className="hidden min-w-0 truncate text-center text-xs text-ink-400 lg:block">
                  {scene.phase} · use the <kbd className="rounded border border-line px-1.5">←</kbd>{" "}
                  <kbd className="rounded border border-line px-1.5">→</kbd> keys
                </p>
                {canNarrate ? (
                  <button
                    type="button"
                    role="switch"
                    aria-checked={autoplay}
                    onClick={() => narration.setAutoplay(!autoplay)}
                    title={autoplay ? "Narration plays on every scene" : "Read each scene aloud automatically"}
                    className={cn(
                      "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-bold transition-colors",
                      autoplay
                        ? "border-brand-300 bg-brand-50 text-brand-700"
                        : "border-line bg-white text-ink-500 hover:text-brand-700"
                    )}
                  >
                    {autoplay ? <Volume2 size={13} /> : <VolumeX size={13} />}
                    <span className="hidden sm:inline">Narration</span>
                  </button>
                ) : null}
              </div>
              {next ? (
                <Button size="lg" onClick={() => go(next)}>
                  <span className="hidden sm:inline">Next</span>
                  <ArrowRight size={16} className="cs-nudge sm:ml-1" />
                </Button>
              ) : (
                <Link to={`/app/careerverse/${CONSULTING_PROFILE.slug}/insights`}>
                  <Button size="lg" variant="forest" icon={<BarChart3 size={16} />}>
                    <span className="hidden sm:inline">Finish: see the career data</span>
                    <span className="sm:hidden">Career data</span>
                  </Button>
                </Link>
              )}
            </nav>

            <p className="px-1 pb-2 text-2xs leading-5 text-ink-400">
              Narrative, figures and images come from the Arjuna career profile “Profile 51 / Rohan Mehta”. Scenes
              follow the engagement in the order the profile describes it.
            </p>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}

/** Engagement-phase badge, shown over the image. */
function SceneMeta({ scene, overlay }: { scene: ConsultingScene; overlay?: boolean }) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2", overlay && "absolute left-4 top-4 z-[1]")}>
      <span className="inline-flex items-center gap-1.5 rounded-full bg-forest-900/55 px-3 py-1.5 text-sm font-bold text-white backdrop-blur">
        <Milestone size={13} /> {scene.phase}
      </span>
    </div>
  );
}
