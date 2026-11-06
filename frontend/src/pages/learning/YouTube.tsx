/** YouTube Summariser: structured study notes from the transcript. */
import { useMemo, useState } from "react";
import { BookmarkPlus, BookOpen, Briefcase, ClipboardPaste, ExternalLink, Layers, Link2, ListChecks, Loader2, Play, RefreshCw, Search, Wrench } from "lucide-react";
import { Badge, Button, Card, EmptyState, ErrorState, InlineNote } from "../../components/ui";
import { SaveToNotebook } from "../../components/learning/SaveToNotebook";
import { Skeleton, useLoad } from "../../components/learning/shared";
import { lh, type Video } from "../../lib/learning";
import { cn } from "../../lib/utils";

const ts = (s: number) => `${Math.floor(s / 3600) ? `${Math.floor(s / 3600)}:` : ""}${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
type Summary = NonNullable<Video["summary"]>;

function Section({ id, icon, title, hint, children }: { id: string; icon: React.ReactNode; title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-28 space-y-3">
      <div className="flex items-center gap-2.5"><span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-50 text-brand-700">{icon}</span><div><h4 className="text-lg font-extrabold text-forest-900">{title}</h4>{hint ? <p className="text-xs text-ink-500">{hint}</p> : null}</div></div>
      {children}
    </section>
  );
}

function Flashcard({ f }: { f: { front: string; back: string } }) {
  const [flip, setFlip] = useState(false);
  return (
    <button onClick={() => setFlip((x) => !x)} aria-label={flip ? "Show question" : "Show answer"} className="group h-36 [perspective:900px] text-left">
      <span className={cn("relative block h-full w-full rounded-2xl transition-transform duration-500 [transform-style:preserve-3d]", flip && "[transform:rotateY(180deg)]")}>
        <span className="absolute inset-0 grid place-items-center rounded-2xl border border-line bg-white p-4 text-center text-sm font-bold [backface-visibility:hidden]">{f.front}</span>
        <span className="absolute inset-0 grid place-items-center rounded-2xl bg-gradient-to-br from-brand-600 to-forest-700 p-4 text-center text-sm font-medium text-white [backface-visibility:hidden] [transform:rotateY(180deg)]">{f.back}</span>
      </span>
    </button>
  );
}

function MiniQuiz({ quiz }: { quiz: Summary["quiz"] }) {
  const [picked, setPicked] = useState<Record<number, number>>({});
  const score = Object.entries(picked).filter(([i, v]) => quiz[+i].answer_index === v).length;
  return (
    <div className="space-y-4">
      {quiz.map((q, i) => (
        <div key={i} className="rounded-2xl border border-line p-4">
          <p className="font-bold">{i + 1}. {q.question}</p>
          <div className="mt-2 grid gap-2">
            {q.options.map((o, k) => {
              const chosen = picked[i] === k, done = picked[i] !== undefined;
              return <button key={k} disabled={done} onClick={() => setPicked((p) => ({ ...p, [i]: k }))} className={cn("rounded-xl border px-3 py-2 text-left text-sm transition", !done && "border-line hover:border-brand-400", done && k === q.answer_index && "border-emerald-500 bg-emerald-50 font-bold", done && chosen && k !== q.answer_index && "border-rose-400 bg-rose-50", done && !chosen && k !== q.answer_index && "opacity-60")}>{o}</button>;
            })}
          </div>
          {picked[i] !== undefined && q.explanation ? <p className="cv-rise mt-2 text-sm text-ink-600"><b>{picked[i] === q.answer_index ? "Correct. " : "Not quite. "}</b>{q.explanation}</p> : null}
        </div>))}
      {Object.keys(picked).length === quiz.length ? <p className="text-center text-lg font-extrabold text-forest-900">You scored {score}/{quiz.length}</p> : null}
    </div>
  );
}

function Notes({ s, url }: { s: Summary; url: string }) {
  const [filter, setFilter] = useState("");
  const concepts = s.concepts ?? [], terms = s.terminology ?? [], apps = s.applications ?? [];
  const shownTerms = useMemo(() => terms.filter((t) => !filter || `${t.term} ${t.definition}`.toLowerCase().includes(filter.toLowerCase())).sort((a, b) => a.term.localeCompare(b.term)), [terms, filter]);
  const nav = [
    concepts.length ? ["concepts", "Concepts"] : null, terms.length ? ["terms", "Terminology"] : null, apps.length ? ["apps", "Applications"] : null,
    ["chapters", "Chapters"], s.takeaways.length || s.examples.length ? ["takeaways", "Takeaways"] : null, s.flashcards.length || s.quiz.length ? ["practice", "Practice"] : null,
  ].filter(Boolean) as [string, string][];
  return (
    <div className="space-y-8">
      <div className="rounded-2xl bg-gradient-to-br from-sage-50 to-white p-5 ring-1 ring-line">
        <p className="text-[11px] font-extrabold uppercase tracking-[0.18em] text-brand-700">At a glance</p>
        <p className="mt-2 text-[16px] leading-7 text-ink-800">{s.overview}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {s.level ? <Badge tone="brand" className="capitalize">{s.level}</Badge> : null}
          {(s.topics ?? []).map((t) => <span key={t} className="rounded-full bg-white px-3 py-1 text-xs font-bold text-forest-800 ring-1 ring-line">{t}</span>)}
        </div>
        {s.prerequisites?.length ? <p className="mt-3 text-sm text-ink-600"><b className="text-forest-800">Before you watch:</b> {s.prerequisites.join(" · ")}</p> : null}
        {s.tools_mentioned?.length ? <p className="mt-2 flex flex-wrap items-center gap-1.5 text-sm text-ink-600"><Wrench size={14} className="text-ink-400" /><b className="text-forest-800">Tools mentioned:</b> {s.tools_mentioned.join(", ")}</p> : null}
      </div>

      <nav aria-label="Summary sections" className="sticky top-12 z-10 -mx-1 flex gap-1.5 overflow-x-auto rounded-xl bg-white/90 px-1 py-2 backdrop-blur [scrollbar-width:none]">
        {nav.map(([id, label]) => <a key={id} href={`#${id}`} onClick={(e) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" }); }} className="shrink-0 rounded-full border border-line-strong px-3.5 py-1.5 text-xs font-bold text-ink-600 transition hover:border-brand-400 hover:text-brand-700">{label}</a>)}
      </nav>

      {concepts.length ? (
        <Section id="concepts" icon={<Layers size={18} />} title="Concepts to learn" hint={`${concepts.length} core ideas, in the order they matter`}>
          <ol className="grid gap-3 md:grid-cols-2">
            {concepts.map((c, i) => (
              <li key={i} className="cv-rise rounded-2xl border border-line bg-white p-4 shadow-sm" style={{ animationDelay: `${i * 40}ms` }}>
                <div className="flex items-start gap-3"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-forest-800 text-xs font-extrabold text-white">{i + 1}</span>
                  <div className="min-w-0 flex-1"><h5 className="font-extrabold leading-snug text-forest-900">{c.name}</h5>
                    <p className="mt-1 text-sm leading-6 text-ink-700">{c.explanation}</p>
                    {c.why_it_matters ? <p className="mt-2 rounded-lg bg-amber-50 px-3 py-1.5 text-xs text-amber-900"><b>Why it matters:</b> {c.why_it_matters}</p> : null}
                    {c.timestamp_seconds != null ? <a href={`${url}&t=${Math.floor(c.timestamp_seconds)}s`} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 font-mono text-[11px] font-bold text-brand-700 underline">Watch this part {ts(c.timestamp_seconds)}</a> : null}</div></div>
              </li>))}
          </ol>
        </Section>
      ) : null}

      {terms.length ? (
        <Section id="terms" icon={<BookOpen size={18} />} title="Terminology used" hint={`${terms.length} terms explained in plain language`}>
          <div className="relative max-w-xs"><Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-300" /><input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter terms" aria-label="Filter terminology" className="input-base h-9 pl-8 text-sm" /></div>
          <dl className="overflow-hidden rounded-2xl border border-line bg-white">
            {shownTerms.map((t, i) => <div key={t.term} className={cn("grid gap-1 px-4 py-3 sm:grid-cols-[220px_1fr] sm:gap-4", i > 0 && "border-t border-line")}><dt className="font-extrabold text-forest-900">{t.term}</dt><dd className="text-sm leading-6 text-ink-700">{t.definition}</dd></div>)}
            {!shownTerms.length ? <p className="p-4 text-sm text-ink-500">No term matches “{filter}”.</p> : null}
          </dl>
        </Section>
      ) : null}

      {apps.length ? (
        <Section id="apps" icon={<Briefcase size={18} />} title="Where it is applied" hint="Uses and real-world settings the video mentions">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{apps.map((a, i) => <div key={i} className="rounded-2xl border border-line bg-white p-4"><h5 className="font-extrabold text-forest-900">{a.area}</h5><p className="mt-1 text-sm leading-6 text-ink-700">{a.description}</p></div>)}</div>
        </Section>
      ) : null}

      <Section id="chapters" icon={<ListChecks size={18} />} title="Chapter notes" hint="Jump to any part of the video">
        <ol className="relative space-y-3 border-l-2 border-sage-300 pl-5">
          {s.chapters.map((c, i) => (
            <li key={i} className="relative">
              <span className="absolute -left-[27px] top-1.5 h-3 w-3 rounded-full border-2 border-white bg-brand-500" aria-hidden />
              <div className="rounded-2xl border border-line bg-white p-4">
                <div className="flex flex-wrap items-center gap-3"><a href={`${url}&t=${Math.floor(c.start_seconds)}s`} target="_blank" rel="noreferrer" className="rounded-lg bg-forest-800 px-2.5 py-1 font-mono text-xs font-bold text-white hover:bg-forest-700">{ts(c.start_seconds)}</a><h5 className="font-extrabold">{c.title}</h5></div>
                <p className="mt-2 text-sm leading-6 text-ink-700">{c.summary}</p>
                {c.key_points.length ? <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-ink-600">{c.key_points.map((k, n) => <li key={n}>{k}</li>)}</ul> : null}
              </div>
            </li>))}
        </ol>
      </Section>

      {s.takeaways.length || s.examples.length ? (
        <Section id="takeaways" icon={<ListChecks size={18} />} title="Takeaways and examples">
          <div className="grid gap-4 md:grid-cols-2">
            {s.takeaways.length ? <div className="rounded-2xl bg-emerald-50 p-4"><h5 className="text-sm font-extrabold text-emerald-800">Key takeaways</h5><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-700">{s.takeaways.map((x, i) => <li key={i}>{x}</li>)}</ul></div> : null}
            {s.examples.length ? <div className="rounded-2xl bg-sky-50 p-4"><h5 className="text-sm font-extrabold text-sky-800">Examples from the video</h5><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-700">{s.examples.map((x, i) => <li key={i}>{x}</li>)}</ul></div> : null}
          </div>
        </Section>
      ) : null}

      {s.flashcards.length || s.quiz.length ? (
        <Section id="practice" icon={<Play size={18} />} title="Practice">
          {s.flashcards.length ? <><p className="text-xs font-bold text-ink-500">Flashcards (tap to flip)</p><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{s.flashcards.map((f, i) => <Flashcard key={i} f={f} />)}</div></> : null}
          {s.quiz.length ? <><p className="pt-2 text-xs font-bold text-ink-500">Check your understanding</p><MiniQuiz quiz={s.quiz} /></> : null}
        </Section>
      ) : null}
    </div>
  );
}

export default function YouTube() {
  const [url, setUrl] = useState("");
  const [cur, setCur] = useState<Video | null>(null);
  const [reason, setReason] = useState<string | null>(null);
  const [paste, setPaste] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const hist = useLoad(() => lh.videos(), []);

  async function run(fn: () => Promise<Video>) {
    setBusy(true); setError(null);
    try { const v = await fn(); setCur(v); setReason(v.needs_transcript ? v.reason ?? "Captions are not available for this video." : null); if (v.summary) setPaste(""); hist.reload(); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  const go = (withTranscript?: string) => run(() => (cur && withTranscript ? lh.summariseVideo(cur.id, withTranscript) : lh.importVideo(url.trim(), withTranscript)));
  const s = cur?.summary;
  const oldFormat = !!s && !s.concepts?.length && !s.terminology?.length;

  return (
    <div className="space-y-5">
      <Card className="space-y-4 p-6">
        <div><h2 className="text-xl font-extrabold text-forest-900">Turn any video into study notes</h2><p className="text-sm text-ink-500">Paste a YouTube link. We fetch the title and captions (when the uploader allows it) and Gemini organises what the speaker said into concepts to learn, terminology, applications, chapters, flashcards and a quiz.</p></div>
        <div className="flex flex-wrap gap-2">
          <div className="relative min-w-[260px] flex-1"><Link2 size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-300" /><input value={url} onChange={(e) => setUrl(e.target.value)} onKeyDown={(e) => e.key === "Enter" && url.trim() && go()} placeholder="https://www.youtube.com/watch?v=…" className="input-base h-12 pl-10" aria-label="YouTube link" /></div>
          <Button size="lg" loading={busy && !cur} disabled={!url.trim()} onClick={() => go()} icon={<Play size={16} />}>Summarise</Button>
        </div>
        {error ? <ErrorState message={error} onRetry={() => go()} /> : null}
      </Card>

      {busy ? <Card className="grid place-items-center gap-3 p-14 text-center"><Loader2 className="animate-spin text-brand-600" size={30} /><p className="font-extrabold text-forest-900">Reading the transcript and organising your notes…</p><p className="text-xs text-ink-400">Usually 20–60 seconds for longer videos.</p></Card> : null}

      {cur && !busy ? (
        <Card className="space-y-6 p-6 sm:p-8">
          <header className="flex flex-wrap gap-4">
            {cur.thumbnail ? <img src={cur.thumbnail} alt="" className="h-24 w-40 rounded-xl object-cover" /> : null}
            <div className="min-w-0 flex-1"><h3 className="text-xl font-extrabold text-forest-900">{cur.title ?? "Untitled video"}</h3><p className="text-sm text-ink-500">{cur.channel}</p>
              <div className="mt-2 flex flex-wrap items-center gap-2"><Badge tone={cur.transcript_status === "unavailable" ? "warn" : "brand"}>{cur.transcript_status === "pasted" ? "Pasted transcript" : cur.transcript_status === "available" ? "Captions found" : "No captions"}</Badge><a href={cur.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs font-bold text-brand-700 underline">Open on YouTube <ExternalLink size={12} /></a>
                {s ? <Button size="sm" variant="outline" icon={<BookmarkPlus size={14} />} onClick={() => setSaveOpen(true)}>Save to notebook</Button> : null}
                {s && cur.segments ? <Button size="sm" variant="ghost" icon={<RefreshCw size={14} />} onClick={() => run(() => lh.resummarise(cur.id))}>Regenerate</Button> : null}</div></div>
          </header>

          {!s ? (
            <div className="space-y-3">
              <InlineNote tone="warn"><b>{reason ?? "No transcript yet."}</b> Not every video has accessible captions. Paste the transcript yourself (copy it from the YouTube “Show transcript” panel) and we will summarise that instead.</InlineNote>
              <textarea value={paste} onChange={(e) => setPaste(e.target.value)} rows={8} placeholder={"Paste the transcript here. Lines may start with timestamps like 00:45 or [01:02:03]."} className="input-base font-mono text-[13px]" aria-label="Transcript" />
              <Button loading={busy} disabled={paste.trim().length < 80} onClick={() => go(paste)} icon={<ClipboardPaste size={15} />}>Summarise pasted transcript</Button>
            </div>
          ) : (
            <>
              {oldFormat && cur.segments ? <InlineNote tone="brand">This summary was made in the older, shorter format. <button className="font-extrabold underline" onClick={() => run(() => lh.resummarise(cur.id))}>Regenerate it</button> to get concepts to learn, terminology and applications.</InlineNote> : null}
              <Notes s={s} url={cur.url} />
            </>
          )}
          <SaveToNotebook open={saveOpen} onClose={() => setSaveOpen(false)} kind="video" id={cur.id} />
        </Card>
      ) : null}

      <Card className="space-y-3 p-5">
        <h3 className="font-extrabold text-forest-900">Your imported videos</h3>
        {hist.loading && !hist.data ? <Skeleton className="h-20" /> : !hist.data?.items.length ? <EmptyState title="No videos yet" description="Summaries you create appear here." /> : (
          <ul className="grid gap-2 sm:grid-cols-2">{hist.data.items.map((v) => <li key={v.id}><button onClick={() => { setCur(v); setReason(v.summary ? null : "Captions were not available for this video."); setError(null); }} className="flex w-full items-center gap-3 rounded-xl border border-line p-2.5 text-left transition hover:border-brand-300">{v.thumbnail ? <img src={v.thumbnail} alt="" className="h-12 w-20 rounded-lg object-cover" /> : <span className="h-12 w-20 rounded-lg bg-sage-100" />}<span className="min-w-0 flex-1"><span className="line-clamp-2 text-sm font-bold">{v.title ?? v.video_id}</span><span className="text-[11px] text-ink-400">{v.summary ? "Summarised" : "Needs transcript"}</span></span></button></li>)}</ul>)}
      </Card>
    </div>
  );
}
