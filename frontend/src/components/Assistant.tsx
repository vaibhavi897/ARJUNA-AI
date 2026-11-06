/** Floating site guide: type what you want to do and it takes you to the right tab. */
import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Send, X } from "lucide-react";
import { cn } from "../lib/utils";

// To use a photo you have the rights to, drop it in /public and set e.g. "/assistant.webp".
const AVATAR_SRC: string | null = "/assistant.webp";

type Dest = { to: string; label: string; says: string; words: string[] };
const DESTS: Dest[] = [
  { to: "/app/dashboard", label: "Student Dashboard", says: "Your readiness, gaps and profile at a glance.", words: ["dashboard", "home", "overview", "readiness", "profile", "gap", "score"] },
  { to: "/app/interview-arena", label: "Interview Arena", says: "Practise mock interviews and get scored feedback.", words: ["interview", "mock", "practice interview", "arena", "hr", "behavioural"] },
  { to: "/app/learning", label: "AI Learning Hub", says: "Your study plan, notes, quizzes and revision.", words: ["learn", "study", "plan", "notes", "quiz", "revision", "youtube", "planner", "diary", "mastery"] },
  { to: "/app/resume-builder", label: "Dynamic Resume Builder", says: "A one-page resume tailored to any job.", words: ["resume", "cv", "tailor", "job description", "jd", "pdf", "word", "docx"] },
  { to: "/app/careerverse", label: "CareerVerse", says: "Explore careers, stories, salaries and your fit.", words: ["career", "profession", "salary", "story", "explore", "fit", "role", "job market"] },
  { to: "/app/settings", label: "Settings", says: "Account, profile details and preferences.", words: ["setting", "account", "password", "preference", "edit profile", "logout", "email"] },
];

function match(q: string): Dest | null {
  const t = q.toLowerCase();
  let best: [number, Dest | null] = [0, null];
  for (const d of DESTS) {
    const s = d.words.reduce((n, w) => n + (t.includes(w) ? w.length : 0), 0) + (t.includes(d.label.toLowerCase()) ? 20 : 0);
    if (s > best[0]) best = [s, d];
  }
  return best[1];
}

function Avatar({ size = 48 }: { size?: number }) {
  if (AVATAR_SRC) return <img src={AVATAR_SRC} alt="" className="rounded-full object-cover object-top" style={{ width: size, height: size }} />;
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} role="img" aria-label="Assistant" className="rounded-full bg-sage-100">
      <circle cx="32" cy="32" r="32" fill="#E8EEEA" />
      <path d="M8 64c2-14 12-20 24-20s22 6 24 20z" fill="#3B4252" />
      <path d="M27 44l5 9 5-9-5-3z" fill="#fff" />
      <path d="M30.5 46h3l1 12-2.5 3-2.5-3z" fill="#14181f" />
      <path d="M22 46l10 18-14-2zM42 46L32 64l14-2z" fill="#2E3440" opacity=".6" />
      <circle cx="32" cy="27" r="11" fill="#E9C7A6" />
      <path d="M21 25c0-9 6-13 12-13s10 4 10 11c-3-3-7-5-11-5s-8 2-11 7z" fill="#6B4E37" />
      <circle cx="28" cy="28" r="1.2" fill="#222" /><circle cx="36" cy="28" r="1.2" fill="#222" />
      <path d="M28.5 33.5q3.5 2 7 0" stroke="#8a5a44" strokeWidth="1.2" fill="none" strokeLinecap="round" />
    </svg>
  );
}

type Msg = { from: "bot" | "me"; text: string; go?: Dest };

export default function Assistant() {
  const nav = useNavigate();
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([{ from: "bot", text: "Good to see you. Tell me what you want to do and I'll take you there." }]);
  const [tip, setTip] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [msgs, open]);

  const here = DESTS.find((d) => loc.pathname.startsWith(d.to));
  // greet once per page visit, then get out of the way
  useEffect(() => {
    setTip(true);
    const t = setTimeout(() => setTip(false), 6000);
    return () => clearTimeout(t);
  }, [loc.pathname]);
  const go = (d: Dest) => { nav(d.to); setOpen(false); };
  const ask = (text: string) => {
    const t = text.trim();
    if (!t) return;
    const d = match(t);
    setMsgs((m) => [...m, { from: "me", text: t }, d
      ? { from: "bot", text: `${d.label}: ${d.says}`, go: d }
      : { from: "bot", text: "I'm not sure which tab that is. Try one of these." }]);
    setQ("");
  };

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-3">
      {open && (
        <div role="dialog" aria-label="Site assistant" className="flex h-[min(520px,75vh)] w-[min(360px,calc(100vw-2rem))] flex-col overflow-hidden rounded-2xl border border-line bg-white shadow-2xl">
          <div className="flex items-center gap-3 bg-forest-800 px-4 py-3 text-white">
            <Avatar size={40} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold">Your guide</p>
              <p className="truncate text-xs text-white/70">{here ? `You're in ${here.label}` : "Ask me where to go"}</p>
            </div>
            <button aria-label="Close assistant" onClick={() => setOpen(false)} className="rounded-lg p-1.5 hover:bg-white/10"><X size={16} /></button>
          </div>
          <div className="flex-1 space-y-2 overflow-y-auto p-3">
            {msgs.map((m, i) => (
              <div key={i} className={cn("max-w-[85%] rounded-2xl px-3 py-2 text-sm", m.from === "me" ? "ml-auto bg-brand-600 text-white" : "bg-sage-100 text-ink-800")}>
                {m.text}
                {m.go && <button onClick={() => go(m.go!)} className="mt-2 block rounded-lg bg-forest-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-forest-900">Take me there</button>}
              </div>
            ))}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {DESTS.filter((d) => d !== here).map((d) => (
                <button key={d.to} onClick={() => go(d)} className="rounded-full border border-line bg-white px-2.5 py-1 text-xs font-semibold text-ink-700 hover:border-brand-400 hover:text-brand-700">{d.label}</button>
              ))}
            </div>
            <div ref={end} />
          </div>
          <form className="flex gap-2 border-t border-line p-2.5" onSubmit={(e) => { e.preventDefault(); ask(q); }}>
            <input aria-label="Ask the assistant" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. build a resume for a sales job" maxLength={200} className="input-base flex-1 text-sm" />
            <button type="submit" aria-label="Send" className="grid h-10 w-10 place-items-center rounded-xl bg-brand-600 text-white hover:bg-brand-700"><Send size={16} /></button>
          </form>
        </div>
      )}
      {tip && !open && here && (
        <button onClick={() => { setTip(false); setOpen(true); }} className="max-w-[260px] rounded-2xl rounded-br-sm border border-line bg-white px-3.5 py-2.5 text-left text-sm text-ink-700 shadow-xl animate-fade-in">
          <span className="block text-xs font-bold text-forest-800">{here.label}</span>{here.says} <span className="font-semibold text-brand-700">Need help?</span>
        </button>
      )}
      <button onClick={() => setOpen((o) => !o)} aria-label={open ? "Close assistant" : "Open assistant"} aria-expanded={open} className="rounded-full shadow-xl ring-4 ring-white transition-transform hover:scale-105">
        <Avatar size={60} />
      </button>
    </div>
  );
}
