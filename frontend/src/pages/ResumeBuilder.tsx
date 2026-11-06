/** Dynamic Resume Builder: pick a job, get a one-page tailored resume, edit it, export PDF or Word. */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, ArrowDown, ArrowLeft, ArrowUp, CheckCircle2, Download, FileText, Plus, RefreshCcw, Repeat, Sparkles, Trash2, Wand2 } from "lucide-react";
import { Badge, Button, Card, EmptyState, ErrorState, LoadingBlock, Modal, TextArea, TextInput } from "../components/ui";
import { AppShell } from "../components/layout";
import { useToast } from "../lib/auth";
import { cn } from "../lib/utils";
import { rb, download, previewPdf, type Candidate, type Content, type Entry, type Fit, type Section, type Version } from "../lib/resume";

const KIND_LABEL: Record<string, string> = { experience: "Experience", project: "Project", leadership: "Leadership", certification: "Certification", achievement: "Achievement" };
const ROLE_LABEL: Record<string, string> = { tech: "Technical", data: "Data", finance: "Finance", consulting: "Consulting", product: "Product", sales: "Sales", marketing: "Marketing", operations: "Operations", general: "General" };
const emptyEntry = (): Entry => ({ title: "", right: "", subtitle: "", subright: "", bullets: [""], source: {} });

function move<T>(arr: T[], i: number, d: number): T[] {
  const j = i + d;
  if (j < 0 || j >= arr.length) return arr;
  const c = arr.slice();
  [c[i], c[j]] = [c[j], c[i]];
  return c;
}

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t); }, [value, ms]);
  return v;
}

// ---------------------------------------------------------------- generate form + history
function Generate({ onDone }: { onDone: (v: Version) => void }) {
  const { push } = useToast();
  const [form, setForm] = useState({ job_title: "", company: "", job_description: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [check, setCheck] = useState<Awaited<ReturnType<typeof rb.check>> | null>(null);
  useEffect(() => { rb.check().then(setCheck).catch(() => undefined); }, []);

  const go = async () => {
    setErr(null);
    if (form.job_title.trim().length < 2) { setErr("Enter the job title you are applying for."); return; }
    setBusy(true);
    try {
      const v = await rb.generate({ job_title: form.job_title.trim(), company: form.company.trim() || undefined, job_description: form.job_description.trim() || undefined });
      push({ title: "Resume ready", description: "Review it, edit anything, then export.", variant: "success" });
      onDone(v);
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <Card className="p-6">
      <div className="mb-4 flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-50 text-brand-700"><Wand2 size={20} /></span>
        <div>
          <h2 className="text-lg font-bold text-forest-900">Tailor a resume to a job</h2>
          <p className="text-sm text-ink-500">Only three inputs. Everything else comes from your profile.</p>
        </div>
      </div>
      {check && !check.ready && (
        <div className="mb-4 rounded-xl border border-warn-500/30 bg-warn-50 p-3 text-sm text-warn-700">
          Your profile has no education, experience, projects or skills yet. Add them in Settings or import your resume first.
        </div>
      )}
      {check && check.ready && (
        <p className="mb-4 text-xs text-ink-500">
          Choosing from {check.counts.experience ?? 0} experiences, {check.counts.project ?? 0} projects, {check.counts.leadership ?? 0} leadership roles, {check.counts.certification ?? 0} certifications, {check.counts.achievement ?? 0} achievements and {check.skills} skills.
        </p>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        <TextInput label="Job title" required placeholder="e.g. Sales Executive" value={form.job_title} maxLength={160} onChange={(e) => setForm({ ...form, job_title: e.target.value })} />
        <TextInput label="Company" placeholder="e.g. Acme Corp (optional)" value={form.company} maxLength={160} onChange={(e) => setForm({ ...form, company: e.target.value })} />
      </div>
      <div className="mt-4">
        <TextArea label="Job description" hint="Optional but recommended. Paste the posting for sharper matching. Without it we infer from the title." rows={7} maxLength={12000} value={form.job_description} onChange={(e) => setForm({ ...form, job_description: e.target.value })} />
      </div>
      {err && <p role="alert" className="mt-3 text-sm font-medium text-danger-700">{err}</p>}
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Button onClick={go} loading={busy} icon={<Sparkles size={16} />} disabled={check ? !check.ready : false}>{busy ? "Tailoring…" : "Generate resume"}</Button>
        <span className="text-xs text-ink-500">Never invents facts or numbers. Everything stays on one page.</span>
      </div>
    </Card>
  );
}

function History({ rows, onOpen, onDelete }: { rows: Version[]; onOpen: (id: number) => void; onDelete: (id: number) => void }) {
  if (!rows.length) return null;
  return (
    <Card className="p-5">
      <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-500">Your tailored resumes</h3>
      <ul className="divide-y divide-line">
        {rows.map((r) => (
          <li key={r.id} className="flex items-center gap-3 py-2.5">
            <button className="min-w-0 flex-1 text-left" onClick={() => onOpen(r.id)}>
              <p className="truncate text-sm font-semibold text-forest-900">{r.title}</p>
              <p className="text-xs text-ink-500">{ROLE_LABEL[r.role_type] ?? r.role_type} · {r.updated_at ? new Date(r.updated_at).toLocaleDateString() : ""}{r.edited ? " · edited" : ""}</p>
            </button>
            <Button variant="ghost" size="sm" aria-label={`Delete ${r.title}`} onClick={() => onDelete(r.id)} icon={<Trash2 size={15} />} />
          </li>
        ))}
      </ul>
    </Card>
  );
}

// ---------------------------------------------------------------- editor pieces
function BulletEditor({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="space-y-2">
      {value.map((b, i) => (
        <div key={i} className="flex gap-2">
          <TextArea aria-label={`Bullet ${i + 1}`} rows={2} className="min-h-[56px] text-sm" value={b} onChange={(e) => onChange(value.map((x, k) => (k === i ? e.target.value : x)))} />
          <div className="flex flex-col gap-1">
            <Button variant="ghost" size="sm" aria-label="Move bullet up" onClick={() => onChange(move(value, i, -1))} icon={<ArrowUp size={14} />} />
            <Button variant="ghost" size="sm" aria-label="Move bullet down" onClick={() => onChange(move(value, i, 1))} icon={<ArrowDown size={14} />} />
            <Button variant="ghost" size="sm" aria-label="Remove bullet" onClick={() => onChange(value.filter((_, k) => k !== i))} icon={<Trash2 size={14} />} />
          </div>
        </div>
      ))}
      <Button variant="outline" size="sm" icon={<Plus size={14} />} onClick={() => onChange([...value, ""])}>Add bullet</Button>
    </div>
  );
}

function SectionEditor({ sec, onChange, onSwap }: { sec: Section; onChange: (s: Section) => void; onSwap: (ref: string | null, kind: string) => void }) {
  const swappable = ["experience", "projects", "leadership"].includes(sec.key);
  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <TextInput aria-label="Section title" className="max-w-[240px] font-bold" value={sec.title} onChange={(e) => onChange({ ...sec, title: e.target.value })} />
        {swappable && <Button variant="outline" size="sm" icon={<Plus size={14} />} onClick={() => onSwap(null, sec.key)}>Add from profile</Button>}
      </div>
      {sec.type === "entries" && (
        <div className="space-y-4">
          {(sec.entries ?? []).map((e, i) => {
            const set = (patch: Partial<Entry>) => onChange({ ...sec, entries: (sec.entries ?? []).map((x, k) => (k === i ? { ...x, ...patch } : x)) });
            return (
              <div key={i} className="rounded-xl border border-line bg-sage-50/40 p-3">
                <div className="grid gap-2 md:grid-cols-[1fr_180px]">
                  <TextInput aria-label="Entry title" placeholder="**Organisation** - Role" value={e.title} onChange={(ev) => set({ title: ev.target.value })} />
                  <TextInput aria-label="Dates" placeholder="Jan 2025 – Present" value={e.right} onChange={(ev) => set({ right: ev.target.value })} />
                  <TextInput aria-label="Subtitle" placeholder="Subtitle (optional)" value={e.subtitle} onChange={(ev) => set({ subtitle: ev.target.value })} />
                  <TextInput aria-label="Right subtitle" placeholder="e.g. **CGPA: 8.5/10**" value={e.subright} onChange={(ev) => set({ subright: ev.target.value })} />
                </div>
                <div className="mt-3"><BulletEditor value={e.bullets} onChange={(bullets) => set({ bullets })} /></div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button variant="ghost" size="sm" icon={<ArrowUp size={14} />} onClick={() => onChange({ ...sec, entries: move(sec.entries ?? [], i, -1) })}>Up</Button>
                  <Button variant="ghost" size="sm" icon={<ArrowDown size={14} />} onClick={() => onChange({ ...sec, entries: move(sec.entries ?? [], i, 1) })}>Down</Button>
                  {swappable && e.source?.ref && <Button variant="ghost" size="sm" icon={<Repeat size={14} />} onClick={() => onSwap(e.source!.ref!, sec.key)}>Swap</Button>}
                  <Button variant="ghost" size="sm" icon={<Trash2 size={14} />} onClick={() => onChange({ ...sec, entries: (sec.entries ?? []).filter((_, k) => k !== i) })}>Remove</Button>
                </div>
              </div>
            );
          })}
          <Button variant="outline" size="sm" icon={<Plus size={14} />} onClick={() => onChange({ ...sec, entries: [...(sec.entries ?? []), emptyEntry()] })}>Add blank entry</Button>
        </div>
      )}
      {sec.type === "bullets" && <BulletEditor value={sec.bullets ?? []} onChange={(bullets) => onChange({ ...sec, bullets })} />}
      {sec.type === "lines" && (
        <div className="space-y-2">
          {(sec.lines ?? []).map((l, i) => (
            <div key={i} className="grid gap-2 md:grid-cols-[170px_1fr_auto]">
              <TextInput aria-label="Label" value={l.label} onChange={(e) => onChange({ ...sec, lines: (sec.lines ?? []).map((x, k) => (k === i ? { ...x, label: e.target.value } : x)) })} />
              <TextArea aria-label="Text" rows={2} className="min-h-[44px] text-sm" value={l.text} onChange={(e) => onChange({ ...sec, lines: (sec.lines ?? []).map((x, k) => (k === i ? { ...x, text: e.target.value } : x)) })} />
              <Button variant="ghost" size="sm" aria-label="Remove line" icon={<Trash2 size={14} />} onClick={() => onChange({ ...sec, lines: (sec.lines ?? []).filter((_, k) => k !== i) })} />
            </div>
          ))}
          <Button variant="outline" size="sm" icon={<Plus size={14} />} onClick={() => onChange({ ...sec, lines: [...(sec.lines ?? []), { label: "", text: "" }] })}>Add line</Button>
        </div>
      )}
    </Card>
  );
}

function FitMeter({ fit }: { fit: Fit | null }) {
  if (!fit) return null;
  if (!fit.fits) return <div role="alert" className="flex items-center gap-2 rounded-xl bg-danger-50 px-3 py-2 text-sm font-medium text-danger-700"><AlertTriangle size={16} />About {fit.overflow_lines} line{fit.overflow_lines === 1 ? "" : "s"} too long for one page. Shorten or remove something to export.</div>;
  return <div className="flex items-center gap-2 rounded-xl bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800"><CheckCircle2 size={16} />Fits on one page{fit.shrunk ? ` (text scaled to ${Math.round(fit.scale * 100)}%)` : ""}</div>;
}

// ---------------------------------------------------------------- workspace
function Workspace({ initial, onBack, onChanged }: { initial: Version; onBack: () => void; onChanged: () => void }) {
  const { push } = useToast();
  const [v, setV] = useState<Version>(initial);
  const [content, setContent] = useState<Content>(initial.content!);
  const [fit, setFit] = useState<Fit | null>(initial.fit ?? null);
  const [status, setStatus] = useState<"saved" | "dirty" | "saving" | "error">("saved");
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfErr, setPdfErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [swap, setSwap] = useState<{ ref: string | null; kind: string } | null>(null);
  const [cands, setCands] = useState<Candidate[] | null>(null);
  const dirty = useRef(false);
  const first = useRef(true);
  const debounced = useDebounced(content, 800);

  // live preview from the same exporter that produces the download
  useEffect(() => {
    const ctl = new AbortController();
    previewPdf(debounced, ctl.signal).then((b) => {
      setPdfErr(null);
      setPdfUrl((old) => { if (old) URL.revokeObjectURL(old); return URL.createObjectURL(b); });
    }).catch((e) => { if ((e as Error).name !== "AbortError") setPdfErr((e as Error).message); });
    rb.fit(debounced).then(setFit).catch(() => undefined);
    return () => ctl.abort();
  }, [debounced]);
  useEffect(() => () => { if (pdfUrl) URL.revokeObjectURL(pdfUrl); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const save = useCallback(async (c: Content) => {
    setStatus("saving");
    try { await rb.save(v.id, c); dirty.current = false; setStatus("saved"); onChanged(); return true; } catch { setStatus("error"); return false; }
  }, [v.id, onChanged]);

  useEffect(() => {
    if (first.current) { first.current = false; return; }
    if (!dirty.current) return;
    void save(debounced);
  }, [debounced, save]);

  const edit = (c: Content) => { dirty.current = true; setStatus("dirty"); setContent(c); };
  const setSection = (i: number, s: Section) => edit({ ...content, sections: content.sections.map((x, k) => (k === i ? s : x)) });

  const adopt = (nv: Version) => { setV(nv); setContent(nv.content!); setFit(nv.fit ?? null); dirty.current = false; first.current = true; setStatus("saved"); onChanged(); };

  const regen = async () => {
    if (!window.confirm("Regenerate from your profile? Your manual edits to this version will be replaced.")) return;
    setBusy("regen");
    try { adopt(await rb.regenerate(v.id)); push({ title: "Regenerated", variant: "success" }); } catch (e) { push({ title: "Could not regenerate", description: (e as Error).message, variant: "error" }); } finally { setBusy(null); }
  };

  const exportAs = async (kind: "pdf" | "docx") => {
    setBusy(kind);
    try {
      if (dirty.current && !(await save(content))) throw new Error("Could not save your edits first. Try again.");
      await download(v.id, kind);
    } catch (e) { push({ title: `Could not export ${kind.toUpperCase()}`, description: (e as Error).message, variant: "error" }); } finally { setBusy(null); }
  };

  const openSwap = async (ref: string | null, kind: string) => {
    setSwap({ ref, kind }); setCands(null);
    try { setCands(await rb.candidates(v.id)); } catch (e) { push({ title: "Could not load your profile items", description: (e as Error).message, variant: "error" }); setSwap(null); }
  };
  const doSwap = async (addRef: string) => {
    if (!swap) return;
    setBusy("swap");
    try {
      if (dirty.current) await save(content);
      adopt(await rb.swap(v.id, addRef, swap.ref));
      setSwap(null);
    } catch (e) { push({ title: "Could not swap", description: (e as Error).message, variant: "error" }); } finally { setBusy(null); }
  };

  const sel = v.selection;
  const swapKinds = useMemo(() => ({ experience: "experience", projects: "project", leadership: "leadership" } as Record<string, string>), []);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="ghost" size="sm" icon={<ArrowLeft size={15} />} onClick={onBack}>All resumes</Button>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-lg font-bold text-forest-900">{v.title}</h2>
          <p className="text-xs text-ink-500">{ROLE_LABEL[v.role_type] ?? v.role_type} wording · {status === "saved" ? "All changes saved" : status === "saving" ? "Saving…" : status === "error" ? "Save failed, retrying on next edit" : "Unsaved changes"}</p>
        </div>
        <Button variant="outline" size="sm" icon={<RefreshCcw size={15} />} loading={busy === "regen"} onClick={regen}>Regenerate</Button>
        <Button variant="outline" size="sm" icon={<Download size={15} />} loading={busy === "docx"} onClick={() => exportAs("docx")}>Word</Button>
        <Button size="sm" icon={<Download size={15} />} loading={busy === "pdf"} disabled={!!fit && !fit.fits} onClick={() => exportAs("pdf")}>PDF</Button>
      </div>
      <FitMeter fit={fit} />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
        <div className="space-y-4 order-2 xl:order-1">
          <Card className="p-4">
            <h3 className="mb-2 text-sm font-bold text-forest-900">Header</h3>
            <TextInput aria-label="Name" value={content.header.name} onChange={(e) => edit({ ...content, header: { ...content.header, name: e.target.value } })} />
            <div className="mt-2 grid gap-2 md:grid-cols-2">
              {content.header.contacts.map((c, i) => (
                <TextInput key={i} aria-label={`Contact ${i + 1}`} value={c} onChange={(e) => edit({ ...content, header: { ...content.header, contacts: content.header.contacts.map((x, k) => (k === i ? e.target.value : x)) } })} />
              ))}
            </div>
          </Card>
          {content.sections.map((s, i) => (
            <SectionEditor key={`${s.key}-${i}`} sec={s} onChange={(n) => setSection(i, n)} onSwap={(ref, key) => openSwap(ref, swapKinds[key] ?? key)} />
          ))}
          <p className="text-xs text-ink-500">Tip: wrap words in **double asterisks** for bold and *single asterisks* for italic.</p>

          {sel && (
            <Card className="p-4">
              <h3 className="mb-3 text-sm font-bold text-forest-900">Why these were chosen</h3>
              <ul className="space-y-2">
                {sel.included.map((i) => (
                  <li key={i.ref} className="rounded-lg border border-line p-2.5 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-forest-900">{i.title}{i.org ? ` · ${i.org}` : ""}</span>
                      <Badge tone="brand">{KIND_LABEL[i.kind] ?? i.kind} · {Math.round(i.score)}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-ink-500">{i.reasons.join(" · ")}</p>
                    {i.flags.map((f) => <p key={f} className="mt-1 flex items-start gap-1 text-xs text-warn-700"><AlertTriangle size={12} className="mt-0.5 shrink-0" />{f}</p>)}
                  </li>
                ))}
              </ul>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div>
                  <p className="mb-1 text-xs font-bold uppercase text-ink-500">Job keywords you cover</p>
                  <div className="flex flex-wrap gap-1.5">{sel.keywords_found.length ? sel.keywords_found.map((k) => <Badge key={k} tone="forest">{k}</Badge>) : <span className="text-xs text-ink-500">None found</span>}</div>
                </div>
                <div>
                  <p className="mb-1 text-xs font-bold uppercase text-ink-500">Not in your profile</p>
                  <div className="flex flex-wrap gap-1.5">{sel.keywords_missing.length ? sel.keywords_missing.map((k) => <Badge key={k} tone="warn">{k}</Badge>) : <span className="text-xs text-ink-500">Nothing missing</span>}</div>
                  <p className="mt-1 text-xs text-ink-500">Only add these if they are true. Add them to your profile and regenerate.</p>
                </div>
              </div>
              {!sel.ai_tailored && <p className="mt-3 text-xs text-ink-500">Bullets use your original wording because AI tailoring was unavailable for this version.</p>}
            </Card>
          )}
        </div>

        <div className="order-1 xl:order-2">
          <div className="xl:sticky xl:top-4">
            <Card className="overflow-hidden p-0">
              <div className="flex items-center justify-between border-b border-line px-4 py-2 text-xs font-semibold text-ink-500"><span>Live preview · exact PDF output</span>{pdfErr && <span className="text-danger-700">{pdfErr}</span>}</div>
              {pdfUrl ? <iframe title="Resume preview" src={`${pdfUrl}#toolbar=0&navpanes=0&view=FitH`} className="h-[78vh] w-full bg-white" /> : <LoadingBlock label="Rendering preview" rows={6} />}
            </Card>
          </div>
        </div>
      </div>

      <Modal open={!!swap} onClose={() => setSwap(null)} title={swap?.ref ? "Swap for another item" : "Add from your profile"} description="Ranked by relevance to this job. The wording is tailored from your own facts." size="lg">
        {!cands ? <LoadingBlock label="Loading" rows={4} /> : (
          <ul className="max-h-[60vh] space-y-2 overflow-y-auto">
            {cands.filter((c) => c.kind === swap?.kind).map((c) => (
              <li key={c.ref} className="flex items-center gap-3 rounded-xl border border-line p-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-forest-900">{c.title}{c.org ? ` · ${c.org}` : ""}</p>
                  <p className="text-xs text-ink-500">{c.reasons.join(" · ")}</p>
                </div>
                <Badge tone={c.included ? "forest" : "brand"}>{c.included ? "On resume" : `Score ${Math.round(c.score)}`}</Badge>
                <Button size="sm" variant="outline" disabled={c.included || busy === "swap"} onClick={() => doSwap(c.ref)}>Use</Button>
              </li>
            ))}
            {cands.filter((c) => c.kind === swap?.kind).length === 0 && <li className="text-sm text-ink-500">Nothing else of this type in your profile.</li>}
          </ul>
        )}
      </Modal>
    </div>
  );
}

// ---------------------------------------------------------------- page
export default function ResumeBuilder() {
  const { push } = useToast();
  const [rows, setRows] = useState<Version[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [open, setOpen] = useState<Version | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => rb.list().then(setRows).catch((e) => setErr((e as Error).message)), []);
  useEffect(() => { void load(); }, [load]);

  const openId = async (id: number) => {
    setLoading(true);
    try { setOpen(await rb.get(id)); } catch (e) { push({ title: "Could not open resume", description: (e as Error).message, variant: "error" }); } finally { setLoading(false); }
  };
  const del = async (id: number) => {
    if (!window.confirm("Delete this tailored resume? Your profile is not affected.")) return;
    try { await rb.remove(id); void load(); } catch (e) { push({ title: "Could not delete", description: (e as Error).message, variant: "error" }); }
  };

  return (
    <AppShell title="Dynamic Resume Builder" subtitle="A one-page resume rebuilt for every job from the profile you already have">
    <div className="space-y-5">
      {err && <ErrorState message={err} onRetry={() => { setErr(null); void load(); }} />}
      {loading && <LoadingBlock label="Opening resume" rows={4} />}
      {!loading && open && <Workspace key={open.id} initial={open} onBack={() => setOpen(null)} onChanged={() => void load()} />}
      {!loading && !open && (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
          <Generate onDone={(v) => { setOpen(v); void load(); }} />
          {rows === null && !err ? <LoadingBlock label="Loading" rows={3} /> : rows && rows.length ? <History rows={rows} onOpen={openId} onDelete={del} /> : (
            <EmptyState icon={<FileText size={22} />} title="No tailored resumes yet" description="Generate your first one from a job title and description." />
          )}
        </div>
      )}
    </div>
    </AppShell>
  );
}
