/** The open notebook: index, numbered pages, chapters, bookmarks, tags, history, autosave, focus mode. */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Bookmark, BookmarkCheck, ChevronLeft, ChevronRight, Eye, FileUp, History, Keyboard, Loader2, Lock, Maximize2, Minimize2, Menu, Plus, Search, Settings2, Trash2, X } from "lucide-react";
import { Button, EmptyState, ErrorState, Modal } from "../ui";
import { Markdown, Skeleton } from "./shared";
import { ApiError } from "../../lib/api";
import { lh, type NbIndex, type Page } from "../../lib/learning";
import { useToast } from "../../lib/auth";
import { cn } from "../../lib/utils";
import { COVER } from "./Covers";

type Draft = { title: string; content: string; tags: string[]; chapter_id: number | null; bookmarked: boolean };
type SaveState = "saved" | "dirty" | "saving" | "error";

export function Diary({ id, token, onBack, onLocked, onSettings }: { id: number; token?: string; onBack: () => void; onLocked: () => void; onSettings: () => void }) {
  const { push } = useToast();
  const [idx, setIdx] = useState<NbIndex | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState<Page | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [save, setSave] = useState<SaveState>("saved");
  const [focus, setFocus] = useState(false);
  const [preview, setPreview] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [help, setHelp] = useState(false);
  const [history, setHistory] = useState<Awaited<ReturnType<typeof lh.history>>["items"] | null>(null);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<{ page_no: number; title: string; snippet: string }[] | null>(null);
  const [tagInput, setTagInput] = useState("");
  const [onlyBookmarks, setOnlyBookmarks] = useState(false);
  const [chapterName, setChapterName] = useState("");
  const [renaming, setRenaming] = useState<{ id: number; title: string } | null>(null);
  const [flipKey, setFlipKey] = useState(0);
  const fileRef = useRef<HTMLInputElement>(null);
  const draftRef = useRef<Draft | null>(null);
  const pageRef = useRef<Page | null>(null);
  const timer = useRef<number | undefined>(undefined);
  draftRef.current = draft; pageRef.current = page;

  const fail = useCallback((e: unknown) => { if (e instanceof ApiError && e.status === 423) { onLocked(); return; } push({ title: "Something went wrong", description: (e as Error).message, variant: "error" }); }, [onLocked, push]);

  const loadIndex = useCallback(async () => { try { setIdx(await lh.nbIndex(id, token)); setError(null); } catch (e) { if (e instanceof ApiError && e.status === 423) onLocked(); else setError((e as Error).message); } }, [id, token, onLocked]);
  useEffect(() => { loadIndex(); }, [loadIndex]);

  const flush = useCallback(async (): Promise<boolean> => {
    window.clearTimeout(timer.current);
    const p = pageRef.current, d = draftRef.current;
    if (!p || !d) return true;
    const same = d.title === p.title && d.content === p.content && d.bookmarked === p.bookmarked && d.chapter_id === p.chapter_id && JSON.stringify(d.tags) === JSON.stringify(p.tags);
    if (same) { setSave("saved"); return true; }
    setSave("saving");
    try { const saved = await lh.savePage(id, p.page_no, { title: d.title, content: d.content, tags: d.tags, chapter_id: d.chapter_id, bookmarked: d.bookmarked }, token); setPage(saved); pageRef.current = saved; setSave("saved"); setIdx((cur) => cur && { ...cur, pages: cur.pages.map((x) => (x.page_no === saved.page_no ? { ...x, title: saved.title, bookmarked: saved.bookmarked, tags: saved.tags, chapter_id: saved.chapter_id } : x)) }); return true; }
    catch (e) { setSave("error"); fail(e); return false; }
  }, [id, token, fail]);

  const open = useCallback(async (no: number) => {
    if (!(await flush())) return;
    try { const p = await lh.page(id, no, token); setPage(p); setDraft({ title: p.title, content: p.content, tags: p.tags, chapter_id: p.chapter_id, bookmarked: p.bookmarked }); setSave("saved"); setFlipKey((k) => k + 1); setPreview(false); setDrawer(false); } catch (e) { fail(e); }
  }, [flush, id, token, fail]);

  useEffect(() => { if (idx && !page && idx.pages.length) open(idx.pages[0].page_no); }, [idx, page, open]);

  // autosave: 1.2s after the last keystroke
  const edit = (patch: Partial<Draft>) => { setDraft((d) => d && { ...d, ...patch }); setSave("dirty"); window.clearTimeout(timer.current); timer.current = window.setTimeout(() => { flush(); }, 1200); };
  useEffect(() => () => window.clearTimeout(timer.current), []);
  useEffect(() => { const h = (e: BeforeUnloadEvent) => { if (save === "dirty" || save === "saving") e.preventDefault(); }; window.addEventListener("beforeunload", h); return () => window.removeEventListener("beforeunload", h); }, [save]);

  const total = idx?.pages.length ?? 0;
  const no = page?.page_no ?? 1;
  const addPage = useCallback(async (chapter?: number | null) => { if (!(await flush())) return; try { const p = await lh.addPage(id, { title: "Untitled page", content: "", chapter_id: chapter ?? draftRef.current?.chapter_id ?? null }, token); await loadIndex(); setPage(p); setDraft({ title: p.title, content: p.content, tags: p.tags, chapter_id: p.chapter_id, bookmarked: false }); setFlipKey((k) => k + 1); setSave("saved"); } catch (e) { fail(e); } }, [flush, id, token, loadIndex, fail]);

  // keyboard shortcuts
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === "s") { e.preventDefault(); flush().then((ok) => ok && push({ title: "Saved", variant: "success" })); }
      else if (e.altKey && e.key === "ArrowRight" && no < total) { e.preventDefault(); open(no + 1); }
      else if (e.altKey && e.key === "ArrowLeft" && no > 1) { e.preventDefault(); open(no - 1); }
      else if (mod && e.shiftKey && e.key.toLowerCase() === "f") { e.preventDefault(); setFocus((f) => !f); }
      else if (mod && e.shiftKey && e.key.toLowerCase() === "b") { e.preventDefault(); draftRef.current && edit({ bookmarked: !draftRef.current.bookmarked }); }
      else if (mod && e.altKey && e.key.toLowerCase() === "n") { e.preventDefault(); addPage(); }
      else if (e.key === "Escape" && focus) setFocus(false);
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [no, total, focus, flush, open, addPage]);

  // in-notebook search
  useEffect(() => { if (q.trim().length < 2) { setHits(null); return; } const t = setTimeout(() => lh.search(id, q.trim(), token).then((r) => setHits(r.items)).catch(fail), 250); return () => clearTimeout(t); }, [q, id, token, fail]);

  async function remove() {
    if (!page || !confirm(`Delete page ${page.page_no} "${page.title}"? This cannot be undone.`)) return;
    try { await lh.deletePage(id, page.page_no, token); setPage(null); setDraft(null); await loadIndex(); } catch (e) { fail(e); }
  }
  async function showHistory() { if (!(await flush()) || !page) return; try { setHistory((await lh.history(id, page.page_no, token)).items); } catch (e) { fail(e); } }
  async function restore(v: number) { if (!page) return; try { const p = await lh.restore(id, page.page_no, v, token); setPage(p); setDraft({ title: p.title, content: p.content, tags: p.tags, chapter_id: p.chapter_id, bookmarked: p.bookmarked }); setHistory(null); push({ title: "Version restored", variant: "success" }); } catch (e) { fail(e); } }
  async function upload(f: File) { try { const r = await lh.upload(id, f, token); push({ title: `Imported ${r.pages.length} page${r.pages.length > 1 ? "s" : ""}`, description: f.name, variant: "success" }); await loadIndex(); open(r.pages[0].page_no); } catch (e) { fail(e); } }
  async function addChapter() { if (!chapterName.trim()) return; try { await lh.addChapter(id, chapterName.trim(), token); setChapterName(""); loadIndex(); } catch (e) { fail(e); } }
  async function rename() { if (!renaming) return; try { await lh.renameChapter(id, renaming.id, renaming.title, token); setRenaming(null); loadIndex(); } catch (e) { fail(e); } }

  const cover = COVER[idx?.notebook.cover_style ?? "forest"] ?? COVER.forest;
  const grouped = useMemo(() => {
    if (!idx) return [];
    const pages = idx.pages.filter((p) => !onlyBookmarks || p.bookmarked);
    const groups = idx.chapters.map((c) => ({ chapter: c as { id: number; title: string } | null, pages: pages.filter((p) => p.chapter_id === c.id) }));
    const loose = pages.filter((p) => !p.chapter_id || !idx.chapters.some((c) => c.id === p.chapter_id));
    return loose.length ? [{ chapter: null, pages: loose }, ...groups] : groups;
  }, [idx, onlyBookmarks]);

  if (error) return <ErrorState message={error} onRetry={loadIndex} />;
  if (!idx) return <div className="grid gap-4 lg:grid-cols-[320px_1fr]"><Skeleton className="h-[560px]" /><Skeleton className="h-[560px]" /></div>;

  const indexPanel = (
    <aside className="flex h-full flex-col gap-3 rounded-2xl p-4 text-[#2B2118]" style={{ background: "linear-gradient(160deg,#F6EEDB,#EADFC4)" }} aria-label="Notebook index">
      <div className="flex items-center gap-2"><span className="h-8 w-1.5 rounded-full" style={{ background: cover.from }} /><div className="min-w-0 flex-1"><p className="truncate font-suits text-lg font-bold leading-tight">{idx.notebook.title}</p><p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#8A7550]">Contents · {total} pages</p></div>{idx.notebook.locked ? <Lock size={15} className="text-[#8A7550]" aria-label="Locked notebook" /> : null}</div>
      <div className="relative"><Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8A7550]" /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search this notebook" aria-label="Search this notebook" className="h-9 w-full rounded-lg border border-[#D8C9A5] bg-white/70 pl-8 pr-3 text-sm outline-none focus:border-[#B07A2B]" /></div>
      {hits ? (
        <div className="min-h-0 flex-1 overflow-y-auto"><p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-[#8A7550]">{hits.length} result{hits.length === 1 ? "" : "s"}</p>{hits.map((h) => <button key={h.page_no} onClick={() => open(h.page_no)} className="mb-1 block w-full rounded-lg bg-white/60 p-2 text-left hover:bg-white"><span className="text-sm font-bold">p.{h.page_no} {h.title}</span><span className="block truncate text-xs text-[#6B5B3F]">…{h.snippet}…</span></button>)}{!hits.length ? <p className="text-sm text-[#6B5B3F]">No matches.</p> : null}</div>
      ) : (
        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
          {grouped.map((g) => (
            <section key={g.chapter?.id ?? "loose"}>
              <div className="group flex items-center gap-1"><h4 className="flex-1 truncate font-suits text-[15px] font-bold italic text-[#5B3B24]">{g.chapter?.title ?? "Loose pages"}</h4>
                {g.chapter ? <><button aria-label={`Rename chapter ${g.chapter.title}`} onClick={() => setRenaming({ id: g.chapter!.id, title: g.chapter!.title })} className="rounded p-1 text-[#8A7550] opacity-0 hover:bg-white/60 group-hover:opacity-100 focus:opacity-100"><Settings2 size={12} /></button><button aria-label={`Add page to ${g.chapter.title}`} onClick={() => addPage(g.chapter!.id)} className="rounded p-1 text-[#8A7550] opacity-0 hover:bg-white/60 group-hover:opacity-100 focus:opacity-100"><Plus size={13} /></button></> : null}</div>
              <ul>{g.pages.map((p) => (
                <li key={p.id}><button onClick={() => open(p.page_no)} aria-current={p.page_no === no ? "page" : undefined} className={cn("flex w-full items-baseline gap-1 rounded-md px-1.5 py-1 text-left text-sm transition", p.page_no === no ? "bg-white font-bold shadow-sm" : "hover:bg-white/50")}>
                  {p.bookmarked ? <BookmarkCheck size={12} className="shrink-0 self-center text-[#B5543A]" /> : null}<span className="truncate">{p.title}</span><span className="mx-1 min-w-3 flex-1 translate-y-[-3px] border-b border-dotted border-[#B8A97F]" /><span className="font-mono text-xs text-[#8A7550]">{p.page_no}</span></button></li>))}
                {!g.pages.length ? <li className="px-1.5 text-xs italic text-[#8A7550]">{onlyBookmarks ? "No bookmarks" : "Empty chapter"}</li> : null}</ul>
            </section>))}
        </div>
      )}
      <div className="space-y-2 border-t border-[#D8C9A5] pt-3">
        <div className="flex gap-1.5"><input value={chapterName} onChange={(e) => setChapterName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addChapter()} placeholder="New chapter" aria-label="New chapter name" className="h-8 min-w-0 flex-1 rounded-lg border border-[#D8C9A5] bg-white/70 px-2 text-sm outline-none" /><button onClick={addChapter} disabled={!chapterName.trim()} className="rounded-lg bg-[#5B3B24] px-2.5 text-xs font-bold text-white disabled:opacity-40">Add</button></div>
        <div className="flex gap-1.5"><button onClick={() => addPage()} className="flex-1 rounded-lg bg-[#1B5740] px-3 py-2 text-xs font-extrabold text-white hover:bg-[#124433]"><Plus size={13} className="mr-1 inline" />New page</button><button onClick={() => fileRef.current?.click()} aria-label="Import PDF, DOCX or TXT" title="Import PDF, DOCX or TXT" className="rounded-lg border border-[#D8C9A5] bg-white/70 px-2.5 text-[#5B3B24] hover:bg-white"><FileUp size={15} /></button>
          <button onClick={() => setOnlyBookmarks((b) => !b)} aria-pressed={onlyBookmarks} aria-label="Show only bookmarks" title="Bookmarks only" className={cn("rounded-lg border px-2.5", onlyBookmarks ? "border-[#B5543A] bg-[#B5543A] text-white" : "border-[#D8C9A5] bg-white/70 text-[#5B3B24] hover:bg-white")}><Bookmark size={15} /></button></div>
        <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.currentTarget.value = ""; }} />
      </div>
    </aside>
  );

  return (
    <div className={cn(focus ? "fixed inset-0 z-[60] overflow-y-auto bg-[#0E1117] p-4 sm:p-10" : "space-y-3")}>
      <div className={cn("flex flex-wrap items-center gap-2", focus && "mx-auto max-w-3xl")}>
        {!focus ? <Button size="sm" variant="outline" onClick={async () => { if (await flush()) onBack(); }} icon={<ArrowLeft size={14} />}>Shelf</Button> : null}
        <Button size="sm" variant="ghost" className="lg:hidden" onClick={() => setDrawer(true)} icon={<Menu size={15} />}>Index</Button>
        <span className="flex-1" />
        <span className={cn("inline-flex items-center gap-1.5 text-xs font-bold", focus ? "text-white/60" : "text-ink-500")} role="status" aria-live="polite">{save === "saving" ? <><Loader2 size={12} className="animate-spin" />Saving…</> : save === "dirty" ? "Unsaved changes" : save === "error" ? <span className="text-rose-500">Not saved. Retrying on next edit</span> : <>Saved</>}</span>
        <Button size="sm" variant={focus ? "secondary" : "outline"} onClick={() => setPreview((p) => !p)} icon={<Eye size={14} />}>{preview ? "Edit" : "Preview"}</Button>
        <Button size="sm" variant={focus ? "secondary" : "outline"} onClick={() => setFocus((f) => !f)} icon={focus ? <Minimize2 size={14} /> : <Maximize2 size={14} />}>{focus ? "Exit focus" : "Focus"}</Button>
        {!focus ? <><Button size="sm" variant="ghost" onClick={() => setHelp(true)} icon={<Keyboard size={14} />} aria-label="Keyboard shortcuts" /><Button size="sm" variant="ghost" onClick={onSettings} icon={<Settings2 size={14} />} aria-label="Notebook settings" /></> : null}
      </div>

      <div className={cn("grid gap-3", !focus && "lg:grid-cols-[330px_1fr]", focus && "mx-auto mt-4 max-w-3xl")}>
        {!focus ? <div className="hidden lg:block lg:h-[680px]">{indexPanel}</div> : null}
        <section className="relative" aria-label="Page">
          {!page || !draft ? <Skeleton className="h-[680px]" /> : (
            <div key={flipKey} className={cn("nb-flip relative flex min-h-[680px] flex-col overflow-hidden rounded-2xl shadow-[0_24px_50px_-24px_rgba(0,0,0,.5)]", focus ? "nb-paper-dark text-white" : "nb-paper text-[#2B2118]")}>
              <span className="absolute inset-y-0 left-0 w-9 bg-gradient-to-r from-black/10 to-transparent" aria-hidden /><span className="absolute inset-y-0 left-9 w-px bg-rose-300/50" aria-hidden />
              <div className="flex items-center gap-2 px-6 pb-1 pt-4 pl-14">
                <span className="font-suits text-sm italic" style={{ color: focus ? "#E6C878" : "#8A7550" }}>Page {page.page_no} of {total}</span><span className="flex-1" />
                {page.source_type !== "manual" ? <span className="rounded-full bg-black/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide">{page.source_type}</span> : null}
                <button onClick={() => edit({ bookmarked: !draft.bookmarked })} aria-pressed={draft.bookmarked} aria-label={draft.bookmarked ? "Remove bookmark" : "Bookmark this page"} className="rounded-lg p-1.5 transition hover:bg-black/10">{draft.bookmarked ? <BookmarkCheck size={18} className="text-[#B5543A]" /> : <Bookmark size={18} className="opacity-60" />}</button>
                {!focus ? <><button onClick={showHistory} aria-label="Page history" className="rounded-lg p-1.5 opacity-70 transition hover:bg-black/10"><History size={17} /></button><button onClick={remove} aria-label="Delete page" className="rounded-lg p-1.5 opacity-70 transition hover:bg-rose-500/15 hover:text-rose-600"><Trash2 size={17} /></button></> : null}
              </div>
              <input value={draft.title} onChange={(e) => edit({ title: e.target.value })} maxLength={200} aria-label="Page title" placeholder="Untitled page" className="bg-transparent px-6 pb-2 pl-14 font-suits text-3xl font-bold outline-none placeholder:opacity-40" />
              {!focus ? (
                <div className="flex flex-wrap items-center gap-2 px-6 pb-2 pl-14">
                  <select value={draft.chapter_id ?? ""} onChange={(e) => edit({ chapter_id: e.target.value ? Number(e.target.value) : null })} aria-label="Chapter" className="rounded-lg border border-black/10 bg-white/60 px-2 py-1 text-xs font-semibold"><option value="">No chapter</option>{idx.chapters.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}</select>
                  {draft.tags.map((t) => <button key={t} onClick={() => edit({ tags: draft.tags.filter((x) => x !== t) })} aria-label={`Remove tag ${t}`} className="inline-flex items-center gap-1 rounded-full bg-[#1B5740]/10 px-2.5 py-1 text-xs font-bold text-[#1B5740] hover:bg-rose-100 hover:text-rose-700">#{t}<X size={10} /></button>)}
                  <input value={tagInput} onChange={(e) => setTagInput(e.target.value)} onKeyDown={(e) => { if ((e.key === "Enter" || e.key === ",") && tagInput.trim()) { e.preventDefault(); const t = tagInput.trim().toLowerCase().replace(/^#/, ""); if (!draft.tags.includes(t) && draft.tags.length < 15) edit({ tags: [...draft.tags, t] }); setTagInput(""); } }} placeholder="+ tag" aria-label="Add a tag" className="w-20 rounded-full border border-dashed border-black/20 bg-transparent px-2.5 py-1 text-xs outline-none focus:border-[#1B5740]" />
                </div>
              ) : null}
              {preview ? <div className="min-h-[440px] flex-1 px-6 pb-6 pl-14 pt-2"><Markdown text={draft.content || "*Nothing written yet.*"} className={focus ? "!text-white/90" : "!text-[#2B2118]"} /></div> : (
                <textarea value={draft.content} onChange={(e) => edit({ content: e.target.value })} aria-label="Page content" placeholder="Start writing… Markdown works: # heading, - list, **bold**, ```code```" spellCheck className="min-h-[440px] flex-1 resize-none bg-transparent px-6 pb-6 pl-14 pt-2 font-[inherit] text-[16px] leading-8 outline-none placeholder:opacity-40" autoFocus={focus} />)}
              <footer className="flex items-center justify-between gap-2 border-t border-black/10 px-4 py-2.5 pl-14">
                <button onClick={() => open(no - 1)} disabled={no <= 1} aria-label="Previous page" className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm font-bold transition hover:bg-black/10 disabled:opacity-30"><ChevronLeft size={16} />Prev</button>
                <label className="flex items-center gap-1.5 text-xs font-bold opacity-80">Go to page<input type="number" min={1} max={total} defaultValue={no} key={no} onKeyDown={(e) => { if (e.key === "Enter") { const n = Math.min(total, Math.max(1, Number(e.currentTarget.value))); open(n); } }} aria-label="Jump to page number" className="h-8 w-14 rounded-lg border border-black/15 bg-white/70 px-2 text-center font-mono text-sm text-[#2B2118]" /></label>
                <button onClick={() => (no >= total ? addPage() : open(no + 1))} aria-label={no >= total ? "Add a new page" : "Next page"} className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm font-bold transition hover:bg-black/10">{no >= total ? <>New page<Plus size={16} /></> : <>Next<ChevronRight size={16} /></>}</button>
              </footer>
            </div>)}
        </section>
      </div>

      {drawer ? <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal aria-label="Notebook index"><button className="absolute inset-0 bg-black/50" aria-label="Close index" onClick={() => setDrawer(false)} /><div className="absolute inset-y-0 left-0 w-[88%] max-w-sm p-2">{indexPanel}</div></div> : null}
      <Modal open={!!history} onClose={() => setHistory(null)} title="Page history" description="Earlier versions of this page. Restoring keeps the current text in history too." size="lg">
        {!history?.length ? <EmptyState title="No earlier versions yet" description="Versions are saved as you edit." /> : <ul className="max-h-96 space-y-2 overflow-y-auto">{history.map((v) => <li key={v.id} className="rounded-xl border border-line p-3"><div className="flex items-center justify-between gap-2"><p className="truncate font-bold">{v.title}</p><span className="text-xs text-ink-400">{new Date(v.saved_at).toLocaleString()}</span><Button size="sm" variant="outline" onClick={() => restore(v.id)}>Restore</Button></div><p className="mt-1 line-clamp-3 whitespace-pre-wrap text-xs text-ink-500">{v.content || "(empty)"}</p></li>)}</ul>}
      </Modal>
      <Modal open={help} onClose={() => setHelp(false)} title="Keyboard shortcuts" size="md">
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">{([["Ctrl/⌘ + S", "Save now"], ["Alt + ← / →", "Previous / next page"], ["Ctrl/⌘ + Shift + F", "Distraction-free mode"], ["Ctrl/⌘ + Shift + B", "Bookmark page"], ["Ctrl/⌘ + Alt + N", "New page"], ["Esc", "Leave focus mode"]] as const).map(([k, v]) => <div key={k} className="contents"><dt><kbd className="rounded border border-line bg-sage-50 px-2 py-0.5 font-mono text-xs">{k}</kbd></dt><dd>{v}</dd></div>)}</dl>
        <p className="mt-3 text-xs text-ink-400">Your writing autosaves 1.2 seconds after you stop typing.</p>
      </Modal>
      <Modal open={!!renaming} onClose={() => setRenaming(null)} title="Rename chapter" size="md" footer={<><Button variant="ghost" onClick={() => setRenaming(null)}>Cancel</Button><Button onClick={rename} disabled={!renaming?.title.trim()}>Rename</Button></>}>
        <input value={renaming?.title ?? ""} onChange={(e) => renaming && setRenaming({ ...renaming, title: e.target.value })} onKeyDown={(e) => e.key === "Enter" && rename()} className="input-base" aria-label="Chapter name" maxLength={160} autoFocus />
      </Modal>
    </div>
  );
}
