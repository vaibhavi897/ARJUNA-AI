/** Communication breakdown for an interview: vocabulary, clarity of thought, filler words and vocal delivery. */
import { AlertTriangle, AudioLines, Brain, MessageSquareWarning, Mic, Sparkles } from "lucide-react";
import { Badge, Card } from "./ui";
import { cn } from "../lib/utils";

type Block = { available: boolean; message?: string; score?: number; band?: string; notes?: string[] };
export type Communication = {
  words_total: number; avg_answer_words: number; caveat?: string;
  vocabulary: Block & { unique_ratio?: number; avg_word_length?: number; advanced_words?: string[]; overused?: { word: string; count: number }[] };
  clarity: Block & { avg_sentence_words?: number; longest_sentence_words?: number; structure_markers?: number; hedges?: number };
  fillers: Block & { total?: number; per_100_words?: number; top?: { word: string; count: number }[]; note?: string };
  delivery: { available: boolean; message?: string; confidence_score?: number; confidence_band?: string; words_per_minute?: number; long_pauses_per_minute?: number; volume_steadiness?: number | null; voice_energy?: number | null; spoken_answers?: number; notes?: string[]; caveat?: string };
  per_answer: { index: number; question?: string; words: number; fillers: number; spoken: boolean }[];
};

const tone = (s: number) => (s >= 80 ? "#187C4F" : s >= 65 ? "#229A63" : s >= 50 ? "#C9872B" : "#C0493D");

function Dial({ score, label, icon, sub }: { score: number | null; label: string; icon: React.ReactNode; sub?: string }) {
  const r = 34, c = 2 * Math.PI * r;
  return (
    <div className="flex flex-col items-center rounded-2xl border border-line bg-white p-4 text-center">
      <div className="relative grid h-24 w-24 place-items-center">
        <svg viewBox="0 0 80 80" className="absolute inset-0 -rotate-90">
          <circle cx="40" cy="40" r={r} fill="none" stroke="#E3EAE5" strokeWidth="7" />
          {score !== null ? <circle cx="40" cy="40" r={r} fill="none" stroke={tone(score)} strokeWidth="7" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - score / 100)} style={{ transition: "stroke-dashoffset 1s ease" }} /> : null}
        </svg>
        <span className="text-2xl font-extrabold tabular-nums text-forest-900">{score ?? "—"}</span>
      </div>
      <p className="mt-2 flex items-center gap-1.5 text-sm font-bold text-forest-900">{icon}{label}</p>
      <p className="text-xs text-ink-500">{sub ?? " "}</p>
    </div>
  );
}

function Notes({ items }: { items?: string[] }) {
  if (!items?.length) return null;
  return <ul className="mt-2 space-y-1">{items.map((n, i) => <li key={i} className="flex gap-2 text-xs leading-relaxed text-ink-600"><Sparkles size={12} className="mt-0.5 shrink-0 text-brand-600" />{n}</li>)}</ul>;
}

export default function CommunicationReport({ data }: { data: Communication }) {
  const { vocabulary: v, clarity: c, fillers: f, delivery: d } = data;
  return (
    <Card className="space-y-5 p-5 sm:p-6">
      <div>
        <h3 className="text-lg font-extrabold text-forest-900">How you communicated</h3>
        <p className="mt-0.5 text-sm text-ink-500">Measured from your actual answers: {data.words_total.toLocaleString()} words across {data.per_answer.length} answers (about {data.avg_answer_words} words each).</p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Dial score={v.available ? v.score ?? null : null} label="Vocabulary" icon={<Brain size={14} className="text-brand-600" />} sub={v.available ? v.band : "Not enough text"} />
        <Dial score={c.available ? c.score ?? null : null} label="Clarity of thought" icon={<Sparkles size={14} className="text-brand-600" />} sub={c.available ? c.band : "Not enough text"} />
        <Dial score={f.available ? f.score ?? null : null} label="Filler control" icon={<MessageSquareWarning size={14} className="text-brand-600" />} sub={f.available ? `${f.per_100_words} per 100 words` : "Not enough text"} />
        <Dial score={d.available ? d.confidence_score ?? null : null} label="Vocal confidence" icon={<Mic size={14} className="text-brand-600" />} sub={d.available ? d.confidence_band : "Answer by voice"} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl bg-brand-50/50 p-4">
          <h4 className="text-sm font-extrabold text-forest-900">Vocabulary</h4>
          {v.available ? (
            <>
              <p className="mt-1 text-xs text-ink-600">Word variety {Math.round((v.unique_ratio ?? 0) * 100)}% · average word length {v.avg_word_length} letters</p>
              {v.advanced_words?.length ? <div className="mt-2 flex flex-wrap gap-1.5">{v.advanced_words.map((w) => <Badge key={w} tone="brand">{w}</Badge>)}</div> : null}
              <Notes items={v.notes} />
            </>
          ) : <p className="mt-1 text-xs text-ink-500">{v.message}</p>}
        </section>

        <section className="rounded-2xl bg-brand-50/50 p-4">
          <h4 className="text-sm font-extrabold text-forest-900">Clarity of thought</h4>
          {c.available ? (
            <>
              <p className="mt-1 text-xs text-ink-600">Average sentence {c.avg_sentence_words} words · {c.structure_markers} reasoning signposts · {c.hedges} hedges</p>
              <Notes items={c.notes} />
            </>
          ) : <p className="mt-1 text-xs text-ink-500">{c.message}</p>}
        </section>

        <section className="rounded-2xl bg-brand-50/50 p-4">
          <h4 className="text-sm font-extrabold text-forest-900">Filler words</h4>
          {f.available ? (
            <>
              <p className="mt-1 text-xs text-ink-600">{f.total} fillers · {f.per_100_words} per 100 words</p>
              {f.top?.length ? <div className="mt-2 flex flex-wrap gap-1.5">{f.top.map((t) => <Badge key={t.word} tone="warn">{t.word} ×{t.count}</Badge>)}</div> : <p className="mt-2 text-xs text-ink-500">None found.</p>}
              <p className="mt-2 text-xs leading-relaxed text-ink-600">{f.note}</p>
            </>
          ) : <p className="mt-1 text-xs text-ink-500">{f.message}</p>}
        </section>

        <section className="rounded-2xl bg-brand-50/50 p-4">
          <h4 className="flex items-center gap-1.5 text-sm font-extrabold text-forest-900"><AudioLines size={14} />Voice delivery</h4>
          {d.available ? (
            <>
              <div className="mt-2 grid grid-cols-3 gap-2 text-center">
                {[["Pace", `${d.words_per_minute} wpm`], ["Long pauses", `${d.long_pauses_per_minute}/min`], ["Steadiness", d.volume_steadiness != null ? `${d.volume_steadiness}` : "n/a"]].map(([l, x]) => (
                  <div key={l} className="rounded-xl bg-white py-2"><p className="text-[11px] font-semibold text-ink-500">{l}</p><p className="text-sm font-extrabold text-brand-700">{x}</p></div>
                ))}
              </div>
              <Notes items={d.notes} />
              <p className="mt-2 text-[11px] text-ink-400">{d.caveat}</p>
            </>
          ) : <p className="mt-1 text-xs text-ink-500">{d.message}</p>}
        </section>
      </div>

      <div>
        <h4 className="mb-2 text-sm font-extrabold text-forest-900">Fillers by answer</h4>
        <ul className="space-y-1.5">
          {data.per_answer.map((a) => (
            <li key={a.index} className="flex items-center gap-3 text-xs">
              <span className="w-6 shrink-0 font-bold text-brand-700">Q{a.index}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-sage-200"><div className={cn("h-full rounded-full", a.fillers > a.words / 20 ? "bg-warn-500" : "bg-brand-500")} style={{ width: `${Math.min(100, a.words ? (a.fillers / Math.max(1, a.words)) * 1000 : 0)}%` }} /></div>
              <span className="w-28 shrink-0 text-right text-ink-500">{a.fillers} fillers · {a.words} words{a.spoken ? " · voice" : ""}</span>
            </li>
          ))}
        </ul>
      </div>
      {data.caveat ? <p className="flex gap-1.5 text-[11px] leading-relaxed text-ink-400"><AlertTriangle size={12} className="mt-0.5 shrink-0" />{data.caveat}</p> : null}
    </Card>
  );
}
