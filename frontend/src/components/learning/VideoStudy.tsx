/** Watch the video inside the page and take notes beside it. Notes autosave on this device and can be saved to a notebook. */
import { Link } from "react-router-dom";
import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import { BookmarkPlus, CheckCircle2, Clock3, Copy, ExternalLink, FastForward, Lock, Pause, Play, Rewind } from "lucide-react";
import { Button, EmptyState, Modal } from "../ui";
import { lh, type NotebookCard, type Video } from "../../lib/learning";
import { useToast } from "../../lib/auth";
import { useLoad } from "./shared";
import { cn } from "../../lib/utils";

export type PlayerApi = { seek: (seconds: number) => void; time: () => number };

declare global {
  interface Window { YT?: any; onYouTubeIframeAPIReady?: () => void }
}

let apiPromise: Promise<any> | null = null;
function loadYouTubeApi(): Promise<any> {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  if (apiPromise) return apiPromise;
  apiPromise = new Promise((resolve, reject) => {
    const prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => { prev?.(); resolve(window.YT); };
    const s = document.createElement("script");
    s.src = "https://www.youtube.com/iframe_api";
    s.async = true;
    s.onerror = () => { apiPromise = null; reject(new Error("The YouTube player could not be loaded.")); };
    document.head.appendChild(s);
  });
  return apiPromise;
}

const clock = (s: number) => {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = Math.floor(s % 60);
  return `${h ? `${h}:${String(m).padStart(2, "0")}` : m}:${String(x).padStart(2, "0")}`;
};
const draftKey = (videoId: string) => `arjuna.vnotes.${videoId}`;

/** Turn [12:34] markers into links that open the video at that moment, for the saved notebook page. */
function withLinks(notes: string, url: string): string {
  return notes.replace(/\[((?:\d{1,2}:)?\d{1,2}:\d{2})\]/g, (_m, t: string) => {
    const parts = t.split(":").map(Number);
    const sec = parts.length === 3 ? parts[0] * 3600 + parts[1] * 60 + parts[2] : parts[0] * 60 + parts[1];
    return `[${t}](${url}${url.includes("?") ? "&" : "?"}t=${sec}s)`;
  });
}

function SaveNotes({ open, onClose, video, notes }: { open: boolean; onClose: () => void; video: Video; notes: string }) {
  const { push } = useToast();
  const list = useLoad(() => (open ? lh.notebooks() : Promise.resolve(null)), [open]);
  const [pick, setPick] = useState<NotebookCard | null>(null);
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const items = list.data?.items ?? [];

  async function save() {
    if (!pick) return;
    setBusy(true); setErr(null);
    try {
      const token = pick.locked ? (await lh.unlock(pick.id, pw)).token ?? undefined : undefined;
      const content = `# My notes: ${video.title ?? "Video"}\n\nVideo: ${video.url}\n\n${withLinks(notes.trim(), video.url)}\n`;
      const page = await lh.addPage(pick.id, { title: `Notes: ${(video.title ?? "Video").slice(0, 150)}`, content, tags: ["video notes"] }, token);
      push({ title: "Notes saved", description: `${pick.title}, page ${page.page_no}`, variant: "success" });
      setPw(""); setPick(null); onClose();
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  return (
    <Modal open={open} onClose={onClose} title="Save a copy to another notebook" description="They become a new page. Timestamps like [12:34] turn into links back to that moment." size="md"
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={busy} onClick={save} disabled={!pick || (pick.locked && !pw)}>Save as new page</Button></>}>
      {!items.length && !list.loading ? <EmptyState title="No notebooks yet" description="Create one in My Notes first." /> : (
        <div className="space-y-2">
          {items.map((n) => (
            <button key={n.id} onClick={() => { setPick(n); setErr(null); }} className={cn("flex w-full items-center gap-3 rounded-xl border p-3 text-left transition", pick?.id === n.id ? "border-brand-500 bg-brand-50" : "border-line hover:border-brand-300")}>
              <span className="flex-1 font-bold">{n.title}</span>{n.locked ? <Lock size={14} className="text-ink-400" /> : null}<span className="text-xs text-ink-500">{n.pages} pages</span>
            </button>))}
          {pick?.locked ? <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} placeholder={`Password for "${pick.title}"`} className="input-base" autoFocus aria-label="Notebook password" /> : null}
          {err ? <p className="text-sm font-semibold text-rose-600" role="alert">{err}</p> : null}
        </div>)}
    </Modal>
  );
}

const VideoStudy = forwardRef<PlayerApi, { video: Video }>(function VideoStudy({ video }, ref) {
  const { push } = useToast();
  const host = useRef<HTMLDivElement>(null);
  const player = useRef<any>(null);
  const area = useRef<HTMLTextAreaElement>(null);
  const [ready, setReady] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const [notes, setNotes] = useState("");
  const [saved, setSaved] = useState<"idle" | "saved">("idle");
  const [sync, setSync] = useState<{ state: "idle" | "saving" | "saved" | "error"; page?: number }>({ state: "idle" });
  const lastSent = useRef<string>("");

  const time = useCallback(() => Number(player.current?.getCurrentTime?.() ?? 0), []);
  const seek = useCallback((s: number) => { player.current?.seekTo?.(s, true); player.current?.playVideo?.(); }, []);
  useImperativeHandle(ref, () => ({ seek, time }), [seek, time]);

  // restore a saved draft for this video
  useEffect(() => {
    lastSent.current = "";
    setSync({ state: "idle" });
    try { setNotes(localStorage.getItem(draftKey(video.video_id)) ?? ""); } catch { setNotes(""); }
  }, [video.video_id]);

  // every change is also filed in My Notes (YouTube Notes notebook): one page per video, updated as you type
  useEffect(() => {
    if (!notes.trim() || notes === lastSent.current) return;
    const t = setTimeout(async () => {
      const sending = notes;
      setSync((x) => ({ ...x, state: "saving" }));
      try {
        const r = await lh.saveVideoNotes(video.id, sending);
        lastSent.current = sending;
        setSync({ state: r.saved ? "saved" : "idle", page: r.page_no });
      } catch { setSync((x) => ({ ...x, state: "error" })); }
    }, 1500);
    return () => clearTimeout(t);
  }, [notes, video.id]);
  useEffect(() => {
    const t = setTimeout(() => { try { if (notes) localStorage.setItem(draftKey(video.video_id), notes); else localStorage.removeItem(draftKey(video.video_id)); setSaved("saved"); } catch { /* storage blocked: notes still work */ } }, 600);
    return () => clearTimeout(t);
  }, [notes, video.video_id]);

  // the embedded player
  useEffect(() => {
    let dead = false;
    setReady(false); setFailed(null); setPlaying(false);
    loadYouTubeApi().then((YT) => {
      if (dead || !host.current) return;
      const el = document.createElement("div");
      host.current.innerHTML = "";
      host.current.appendChild(el);
      player.current = new YT.Player(el, {
        videoId: video.video_id, width: "100%", height: "100%",
        playerVars: { rel: 0, modestbranding: 1, playsinline: 1 },
        events: {
          onReady: () => !dead && setReady(true),
          onStateChange: (e: any) => !dead && setPlaying(e.data === 1),
          onError: (e: any) => !dead && setFailed(e.data === 101 || e.data === 150 ? "The uploader does not allow this video to be played outside YouTube." : "This video cannot be played here."),
        },
      });
    }).catch((e) => !dead && setFailed((e as Error).message));
    return () => { dead = true; try { player.current?.destroy?.(); } catch { /* already gone */ } player.current = null; };
  }, [video.video_id]);

  function stamp() {
    const t = `[${clock(time())}] `;
    const ta = area.current;
    if (!ta) { setNotes((n) => n + (n && !n.endsWith("\n") ? "\n" : "") + t); return; }
    const a = ta.selectionStart ?? notes.length, b = ta.selectionEnd ?? a;
    const atLineStart = a === 0 || notes[a - 1] === "\n";
    const ins = (atLineStart ? "" : "\n") + t;
    setNotes(notes.slice(0, a) + ins + notes.slice(b));
    requestAnimationFrame(() => { ta.focus(); const p = a + ins.length; ta.setSelectionRange(p, p); });
  }
  const jump = (d: number) => seek(Math.max(0, time() + d));
  async function copy() { try { await navigator.clipboard.writeText(notes); push({ title: "Notes copied", variant: "success" }); } catch { push({ title: "Could not copy", variant: "error" }); } }

  return (
    <section id="watch" aria-label="Watch and take notes" className="grid gap-5 scroll-mt-24 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
      <div className="space-y-3">
        <div className="relative aspect-video overflow-hidden rounded-2xl bg-black shadow-md">
          <div ref={host} className="absolute inset-0 [&>iframe]:h-full [&>iframe]:w-full" />
          {failed ? (
            <div className="absolute inset-0 grid place-items-center bg-forest-900/95 p-6 text-center text-white">
              <div><p className="font-bold">{failed}</p>
                <a href={video.url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-sm font-bold text-forest-900">Open on YouTube <ExternalLink size={14} /></a></div>
            </div>
          ) : !ready ? <div className="absolute inset-0 grid place-items-center text-sm font-semibold text-white/70">Loading player…</div> : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="outline" disabled={!ready} onClick={() => jump(-10)} icon={<Rewind size={14} />}>10s</Button>
          <Button size="sm" variant="outline" disabled={!ready} onClick={() => (playing ? player.current?.pauseVideo?.() : player.current?.playVideo?.())} icon={playing ? <Pause size={14} /> : <Play size={14} />}>{playing ? "Pause" : "Play"}</Button>
          <Button size="sm" variant="outline" disabled={!ready} onClick={() => jump(10)} icon={<FastForward size={14} />}>10s</Button>
          <span className="text-xs text-ink-500">Click any timestamp in the notes below to jump here.</span>
        </div>
      </div>

      <div className="flex flex-col gap-2 lg:sticky lg:top-4 lg:self-start">
        <div className="flex items-center justify-between gap-2">
          <h4 className="text-base font-extrabold text-forest-900">My notes</h4>
          <span className="text-[11px] font-semibold text-ink-400">{!notes ? "Nothing yet" : sync.state === "saved" ? "" : sync.state === "error" ? "Not synced yet, kept on this device" : saved === "saved" ? "Saving to My Notes…" : "Typing…"}</span>
        </div>
        <textarea ref={area} value={notes} onChange={(e) => { setNotes(e.target.value); setSaved("idle"); }}
          onKeyDown={(e) => { if (e.altKey && e.key.toLowerCase() === "t") { e.preventDefault(); stamp(); } }}
          rows={12} aria-label="My notes" placeholder={"Type while you watch.\nPress the timestamp button (or Alt+T) to mark the moment you are at."}
          className="input-base min-h-[260px] resize-y text-[15px] leading-7" />
        {sync.state === "saved" ? (
          <p className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700"><CheckCircle2 size={14} />Saved in My Notes: YouTube Notes{sync.page ? `, page ${sync.page}` : ""} · <Link to="/app/learning/notes" className="underline">Open My Notes</Link></p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" disabled={!ready} onClick={stamp} icon={<Clock3 size={14} />}>Add timestamp</Button>
          <Button size="sm" disabled={!notes.trim()} onClick={() => setSaveOpen(true)} icon={<BookmarkPlus size={14} />}>Also save elsewhere</Button>
          <Button size="sm" variant="ghost" disabled={!notes.trim()} onClick={copy} icon={<Copy size={14} />}>Copy</Button>
        </div>
      </div>
      <SaveNotes open={saveOpen} onClose={() => setSaveOpen(false)} video={video} notes={notes} />
    </section>
  );
});

export default VideoStudy;
