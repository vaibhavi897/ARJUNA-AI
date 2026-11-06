import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { ArrowUpRight, Bookmark, BriefcaseBusiness, Copy, Linkedin, MapPin, MessageSquareText, Sparkles, Trash2, Users } from "lucide-react";
import { AppShell } from "../components/layout";
import { Badge, Button, Card, EmptyState } from "../components/ui";
import { COMPANIES, DOMAINS, OPPORTUNITIES, PROFESSIONALS, type Opportunity, type Professional } from "../lib/careerConnectData";
import { request } from "../lib/api";
import { useToast } from "../lib/auth";
import { cn } from "../lib/utils";

type Saved = { item_type: "job" | "professional"; item_id: string };
const purposes = ["career guidance", "informational interview", "referral request", "general networking"] as const;

function useSaved() {
  const [saved, setSaved] = useState<Saved[]>([]);
  const [loading, setLoading] = useState(true);
  const { push } = useToast();
  async function reload() {
    try { setSaved(await request<Saved[]>("/career-connect/saved")); }
    catch (e) { push({ title: "Could not load saved items", description: (e as Error).message, variant: "error" }); }
    finally { setLoading(false); }
  }
  useEffect(() => { void reload(); }, []);
  async function toggle(type: Saved["item_type"], id: string) {
    const has = saved.some((x) => x.item_type === type && x.item_id === id);
    try {
      if (has) await request(`/career-connect/saved/${type}/${encodeURIComponent(id)}`, { method: "DELETE" });
      else await request("/career-connect/saved", { method: "POST", body: { item_type: type, item_id: id } });
      setSaved((cur) => has ? cur.filter((x) => !(x.item_type === type && x.item_id === id)) : [...cur, { item_type: type, item_id: id }]);
    } catch (e) { push({ title: "Could not update saved items", description: (e as Error).message, variant: "error" }); }
  }
  return { saved, loading, reload, toggle };
}

function FilterBar({ domain, setDomain, company, setCompany }: {
  domain: string; setDomain: (v: string) => void; company: string; setCompany: (v: string) => void;
}) {
  return <div className="grid max-w-3xl gap-4 rounded-2xl border border-line bg-white p-4 sm:grid-cols-2">
    <label className="text-xs font-semibold text-ink-500">Career domain<select className="input-base mt-1" value={domain} onChange={(e) => setDomain(e.target.value)}><option value="">All career domains</option>{DOMAINS.map((d) => <option key={d}>{d}</option>)}</select></label>
    <label className="text-xs font-semibold text-ink-500">Company<select className="input-base mt-1" value={company} onChange={(e) => setCompany(e.target.value)}><option value="">All companies</option>{COMPANIES.map((c) => <option key={c}>{c}</option>)}</select></label>
  </div>;
}

function DraftDialog({ person, onClose }: { person: Professional; onClose: () => void }) {
  const { push } = useToast();
  const [purpose, setPurpose] = useState<(typeof purposes)[number]>(purposes[0]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  async function generate() {
    setBusy(true); setMessage("");
    try { const result = await request<{ message: string }>("/career-connect/message-draft", { method: "POST", body: { purpose, professional_name: person.name, designation: person.designation, company: person.company, domain: person.domain } }); setMessage(result.message); }
    catch (e) { push({ title: "Could not draft message", description: (e as Error).message, variant: "error" }); }
    finally { setBusy(false); }
  }
  async function copy() { await navigator.clipboard.writeText(message); push({ title: "Message copied", variant: "success" }); }
  return <div className="fixed inset-0 z-50 grid place-items-center bg-ink-950/50 p-4" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}><Card className="w-full max-w-xl space-y-4 p-5 sm:p-7"><div className="flex justify-between gap-3"><div><h2 className="text-xl font-bold">Draft a message</h2><p className="mt-1 text-sm text-ink-500">For {person.name} · {person.company}. Nothing is sent automatically.</p></div><button onClick={onClose} aria-label="Close" className="text-ink-400">×</button></div><label className="block text-xs font-semibold text-ink-500">Message purpose<select className="input-base mt-1" value={purpose} onChange={(e) => setPurpose(e.target.value as typeof purpose)}>{purposes.map((p) => <option key={p}>{p}</option>)}</select></label><Button loading={busy} icon={<Sparkles size={16} />} onClick={() => void generate()}>{message ? "Regenerate draft" : "Generate draft"}</Button>{message && <><textarea className="input-base min-h-40" value={message} onChange={(e) => setMessage(e.target.value)} /><Button variant="secondary" icon={<Copy size={16} />} onClick={() => void copy()}>Copy message</Button></>}</Card></div>;
}

function OpportunityHub({ saved, toggle }: { saved: Saved[]; toggle: (t: Saved["item_type"], id: string) => Promise<void> }) {
  const [domain, setDomain] = useState(""); const [company, setCompany] = useState("");
  const filtered = OPPORTUNITIES.filter((x) => (!domain || x.domain === domain) && (!company || x.company === company));
  return <div className="space-y-5"><div><h2 className="text-2xl font-bold">Opportunity Hub</h2><p className="mt-1 text-sm text-ink-500">Curated starting points from job platforms. Listings are not fetched live.</p></div><FilterBar {...{ domain, setDomain, company, setCompany }} />{filtered.length ? <div className="grid gap-4 md:grid-cols-2">{filtered.map((job) => <OpportunityCard key={job.id} job={job} saved={saved.some((x) => x.item_type === "job" && x.item_id === job.id)} onSave={() => void toggle("job", job.id)} />)}</div> : <EmptyState title="No curated opportunities match" description="Try another domain or clear a filter." />}</div>;
}

function OpportunityCard({ job, saved, onSave }: { job: Opportunity; saved: boolean; onSave: () => void }) {
  return <Card className="flex flex-col gap-4 p-5"><div className="flex items-start justify-between gap-3"><div><Badge tone="forest">{job.domain}</Badge><h3 className="mt-3 text-lg font-bold">{job.title}</h3><p className="mt-1 text-sm text-ink-600">{job.company}</p><p className="mt-2 flex items-center gap-1.5 text-xs text-ink-500"><MapPin size={14} />{job.location} · {job.employmentType}</p></div><button onClick={onSave} className={cn("rounded-xl p-2", saved ? "bg-brand-50 text-brand-700" : "bg-sage-100 text-ink-500")} aria-label={saved ? "Remove saved job" : "Save job"}><Bookmark size={18} fill={saved ? "currentColor" : "none"} /></button></div><div className="mt-auto flex flex-wrap gap-2">{job.sources.map((source) => <a key={source.url} href={source.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-xl bg-forest-800 px-3 py-2 text-xs font-semibold text-white hover:bg-forest-900">{source.kind === "individual listing" ? "Apply / View Job" : "View job search"}<ArrowUpRight size={14} /><span className="sr-only"> at {source.name}</span></a>)}</div><p className="text-[11px] text-ink-400">{job.sources.map((s) => s.name).join(" · ")}</p></Card>;
}

function ProfessionalConnect({ saved, toggle }: { saved: Saved[]; toggle: (t: Saved["item_type"], id: string) => Promise<void> }) {
  const [domain, setDomain] = useState(""); const [company, setCompany] = useState(""); const [designation, setDesignation] = useState(""); const [draft, setDraft] = useState<Professional | null>(null);
  const filtered = PROFESSIONALS.filter((x) => (!domain || x.domain === domain) && (!company || x.company === company) && (!designation || x.designation.toLowerCase().includes(designation.toLowerCase())));
  return <div className="space-y-5"><div><h2 className="text-2xl font-bold">Professional Connect</h2><p className="mt-1 text-sm text-ink-500">Manually curated profile examples. Details shown are limited to the supplied information.</p></div><FilterBar {...{ domain, setDomain, company, setCompany }} /><label className="block max-w-sm text-xs font-semibold text-ink-500">Professional designation<input className="input-base mt-1" placeholder="e.g. Data Scientist" value={designation} onChange={(e) => setDesignation(e.target.value)} /></label>{filtered.length ? <div className="grid gap-4 md:grid-cols-2">{filtered.map((person) => <Card key={person.id} className="p-5"><div className="flex items-start gap-3"><div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-brand-50 text-brand-700"><Users size={19} /></div><div className="min-w-0 flex-1"><Badge tone="forest">{person.domain}</Badge><h3 className="mt-2 font-bold">{person.name}</h3><p className="text-sm text-ink-600">{person.designation}</p><p className="mt-1 text-xs text-ink-500">{person.company}{person.location ? ` · ${person.location}` : ""}</p></div></div><div className="mt-4 flex flex-wrap gap-2"><a href={person.url} target="_blank" rel="noreferrer" className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-[#0A66C2] px-3 text-xs font-semibold text-white"><Linkedin size={15} />View LinkedIn Profile<ArrowUpRight size={13} /></a><Button size="sm" variant="secondary" icon={<Bookmark size={14} />} onClick={() => void toggle("professional", person.id)}>{saved.some((x) => x.item_type === "professional" && x.item_id === person.id) ? "Saved" : "Save"}</Button><Button size="sm" variant="outline" icon={<MessageSquareText size={14} />} onClick={() => setDraft(person)}>Draft a Message</Button></div></Card>)}</div> : <EmptyState title="No curated profiles match" description="Try another domain or clear a filter." />}<Card className="p-4"><p className="text-sm font-semibold">Discover more</p><p className="mt-1 text-xs text-ink-500">LinkedIn may require sign-in. No additional company employee-search URLs were supplied, so none are fabricated here.</p></Card>{draft && <DraftDialog person={draft} onClose={() => setDraft(null)} />}</div>;
}

function SavedItems({ saved, loading, toggle }: { saved: Saved[]; loading: boolean; toggle: (t: Saved["item_type"], id: string) => Promise<void> }) {
  const jobs = saved.filter((x) => x.item_type === "job").map((x) => OPPORTUNITIES.find((j) => j.id === x.item_id)).filter((x): x is Opportunity => Boolean(x));
  const people = saved.filter((x) => x.item_type === "professional").map((x) => PROFESSIONALS.find((p) => p.id === x.item_id)).filter((x): x is Professional => Boolean(x));
  if (loading) return <p className="text-sm text-ink-500">Loading saved items…</p>;
  return <div className="space-y-7"><div><h2 className="text-2xl font-bold">My Saved</h2><p className="mt-1 text-sm text-ink-500">Your saved opportunities and professionals, linked to your Arjuna account.</p></div>{!jobs.length && !people.length ? <EmptyState title="Nothing saved yet" description="Save a job opportunity or professional to keep it here." /> : <><section className="space-y-3"><h3 className="font-bold">Saved opportunities · {jobs.length}</h3><div className="grid gap-3 md:grid-cols-2">{jobs.map((job) => <OpportunityCard key={job.id} job={job} saved onSave={() => void toggle("job", job.id)} />)}</div></section><section className="space-y-3"><h3 className="font-bold">Saved professionals · {people.length}</h3><div className="grid gap-3 md:grid-cols-2">{people.map((p) => <Card key={p.id} className="flex items-center justify-between gap-3 p-4"><div><p className="font-semibold">{p.name}</p><p className="text-xs text-ink-500">{p.designation} · {p.company}</p><a className="mt-1 inline-block text-xs text-brand-700 underline" href={p.url} target="_blank" rel="noreferrer">View LinkedIn Profile</a></div><Button size="sm" variant="ghost" icon={<Trash2 size={15} />} onClick={() => void toggle("professional", p.id)}>Remove</Button></Card>)}</div></section></>}</div>;
}

function CareerConnectFrame() {
  const { saved, loading, toggle } = useSaved();
  const tabs = [{ to: "/app/career-connect/opportunities", label: "Opportunity Hub", icon: <BriefcaseBusiness size={16} /> }, { to: "/app/career-connect/professionals", label: "Professional Connect", icon: <Users size={16} /> }, { to: "/app/career-connect/saved", label: "My Saved", icon: <Bookmark size={16} /> }];
  return <AppShell title="Arjuna Career Connect" subtitle="Curated opportunities and professional networking, in one place"><div className="mx-auto max-w-6xl space-y-6 pb-12"><div className="flex gap-2 overflow-x-auto rounded-2xl bg-sage-100 p-1">{tabs.map((tab) => <NavLink key={tab.to} to={tab.to} className={({ isActive }) => cn("inline-flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold", isActive ? "bg-white text-forest-800 shadow-sm" : "text-ink-500 hover:text-ink-800")} >{tab.icon}{tab.label}</NavLink>)}</div><Routes><Route index element={<OpportunityHub saved={saved} toggle={toggle} />} /><Route path="opportunities" element={<OpportunityHub saved={saved} toggle={toggle} />} /><Route path="professionals" element={<ProfessionalConnect saved={saved} toggle={toggle} />} /><Route path="saved" element={<SavedItems saved={saved} loading={loading} toggle={toggle} />} /></Routes></div></AppShell>;
}

export default CareerConnectFrame;
