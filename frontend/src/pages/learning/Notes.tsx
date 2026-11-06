/** My Notes: a bookshelf of private notebooks. Locked notebooks are protected by the server. */
import { useState } from "react";
import { Eye, EyeOff, Lock, LockOpen, Search, ShieldCheck, Trash2 } from "lucide-react";
import { Button, EmptyState, ErrorState, Modal } from "../../components/ui";
import { CoverFace, COVER, NewBook, ShelfBook } from "../../components/learning/Covers";
import { Diary } from "../../components/learning/Diary";
import { Skeleton, useLoad } from "../../components/learning/shared";
import { lh, type NotebookCard } from "../../lib/learning";
import { useToast } from "../../lib/auth";
import { cn } from "../../lib/utils";

const COVER_KEYS = Object.keys(COVER);

function PasswordField({ value, onChange, label, autoFocus, onEnter }: { value: string; onChange: (v: string) => void; label: string; autoFocus?: boolean; onEnter?: () => void }) {
  const [show, setShow] = useState(false);
  return (
    <label className="block text-sm font-bold">{label}
      <span className="relative mt-1.5 block"><input type={show ? "text" : "password"} value={value} onChange={(e) => onChange(e.target.value)} onKeyDown={(e) => e.key === "Enter" && onEnter?.()} autoFocus={autoFocus} autoComplete="off" className="input-base pr-10" /><button type="button" onClick={() => setShow((s) => !s)} aria-label={show ? "Hide password" : "Show password"} className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-1 text-ink-400 hover:text-ink-700">{show ? <EyeOff size={15} /> : <Eye size={15} />}</button></span>
    </label>
  );
}

function CoverPicker({ value, onChange, title }: { value: string; onChange: (k: string) => void; title: string }) {
  return <div role="radiogroup" aria-label="Cover style" className="grid grid-cols-4 gap-2">{COVER_KEYS.map((k) => <button key={k} role="radio" aria-checked={value === k} aria-label={k} onClick={() => onChange(k)} className={cn("aspect-[3/4] overflow-hidden rounded-lg border-2 transition", value === k ? "scale-105 border-brand-500 shadow-lg" : "border-transparent opacity-80 hover:opacity-100")}><CoverFace style={k} title={title || "Notebook"} small /></button>)}</div>;
}

export default function Notes() {
  const { push } = useToast();
  const shelf = useLoad(() => lh.notebooks(), []);
  const [open, setOpen] = useState<{ nb: NotebookCard; token?: string } | null>(null);
  const [opening, setOpening] = useState<number | null>(null);
  const [unlock, setUnlock] = useState<NotebookCard | null>(null);
  const [create, setCreate] = useState(false);
  const [settings, setSettings] = useState(false);
  const [folder, setFolder] = useState("all");
  const [q, setQ] = useState("");

  function enter(nb: NotebookCard, token?: string) {
    setOpening(nb.id);
    setTimeout(() => { setOpen({ nb, token }); setOpening(null); setUnlock(null); }, 850); // let the cover swing open
  }
  function pick(nb: NotebookCard) { nb.locked ? setUnlock(nb) : enter(nb); }

  if (open) {
    return (
      <>
        <Diary key={open.nb.id} id={open.nb.id} token={open.token} onBack={() => { setOpen(null); shelf.reload(); }} onLocked={() => { const nb = open.nb; setOpen(null); setUnlock({ ...nb, locked: true }); push({ title: "Notebook locked", description: "Your unlock expired. Enter the password again.", variant: "info" }); }} onSettings={() => setSettings(true)} />
        <SettingsModal open={settings} nb={open.nb} token={open.token} onClose={() => setSettings(false)} onChanged={(nb, token) => { setOpen({ nb, token: token ?? open.token }); shelf.reload(); }} onDeleted={() => { setSettings(false); setOpen(null); shelf.reload(); }} />
      </>
    );
  }

  const items = (shelf.data?.items ?? []).filter((n) => (folder === "all" || (n.folder ?? "") === (folder === "none" ? "" : folder)) && (!q.trim() || n.title.toLowerCase().includes(q.toLowerCase()) || n.tags.some((t) => t.includes(q.toLowerCase()))));
  const folders = [...new Set((shelf.data?.items ?? []).map((n) => n.folder).filter(Boolean))] as string[];
  const rows: NotebookCard[][] = [];
  const perRow = 4;
  for (let i = 0; i < items.length + 1; i += perRow) rows.push(items.slice(i, i + perRow));

  return (
    <div className="space-y-5">
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-b from-[#3A2616] via-[#2A1B10] to-[#1B120A] p-5 shadow-xl sm:p-8" style={{ boxShadow: "inset 0 0 120px rgba(0,0,0,.45)" }}>
        <div className="mb-6 flex flex-wrap items-end gap-3">
          <div className="flex-1"><p className="text-[11px] font-extrabold uppercase tracking-[0.3em] text-[#E6C878]">Your study diary</p><h2 className="font-suits text-3xl font-bold !text-white">The Library</h2><p className="mt-1 max-w-xl text-sm text-white/60">One notebook per subject, goal or course. Save AI notes and video summaries straight in, or write your own.</p></div>
          <div className="relative"><Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Find a notebook" aria-label="Find a notebook" className="h-10 w-48 rounded-xl border border-white/15 bg-white/10 pl-9 pr-3 text-sm text-white outline-none placeholder:text-white/40 focus:border-[#E6C878]" /></div>
        </div>
        {folders.length ? <div className="mb-6 flex flex-wrap gap-1.5" role="tablist" aria-label="Folders">{["all", ...folders].map((f) => <button key={f} role="tab" aria-selected={folder === f} onClick={() => setFolder(f)} className={cn("rounded-full border px-3.5 py-1 text-xs font-bold capitalize transition", folder === f ? "border-[#E6C878] bg-[#E6C878] text-[#2A1B10]" : "border-white/20 text-white/70 hover:border-white/50")}>{f === "all" ? "All notebooks" : f}</button>)}</div> : null}
        {shelf.loading && !shelf.data ? <div className="flex gap-6">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-60 w-40 !bg-white/10" />)}</div> : shelf.error ? <ErrorState message={shelf.error} onRetry={shelf.reload} /> : (
          <div className="space-y-10">
            {rows.map((row, ri) => (
              <div key={ri}>
                <div className="flex flex-wrap items-end gap-6 px-2 sm:gap-8">
                  {row.map((nb) => <ShelfBook key={nb.id} nb={nb} onOpen={() => pick(nb)} opening={opening === nb.id} />)}
                  {ri === rows.length - 1 && row.length < perRow + 1 && (row.length < perRow || items.length % perRow === 0) ? <NewBook onClick={() => setCreate(true)} /> : null}
                </div>
                <div className="nb-shelf -mt-1 h-4 rounded-b-md" aria-hidden />
              </div>))}
            {!items.length && (shelf.data?.items.length ?? 0) > 0 ? <p className="text-center text-sm text-white/60">No notebook matches your search.</p> : null}
          </div>)}
        {shelf.data && !shelf.data.items.length ? <p className="mt-6 text-center text-sm text-white/60">Your shelf is empty. Create a notebook to begin.</p> : null}
      </div>
      <div className="flex items-start gap-2 rounded-xl border border-line bg-white p-3 text-xs text-ink-500"><ShieldCheck size={15} className="mt-0.5 shrink-0 text-brand-600" /><p><b className="text-ink-700">About notebook locks.</b> A locked notebook is protected by the server: its pages, index and search are refused until the password is verified, and the unlock expires after 30 minutes. This is access control, not end-to-end encryption, so there is no password recovery. If you forget it, the notebook cannot be reopened.</p></div>

      <CreateModal open={create} covers={shelf.data?.covers ?? COVER_KEYS} onClose={() => setCreate(false)} onCreated={(nb) => { setCreate(false); shelf.reload(); push({ title: "Notebook created", description: nb.title, variant: "success" }); }} />
      <UnlockModal nb={unlock} onClose={() => setUnlock(null)} onUnlocked={(nb, token) => enter(nb, token)} />
    </div>
  );
}

function CreateModal({ open, onClose, onCreated }: { open: boolean; covers: string[]; onClose: () => void; onCreated: (nb: NotebookCard) => void }) {
  const [title, setTitle] = useState(""); const [cover, setCover] = useState("forest"); const [desc, setDesc] = useState(""); const [folder, setFolder] = useState(""); const [tags, setTags] = useState("");
  const [lock, setLock] = useState(false); const [pw, setPw] = useState(""); const [pw2, setPw2] = useState(""); const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null);
  const bad = !title.trim() || (lock && (pw.length < 6 || pw !== pw2));
  async function go() {
    setBusy(true); setErr(null);
    try { const nb = await lh.createNotebook({ title: title.trim(), cover_style: cover, description: desc || null, folder: folder.trim() || null, tags: tags.split(",").map((t) => t.trim().toLowerCase()).filter(Boolean), password: lock ? pw : null }); setTitle(""); setDesc(""); setFolder(""); setTags(""); setLock(false); setPw(""); setPw2(""); onCreated(nb); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  return (
    <Modal open={open} onClose={onClose} title="New notebook" description="Choose a cover and give it a purpose." size="lg" footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={busy} disabled={bad} onClick={go}>Create notebook</Button></>}>
      <div className="grid gap-5 sm:grid-cols-[170px_1fr]">
        <div className="mx-auto w-[150px]"><div className="aspect-[3/4] rounded-r-xl shadow-[8px_12px_20px_-8px_rgba(0,0,0,.5)]"><CoverFace style={cover} title={title || "Untitled"} locked={lock} /></div></div>
        <div className="space-y-3">
          <label className="block text-sm font-bold">Title<input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={160} autoFocus className="input-base mt-1.5" placeholder="e.g. SQL Mastery, Interview Prep" /></label>
          <CoverPicker value={cover} onChange={setCover} title={title} />
          <div className="grid grid-cols-2 gap-3"><label className="block text-sm font-bold">Folder<input value={folder} onChange={(e) => setFolder(e.target.value)} maxLength={80} className="input-base mt-1.5" placeholder="Optional" /></label><label className="block text-sm font-bold">Tags<input value={tags} onChange={(e) => setTags(e.target.value)} className="input-base mt-1.5" placeholder="sql, backend" /></label></div>
          <label className="block text-sm font-bold">Description<input value={desc} onChange={(e) => setDesc(e.target.value)} maxLength={300} className="input-base mt-1.5" placeholder="Optional" /></label>
          <label className="flex cursor-pointer items-center gap-2 text-sm font-bold"><input type="checkbox" checked={lock} onChange={(e) => setLock(e.target.checked)} className="accent-brand-600" /><Lock size={14} />Protect with a password</label>
          {lock ? <div className="space-y-2 rounded-xl bg-amber-50 p-3"><PasswordField label="Password (min 6 characters)" value={pw} onChange={setPw} /><PasswordField label="Confirm password" value={pw2} onChange={setPw2} />{pw2 && pw !== pw2 ? <p className="text-xs font-semibold text-rose-600">Passwords do not match.</p> : null}<p className="text-[11px] text-amber-800">There is no recovery. If you forget this password the notebook cannot be reopened.</p></div> : null}
          {err ? <p className="text-sm font-semibold text-rose-600" role="alert">{err}</p> : null}
        </div>
      </div>
    </Modal>
  );
}

function UnlockModal({ nb, onClose, onUnlocked }: { nb: NotebookCard | null; onClose: () => void; onUnlocked: (nb: NotebookCard, token: string) => void }) {
  const [pw, setPw] = useState(""); const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null); const [shake, setShake] = useState(0); const [ok, setOk] = useState(false);
  async function go() {
    if (!nb || !pw) return;
    setBusy(true); setErr(null);
    try { const r = await lh.unlock(nb.id, pw); if (!r.token) throw new Error("This notebook is not locked."); setOk(true); setTimeout(() => { setPw(""); setOk(false); onUnlocked(nb, r.token!); }, 650); }
    catch (e) { setErr((e as Error).message); setShake((s) => s + 1); } finally { setBusy(false); }
  }
  return (
    <Modal open={!!nb} onClose={() => { setPw(""); setErr(null); onClose(); }} title={nb ? `“${nb.title}” is locked` : ""} description="Enter the notebook password. It is checked by the server." size="md" footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={busy} disabled={!pw || ok} onClick={go} icon={<LockOpen size={15} />}>Unlock</Button></>}>
      <div key={shake} className={cn("space-y-4", shake > 0 && err && "nb-shake")}>
        <div className="grid place-items-center"><span className={cn("grid h-20 w-20 place-items-center rounded-full border-4 transition-all duration-500", ok ? "nb-unlocked border-[#E6C878] bg-[#E6C878]/20 text-[#B07A2B]" : "border-ink-200 bg-sage-50 text-ink-500")}>{ok ? <LockOpen size={34} /> : <Lock size={34} />}</span></div>
        <PasswordField label="Password" value={pw} onChange={setPw} autoFocus onEnter={go} />
        {err ? <p className="text-center text-sm font-semibold text-rose-600" role="alert">{err}</p> : null}
      </div>
    </Modal>
  );
}

function SettingsModal({ open, nb, token, onClose, onChanged, onDeleted }: { open: boolean; nb: NotebookCard; token?: string; onClose: () => void; onChanged: (nb: NotebookCard, token?: string) => void; onDeleted: () => void }) {
  const { push } = useToast();
  const [title, setTitle] = useState(nb.title); const [cover, setCover] = useState(nb.cover_style); const [folder, setFolder] = useState(nb.folder ?? ""); const [tags, setTags] = useState(nb.tags.join(", ")); const [desc, setDesc] = useState(nb.description ?? "");
  const [cur, setCur] = useState(""); const [npw, setNpw] = useState(""); const [busy, setBusy] = useState(false);
  async function save() {
    setBusy(true);
    try { const r = await lh.patchNotebook(nb.id, { title, cover_style: cover, folder: folder || null, description: desc || null, tags: tags.split(",").map((t) => t.trim().toLowerCase()).filter(Boolean) }, token); onChanged({ ...nb, ...r }); push({ title: "Notebook updated", variant: "success" }); onClose(); }
    catch (e) { push({ title: "Could not save", description: (e as Error).message, variant: "error" }); } finally { setBusy(false); }
  }
  async function lock(setNew: boolean) {
    setBusy(true);
    try { const r = await lh.setLock(nb.id, { new_password: setNew ? npw : null, current_password: nb.locked ? cur : null }); let t = token; if (setNew && r.locked) t = (await lh.unlock(nb.id, npw)).token ?? undefined; onChanged({ ...nb, ...r }, r.locked ? t : undefined); setCur(""); setNpw(""); push({ title: setNew ? (nb.locked ? "Password changed" : "Notebook locked") : "Lock removed", variant: "success" }); }
    catch (e) { push({ title: "Could not change the lock", description: (e as Error).message, variant: "error" }); } finally { setBusy(false); }
  }
  async function del() { if (!confirm(`Delete "${nb.title}" and every page in it? This cannot be undone.`)) return; try { await lh.deleteNotebook(nb.id, token); push({ title: "Notebook deleted", variant: "success" }); onDeleted(); } catch (e) { push({ title: "Could not delete", description: (e as Error).message, variant: "error" }); } }
  return (
    <Modal open={open} onClose={onClose} title="Notebook settings" size="lg" footer={<><Button variant="danger" onClick={del} icon={<Trash2 size={14} />}>Delete notebook</Button><span className="flex-1" /><Button variant="ghost" onClick={onClose}>Close</Button><Button loading={busy} onClick={save} disabled={!title.trim()}>Save changes</Button></>}>
      <div className="space-y-4">
        <label className="block text-sm font-bold">Title<input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={160} className="input-base mt-1.5" /></label>
        <CoverPicker value={cover} onChange={setCover} title={title} />
        <div className="grid grid-cols-2 gap-3"><label className="block text-sm font-bold">Folder<input value={folder} onChange={(e) => setFolder(e.target.value)} className="input-base mt-1.5" /></label><label className="block text-sm font-bold">Tags<input value={tags} onChange={(e) => setTags(e.target.value)} className="input-base mt-1.5" /></label></div>
        <label className="block text-sm font-bold">Description<input value={desc} onChange={(e) => setDesc(e.target.value)} maxLength={300} className="input-base mt-1.5" /></label>
        <div className="space-y-2 rounded-2xl border border-line bg-sage-50 p-4"><p className="flex items-center gap-2 text-sm font-extrabold">{nb.locked ? <Lock size={15} /> : <LockOpen size={15} />}Privacy lock <span className="text-xs font-medium text-ink-500">{nb.locked ? "This notebook is locked." : "Not locked."}</span></p>
          {nb.locked ? <PasswordField label="Current password" value={cur} onChange={setCur} /> : null}
          <PasswordField label={nb.locked ? "New password (to change it)" : "Set a password (min 6 characters)"} value={npw} onChange={setNpw} />
          <div className="flex flex-wrap gap-2"><Button size="sm" disabled={npw.length < 6 || (nb.locked && !cur)} loading={busy} onClick={() => lock(true)}>{nb.locked ? "Change password" : "Lock notebook"}</Button>{nb.locked ? <Button size="sm" variant="outline" disabled={!cur} onClick={() => lock(false)}>Remove lock</Button> : null}</div>
          <p className="text-[11px] text-ink-500">Server-side access control with a 30-minute unlock. No recovery if the password is lost.</p></div>
      </div>
    </Modal>
  );
}
