/** "Save to notebook" dialog. Locked notebooks are unlocked server-side before anything is written. */
import { useState } from "react";
import { Lock } from "lucide-react";
import { Button, EmptyState, Modal } from "../ui";
import { lh, type NotebookCard } from "../../lib/learning";
import { useToast } from "../../lib/auth";
import { useLoad } from "./shared";
import { cn } from "../../lib/utils";

export function SaveToNotebook({ open, onClose, kind, id }: { open: boolean; onClose: () => void; kind: "material" | "video"; id: number }) {
  const { push } = useToast();
  const list = useLoad(() => (open ? lh.notebooks() : Promise.resolve(null)), [open]);
  const [pick, setPick] = useState<NotebookCard | null>(null);
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    if (!pick) return;
    setBusy(true); setErr(null);
    try {
      let token: string | undefined;
      if (pick.locked) token = (await lh.unlock(pick.id, pw)).token ?? undefined;
      const page = kind === "material" ? await lh.saveMaterial(pick.id, id, token) : await lh.saveVideo(pick.id, id, token);
      push({ title: "Saved to notebook", description: `${pick.title}, page ${page.page_no}`, variant: "success" });
      setPw(""); setPick(null); onClose();
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }
  const items = list.data?.items ?? [];
  return (
    <Modal open={open} onClose={onClose} title="Save to a notebook" description="It becomes a new page you can edit, bookmark and revisit." size="md"
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
