/** Learning Materials: notes written on demand by Gemini, saved for later. */
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { BookmarkPlus, ClipboardCheck, Code2, GraduationCap, Layers, Lightbulb, Loader2, MessageCircleQuestion, Network, RefreshCw, Search, Send, Sparkles, Trash2, Wand2 } from "lucide-react";
import { Badge, Button, Card, EmptyState, ErrorState, InlineNote } from "../../components/ui";
import { Diagram } from "../../components/learning/Diagram";
import { SaveToNotebook } from "../../components/learning/SaveToNotebook";
import { Markdown, Skeleton, useLoad } from "../../components/learning/shared";
import { lh, type Material } from "../../lib/learning";
import { useToast } from "../../lib/auth";
import { cn } from "../../lib/utils";

const LEVELS = ["beginner", "intermediate", "advanced"] as const;
const DEPTHS = [["brief", "Brief"], ["standard", "Standard"], ["deep", "In-depth"]] as const;
const ACTIONS = [
  { a: "simplify", label: "Explain simply", icon: <Lightbulb size={15} /> },
  { a: "deeper", label: "Go deeper", icon: <GraduationCap size={15} /> },
  { a: "examples", label: "Give examples", icon: <Layers size={15} /> },
  { a: "implementation", label: "Show practical implementation", icon: <Code2 size={15} /> },
  { a: "diagram", label: "Generate diagram", icon: <Network size={15} /> },
] as const;

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="cv-rise"><h3 className="mb-2 text-sm font-extrabold uppercase tracking-wide text-brand-700">{title}</h3>{children}</section>;
}
const Bullets = ({ items }: { items: string[] }) => <ul className="list-disc space-y-1.5 pl-5 text-[15px] leading-7 text-ink-700">{items.map((i, n) => <li key={n}>{i}</li>)}</ul>;

export default function Materials() {
  const nav = useNavigate();
  const { push } = useToast();
  const [params] = useSearchParams();
  const [topic, setTopic] = useState(params.get("topic") ?? "");
  const [level, setLevel] = useState<(typeof LEVELS)[number]>("beginner");
  const [depth, setDepth] = useState<(typeof DEPTHS)[number][0]>("standard");
  const [search, setSearch] = useState("");
  const [cur, setCur] = useState<Material | null>(null);
  const [diagram, setDiagram] = useState<Material | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ask, setAsk] = useState("");
  const [saveOpen, setSaveOpen] = useState(false);
  const saved = useLoad(() => lh.materials(search), [search]);

  useEffect(() => { if (params.get("topic")) setTopic(params.get("topic")!); }, [params]);

  async function run<T>(label: string, fn: () => Promise<T>, then: (r: T) => void) {
    setBusy(label); setError(null);
    try { then(await fn()); saved.reload(); } catch (e) { setError((e as Error).message); } finally { setBusy(null); }
  }
  const generate = (force = false) => run("generate", () => lh.createMaterial({ topic: topic.trim(), level, depth, force }), (m) => { setCur(m); setDiagram(null); });
  const open = (id: number) => run("open", () => lh.material(id), (m) => { setCur(m); setDiagram(null); setTopic(m.topic); setLevel(m.level as typeof level); });
  const act = (a: string) => cur && run(a, () => lh.materialAction(cur.id, a), (m) => { if (m.kind === "diagram") setDiagram(m); else { setCur(m); setDiagram(null); } });
  const send = () => cur && ask.trim().length >= 3 && run("ask", () => lh.ask(cur.id, ask.trim()), (r) => { setCur({ ...cur, followups: [...cur.followups, r] }); setAsk(""); });
  async function remove(id: number) { try { await lh.deleteMaterial(id); if (cur?.id === id) setCur(null); saved.reload(); } catch (e) { push({ title: "Could not delete", description: (e as Error).message, variant: "error" }); } }

  const c = cur?.content;
  return (
    <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
      <aside className="space-y-4">
        <Card className="space-y-4 p-5">
          <h3 className="flex items-center gap-2 font-extrabold text-forest-900"><Wand2 size={16} className="text-brand-600" />Ask for notes on anything</h3>
          <input value={topic} onChange={(e) => setTopic(e.target.value)} onKeyDown={(e) => e.key === "Enter" && topic.trim().length >= 2 && generate()} placeholder="e.g. SQL window functions, DCF valuation…" className="input-base" aria-label="Topic" maxLength={200} />
          <div><p className="mb-1.5 text-xs font-bold text-ink-500">Level</p><div className="flex gap-1.5">{LEVELS.map((l) => <button key={l} aria-pressed={level === l} onClick={() => setLevel(l)} className={cn("flex-1 rounded-lg border px-2 py-1.5 text-xs font-extrabold capitalize", level === l ? "border-forest-800 bg-forest-800 text-white" : "border-line-strong bg-white text-ink-600")}>{l}</button>)}</div></div>
          <div><p className="mb-1.5 text-xs font-bold text-ink-500">Depth</p><div className="flex gap-1.5">{DEPTHS.map(([k, l]) => <button key={k} aria-pressed={depth === k} onClick={() => setDepth(k)} className={cn("flex-1 rounded-lg border px-2 py-1.5 text-xs font-extrabold", depth === k ? "border-brand-600 bg-brand-600 text-white" : "border-line-strong bg-white text-ink-600")}>{l}</button>)}</div></div>
          <Button fullWidth loading={busy === "generate"} disabled={topic.trim().length < 2} onClick={() => generate()} icon={<Sparkles size={16} />}>Generate notes</Button>
          <p className="text-[11px] text-ink-400">Written by Gemini on request and saved. The same request reopens instantly without regenerating.</p>
        </Card>
        <Card className="space-y-3 p-5">
          <div className="relative"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-300" /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search saved materials" className="input-base pl-9" aria-label="Search saved materials" /></div>
          {saved.loading && !saved.data ? <Skeleton className="h-24" /> : !saved.data?.items.length ? <p className="text-sm text-ink-500">Nothing saved yet.</p> : (
            <ul className="max-h-[420px] space-y-1 overflow-y-auto">
              {saved.data.items.filter((m) => m.kind === "notes").map((m) => (
                <li key={m.id} className={cn("group flex items-center gap-2 rounded-xl border p-2.5 transition", cur?.id === m.id ? "border-brand-500 bg-brand-50" : "border-transparent hover:bg-sage-50")}>
                  <button onClick={() => open(m.id)} className="min-w-0 flex-1 text-left"><p className="truncate text-sm font-bold">{m.topic}</p><p className="text-[11px] capitalize text-ink-400">{m.level} · {m.depth}</p></button>
                  <button aria-label={`Delete ${m.topic}`} onClick={() => remove(m.id)} className="rounded-lg p-1.5 text-ink-300 opacity-0 transition hover:bg-rose-50 hover:text-rose-600 group-hover:opacity-100 focus:opacity-100"><Trash2 size={14} /></button>
                </li>))}
            </ul>)}
        </Card>
      </aside>

      <main className="min-w-0 space-y-4" aria-live="polite">
        {error ? <ErrorState message={error} onRetry={() => (cur ? undefined : generate())} /> : null}
        {busy && busy !== "ask" ? (
          <Card className="grid place-items-center gap-3 p-16 text-center"><Loader2 className="animate-spin text-brand-600" size={32} /><p className="font-extrabold text-forest-900">{busy === "diagram" ? "Drawing your diagram…" : "Gemini is writing your notes…"}</p><p className="text-xs text-ink-400">Usually 10–40 seconds.</p></Card>
        ) : !cur ? (
          <EmptyState icon={<Sparkles size={22} />} title="Your AI study workspace" description="Type any topic, choose a level and depth, and get structured notes with examples, code, common mistakes, interview relevance, practice problems and a revision summary." />
        ) : c ? (
          <>
            <Card className="space-y-5 p-6 sm:p-8">
              <header className="space-y-2">
                <div className="flex flex-wrap items-center gap-2"><Badge tone="brand" className="capitalize">{cur.level}</Badge><Badge className="capitalize">{cur.depth}</Badge></div>
                <h2 className="font-display text-3xl font-extrabold text-forest-900">{c.title}</h2>
                <p className="max-w-3xl text-[16px] leading-7 text-ink-600">{c.summary}</p>
              </header>
              <div className="flex flex-wrap gap-2 border-y border-line py-3">
                {ACTIONS.map((x) => <Button key={x.a} size="sm" variant="outline" icon={x.icon} loading={busy === x.a} onClick={() => act(x.a)}>{x.label}</Button>)}
                <Button size="sm" variant="outline" icon={<ClipboardCheck size={15} />} onClick={() => nav(`/app/learning/quizzes?topic=${encodeURIComponent(cur.topic)}`)}>Create quiz from this topic</Button>
                <Button size="sm" variant="outline" icon={<BookmarkPlus size={15} />} onClick={() => setSaveOpen(true)}>Save to notebook</Button>
                <Button size="sm" variant="ghost" icon={<RefreshCw size={15} />} loading={busy === "regenerate"} onClick={() => act("regenerate")}>Regenerate</Button>
              </div>
              {c.definitions?.length ? <Block title="Definitions">{c.definitions.map((d, i) => <p key={i} className="mb-2 text-[15px] leading-7"><b>{d.heading}.</b> {d.body}</p>)}</Block> : null}
              <Block title="Explanation (beginner to advanced)">{c.explanation.map((s, i) => <div key={i} className="mb-4"><h4 className="font-bold text-forest-900">{s.heading}</h4><Markdown text={s.body} /></div>)}</Block>
              {c.examples?.length ? <Block title="Examples">{c.examples.map((s, i) => <div key={i} className="mb-3 rounded-xl bg-sage-50 p-4"><h4 className="font-bold">{s.heading}</h4><Markdown text={s.body} /></div>)}</Block> : null}
              {c.code_snippets?.length ? <Block title="Code">{c.code_snippets.map((s, i) => <div key={i} className="mb-4"><p className="mb-1 font-bold">{s.title}</p><Markdown text={"```" + s.language + "\n" + s.code + "\n```"} />{s.explanation ? <p className="text-sm text-ink-600">{s.explanation}</p> : null}</div>)}</Block> : null}
              {c.formulas?.length ? <Block title="Formulas">{c.formulas.map((f, i) => <p key={i} className="mb-2 rounded-lg bg-amber-50 px-4 py-2 font-mono text-sm"><b className="font-sans">{f.heading}: </b>{f.body}</p>)}</Block> : null}
              <div className="grid gap-6 md:grid-cols-2">
                {c.real_world_applications?.length ? <Block title="Real-world applications"><Bullets items={c.real_world_applications} /></Block> : null}
                {c.common_mistakes?.length ? <Block title="Common mistakes"><Bullets items={c.common_mistakes} /></Block> : null}
                {c.interview_relevance?.length ? <Block title="Interview relevance"><Bullets items={c.interview_relevance} /></Block> : null}
                {c.key_takeaways?.length ? <Block title="Key takeaways"><Bullets items={c.key_takeaways} /></Block> : null}
              </div>
              {c.practice_problems?.length ? <Block title="Practice problems">{c.practice_problems.map((p, i) => <details key={i} className="mb-2 rounded-xl border border-line p-3"><summary className="cursor-pointer font-bold">{i + 1}. {p.question}</summary>{p.hint ? <p className="mt-2 text-sm text-ink-500"><b>Hint:</b> {p.hint}</p> : null}{p.answer ? <div className="mt-2 text-sm"><b>Answer:</b> <Markdown text={p.answer} className="inline" /></div> : null}</details>)}</Block> : null}
              {c.revision_summary ? <InlineNote tone="brand"><b>Revision summary.</b> {c.revision_summary}</InlineNote> : null}
              {c.sources?.length ? <p className="text-xs text-ink-400"><b>Reference works named by the model (verify before relying on them):</b> {c.sources.join("; ")}</p> : <p className="text-xs text-ink-400">AI-generated. Check important facts against an authoritative source.</p>}
            </Card>

            {diagram?.content.nodes ? <Card className="space-y-3 p-6 cv-rise"><h3 className="font-extrabold text-forest-900">{diagram.content.title}</h3>{diagram.content.description ? <p className="text-sm text-ink-600">{diagram.content.description}</p> : null}<Diagram nodes={diagram.content.nodes} edges={diagram.content.edges ?? []} title={diagram.content.title} /></Card> : null}

            <Card className="space-y-4 p-6">
              <h3 className="flex items-center gap-2 font-extrabold text-forest-900"><MessageCircleQuestion size={17} className="text-brand-600" />Ask Gemini about this topic</h3>
              {cur.followups.map((f, i) => <div key={i} className="space-y-2"><p className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2 text-sm font-medium text-white">{f.question}</p><div className="max-w-[92%] rounded-2xl rounded-bl-sm bg-sage-50 px-4 py-3"><Markdown text={f.answer} /></div></div>)}
              {busy === "ask" ? <p className="flex items-center gap-2 text-sm text-ink-500"><Loader2 size={15} className="animate-spin" />Thinking…</p> : null}
              <div className="flex gap-2"><input value={ask} onChange={(e) => setAsk(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Ask a follow-up question…" className="input-base" aria-label="Follow-up question" maxLength={800} /><Button onClick={send} disabled={ask.trim().length < 3 || busy === "ask"} icon={<Send size={15} />}>Ask</Button></div>
            </Card>
            <SaveToNotebook open={saveOpen} onClose={() => setSaveOpen(false)} kind="material" id={cur.id} />
          </>
        ) : null}
      </main>
    </div>
  );
}
