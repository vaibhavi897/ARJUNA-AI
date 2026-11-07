import Waveform from "../components/Waveform";
import CommunicationReport, { type Communication } from "../components/CommunicationReport";
import { VoiceMeter } from "../lib/voiceMetrics";
import CodeEditor from "../components/CodeEditor";
import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, AlertTriangle, ArrowLeft, Camera, CheckCircle2, Clock3, History, Mic, MicOff, Play, Send, Shield, Square, Volume2, VolumeX } from "lucide-react";
import { SkillRadar } from "../components/charts";
import { AppShell } from "../components/layout";
import { Badge, Button, Card } from "../components/ui";
import { ApiError, api, type InterviewSession, type InterviewMessage } from "../lib/api";

const DOMAINS = ["Software Engineering", "ML/AI", "Data Analytics", "Management Consulting", "Finance/Investment Banking", "Corporate Risk", "Product Management", "HR/Management"];
const PERSONAS = ["Technical Interviewer", "HR Interviewer", "Finance Expert"];
const SENIORITY_LEVELS = [
  "Junior (0–3 years)",
  "Mid-Level (4–8 years)",
  "Senior (9–15 years)",
  "Expert/Leadership (15+ years)",
];
const AREAS = [
  { key: "technical", label: "Technical" },
  { key: "behavioural", label: "HR & Behavioural" },
] as const;
type Focus = { technical: number; behavioural: number };
const DEFAULTS: Record<string, Focus> = {
  "Software Engineering": { technical: 75, behavioural: 25 },
  "ML/AI": { technical: 75, behavioural: 25 },
  "Data Analytics": { technical: 70, behavioural: 30 },
  "Management Consulting": { technical: 65, behavioural: 35 },
  "Finance/Investment Banking": { technical: 70, behavioural: 30 },
  "Corporate Risk": { technical: 70, behavioural: 30 },
  "Product Management": { technical: 65, behavioural: 35 },
  "HR/Management": { technical: 45, behavioural: 55 },
};
const AREA_LABEL: Record<string, string> = {
  technical: "Technical",
  behavioural: "HR & Behavioural",
  case_study: "Technical",
  resume_projects: "Technical",
};
const FOCUS_COLORS: Record<keyof Focus, string> = {
  technical: "#187C4F",
  behavioural: "#44B47C",
};

function formatDate(value: string | null) {
  if (!value) return "In progress";
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function InterviewArena() {
  const [history, setHistory] = useState<InterviewSession[]>([]);
  const [domain, setDomain] = useState(DOMAINS[0]);
  const [personas, setPersonas] = useState<string[]>(["Technical Interviewer", "HR Interviewer"]);
  const [seniority, setSeniority] = useState(SENIORITY_LEVELS[1]);
  const [jobDescription, setJobDescription] = useState("");
  const [uploadingJd, setUploadingJd] = useState(false);
  const [focus, setFocus] = useState<Focus>(DEFAULTS[DOMAINS[0]]);
  const [consent, setConsent] = useState(false);
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [selectedReport, setSelectedReport] = useState<InterviewSession | null>(null);
  const [answer, setAnswer] = useState("");
  const [codeMode, setCodeMode] = useState(false);
  const [lang, setLang] = useState("python");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cameraOn, setCameraOn] = useState(false);
  const [micOn, setMicOn] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [listening, setListening] = useState(false);
  const [muted, setMuted] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [signals, setSignals] = useState<{ type: string; at: string; detail?: string }[]>([]);
  const mediaRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const recognitionRef = useRef<any>(null);
  const meter = useRef<VoiceMeter | null>(null);
  if (!meter.current) meter.current = new VoiceMeter();
  const multipleFacesReported = useRef(false);

  const reloadHistory = useCallback(async () => {
    setLoading(true);
    try { setHistory(await api.interviewHistory()); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Interview history could not be loaded."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void reloadHistory(); }, [reloadHistory]);
  useEffect(() => { setFocus(DEFAULTS[domain]); }, [domain]);
  useEffect(() => {
    if (!session || session.status !== "active") return;
    const started = Date.parse(session.started_at);
    const tick = () => setElapsed(Math.max(0, Math.floor((Date.now() - started) / 1000)));
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [session?.id, session?.started_at, session?.status]);
  useEffect(() => {
    if (!session || session.status !== "active" || !session.consent_media) return;
    const onVisibility = () => {
      if (document.hidden) setSignals((old) => [...old, { type: "tab_hidden", at: new Date().toISOString(), detail: "Browser tab became hidden." }]);
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [session?.id, session?.status, session?.consent_media]);
  useEffect(() => {
    if (!session || session.status !== "active" || !session.consent_media || !cameraOn || !videoRef.current) return;
    const FaceDetector = (window as any).FaceDetector;
    if (!FaceDetector) return;
    let stopped = false;
    const detector = new FaceDetector({ fastMode: true, maxDetectedFaces: 4 });
    const scan = async () => {
      if (stopped || !videoRef.current || videoRef.current.readyState < 2) return;
      try {
        const faces = await detector.detect(videoRef.current);
        if (faces.length > 1 && !multipleFacesReported.current) {
          multipleFacesReported.current = true;
          addSignal("multiple_faces", `${faces.length} faces detected in a frame; this is an indicator only.`);
        }
      } catch { /* Unsupported detector input is ignored; no face conclusion is drawn. */ }
    };
    const timer = window.setInterval(() => void scan(), 5000);
    void scan();
    return () => { stopped = true; window.clearInterval(timer); };
  }, [session?.id, session?.status, session?.consent_media, cameraOn]);
  useEffect(() => () => {
    recognitionRef.current?.stop?.();
    mediaRef.current?.getTracks().forEach((track) => track.stop());
    window.speechSynthesis?.cancel();
  }, []);

  const messages = session?.transcript ?? [];
  const currentQuestion = [...messages].reverse().find((m) => m.role === "interviewer");
  const awaitingNextQuestion = messages.length > 0 && messages[messages.length - 1].role === "student";
  const attempted = messages.filter((m) => m.role === "student").length;
  const totalFocus = Object.values(focus).reduce((sum, n) => sum + Number(n || 0), 0);

  const addSignal = (type: string, detail?: string) => setSignals((old) => [...old, { type, at: new Date().toISOString(), detail }]);
  const togglePersona = (value: string) => setPersonas((old) => old.includes(value) ? old.filter((x) => x !== value) : old.length < 3 ? [...old, value] : old);
  const updateFocus = (key: keyof Focus, value: number) => {
    const nextValue = Math.max(0, Math.min(100, Math.round(value)));
    setFocus(key === "technical"
      ? { technical: nextValue, behavioural: 100 - nextValue }
      : { technical: 100 - nextValue, behavioural: nextValue });
  };

  const start = async () => {
    setError(null);
    if (totalFocus !== 100) { setError("Focus percentages need to total 100%."); return; }
    if (!personas.length) { setError("Select at least one interviewer persona."); return; }
    setBusy(true);
    let stream: MediaStream | null = null;
    try {
      if (consent && navigator.mediaDevices?.getUserMedia) {
        try {
          stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
          mediaRef.current = stream;
          setCameraOn(true); setMicOn(true);
          stream.getVideoTracks().forEach((track) => track.addEventListener("ended", () => { setCameraOn(false); addSignal("camera_disconnected", "Camera track disconnected."); }));
          stream.getAudioTracks().forEach((track) => track.addEventListener("ended", () => { setMicOn(false); addSignal("microphone_disconnected", "Microphone track disconnected."); }));
        } catch { setError("Camera/microphone access was unavailable. You can continue with text and browser speech tools."); }
      }
      const created = await api.startInterview({ domain, personas, focus, consent_media: consent, seniority, job_description: jobDescription.trim() || null });
      setSignals([]); multipleFacesReported.current = false; setSession(created); setSelectedReport(null); setElapsed(0); setAnswer("");
      if (videoRef.current && stream) videoRef.current.srcObject = stream;
      speak([...created.transcript].reverse().find((m) => m.role === "interviewer")?.text ?? "");
      if (consent && !stream) addSignal("media_unavailable", "Media permission was granted for integrity signals, but the browser did not provide a stream.");
    } catch (e) { setError(e instanceof ApiError ? e.message : "Could not start interview."); stream?.getTracks().forEach((t) => t.stop()); }
    finally { setBusy(false); }
  };

  const speak = (text: string) => {
    if (!text || muted || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.96;
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const submitAnswer = async () => {
    if (!session || !answer.trim()) return;
    setBusy(true); setError(null);
    try {
      const voice = meter.current?.snapshot() ?? null;
      const result = await api.answerInterview(session.id, answer.trim(), voice);
      meter.current?.reset();
      setSession(result.session); setAnswer(""); setError(result.message ?? (result.closing && result.session.transcript.at(-1)?.role === "student" ? "Your answer was saved, but no next question came back. End the interview to review your saved responses." : null));
      if (result.session.status === "active" && result.session.transcript.at(-1)?.role === "interviewer") speak(result.session.transcript.at(-1)?.text ?? "");
    } catch (e) { setError(e instanceof ApiError ? e.message : "Could not submit your response."); }
    finally { setBusy(false); }
  };

  const endInterview = async () => {
    if (!session || session.status !== "active") return;
    if (!window.confirm("End this interview now? Your attempted responses will be saved and evaluated. Ending early will not be penalized.")) return;
    setBusy(true); setError(null); window.speechSynthesis?.cancel(); recognitionRef.current?.stop?.();
    try {
      const ended = await api.endInterview(session.id, signals);
      setSession(ended); setSelectedReport(ended); mediaRef.current?.getTracks().forEach((track) => track.stop()); mediaRef.current = null;
      setCameraOn(false); setMicOn(false); await reloadHistory();
    } catch (e) { setError(e instanceof ApiError ? e.message : "Could not save the interview report."); }
    finally { setBusy(false); }
  };

  const toggleListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) { setError("Speech recognition is not supported in this browser. You can type your response instead."); return; }
    if (listening) { recognitionRef.current?.stop?.(); meter.current?.pause(); setListening(false); return; }
    const recognition = new SpeechRecognition(); recognition.lang = "en-US"; recognition.continuous = true; recognition.interimResults = true;
    recognition.onresult = (event: any) => {
      let finalText = ""; let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) (event.results[i].isFinal ? finalText += event.results[i][0].transcript + " " : interim += event.results[i][0].transcript);
      if (finalText) { meter.current?.addWords(finalText); setAnswer((old) => `${old}${old ? " " : ""}${finalText.trim()}`); }
      if (interim) setListening(true);
    };
    recognition.onerror = () => { meter.current?.pause(); setListening(false); }; recognition.onend = () => { meter.current?.pause(); setListening(false); };
    recognitionRef.current = recognition; recognition.start(); void meter.current?.start(); setListening(true); setMicOn(true);
  };

  const showSession = (item: InterviewSession) => {
    setSelectedReport(item); setSession(item.status === "active" ? item : null);
    setError(null);
  };

  if (session?.status === "active") return <AppShell title="Interview Arena" subtitle="Personalized practice, one question at a time." actions={<Button variant="danger" size="sm" icon={<Square size={14} />} onClick={endInterview} disabled={busy}>End Interview</Button>}>
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div className="space-y-5">
        <Card className="overflow-hidden p-0">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-white px-5 py-4">
            <div><p className="font-bold text-ink-900">{session.domain}</p><p className="mt-0.5 text-xs text-ink-500">{session.personas.join(" · ")}</p></div>
            <div className="flex items-center gap-2"><Badge tone={speaking ? "brand" : listening ? "warn" : "forest"}>{speaking ? "Interviewer speaking" : listening ? "Listening" : "Your turn"}</Badge><span className="flex items-center gap-1 text-xs tabular-nums text-ink-500"><Clock3 size={14} />{Math.floor(elapsed / 60).toString().padStart(2, "0")}:{(elapsed % 60).toString().padStart(2, "0")}</span></div>
          </div>
          <div className="bg-gradient-to-br from-forest-900 to-forest-800 p-6 text-white sm:p-9">
            <p className="text-2xs font-semibold uppercase tracking-[0.16em] text-brand-300">{awaitingNextQuestion ? "Response saved" : `Current question · ${AREA_LABEL[currentQuestion?.category ?? ""] ?? "Interview"}`}</p>
            <h2 className="mt-4 max-w-3xl font-display text-2xl font-bold leading-relaxed text-white sm:text-3xl">{awaitingNextQuestion ? (error ? "Your response is saved. End the interview to review it." : "Your response is saved. Preparing your next question…") : currentQuestion?.text ?? "Preparing your next question…"}</h2>
            <div className="mt-6 flex flex-wrap gap-2"><Button size="sm" variant="secondary" icon={<Volume2 size={15} />} onClick={() => speak(currentQuestion?.text ?? "")}>Repeat question</Button><Button size="sm" variant="ghost" className="text-white hover:bg-white/10 hover:text-white" icon={muted ? <VolumeX size={15} /> : <Volume2 size={15} />} onClick={() => { setMuted(!muted); if (!muted) window.speechSynthesis?.cancel(); }}> {muted ? "Enable voice" : "Mute voice"}</Button></div>
          </div>
          <div className="p-5 sm:p-6">
            {error && <p className="mb-4 rounded-xl border border-warn-500/25 bg-warn-50 p-3 text-sm text-warn-700">{error}</p>}
            <div className="mb-2 flex items-center justify-between gap-2"><label className="block text-sm font-semibold text-ink-800" htmlFor="answer">Your response</label>
              <div className="flex items-center gap-2">{codeMode && <select aria-label="Language" value={lang} onChange={(e) => setLang(e.target.value)} className="rounded-lg border border-line bg-white px-2 py-1 text-xs font-semibold">{["python", "javascript", "typescript", "java", "cpp", "sql"].map((l) => <option key={l}>{l}</option>)}</select>}
                <button type="button" onClick={() => setCodeMode((v) => !v)} className="rounded-lg border border-line px-2.5 py-1 text-xs font-bold text-ink-700 hover:border-brand-400 hover:text-brand-700">{codeMode ? "Switch to text" : "Write code"}</button></div></div>
            {codeMode ? <CodeEditor value={answer} onChange={setAnswer} language={lang} height={300} /> : <textarea id="answer" rows={5} value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Speak your answer or type it here…" className="input-base resize-y" onKeyDown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") void submitAnswer(); }} />}
            <Waveform active={listening} />
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2"><div className="flex items-center gap-2"><Button variant={listening ? "danger" : "outline"} size="sm" icon={listening ? <MicOff size={15} /> : <Mic size={15} />} onClick={toggleListening}>{listening ? "Stop dictation" : "Answer by voice"}</Button><span className="text-2xs text-ink-400">Ctrl/⌘ + Enter to submit</span></div><Button icon={<Send size={15} />} onClick={submitAnswer} loading={busy} disabled={!answer.trim() || awaitingNextQuestion}>Submit answer</Button></div>
          </div>
        </Card>
        <Card className="p-5"><h3 className="font-bold">Live transcript <span className="ml-1 text-xs font-medium text-ink-400">{attempted} attempted response{attempted === 1 ? "" : "s"}</span></h3><div className="mt-3 max-h-[330px] space-y-3 overflow-y-auto">{messages.map((m, i) => <TranscriptTurn key={`${i}-${m.at ?? ""}`} message={m} />)}</div></Card>
      </div>
      <div className="space-y-5">
        <Card className="overflow-hidden p-0"><div className="flex items-center justify-between border-b border-line px-4 py-3"><h3 className="text-sm font-bold">Interview room</h3><span className="flex gap-2"><span title={cameraOn ? "Camera on" : "Camera off"} className={cameraOn ? "text-brand-600" : "text-ink-300"}><Camera size={17} /></span><span title={micOn ? "Microphone on" : "Microphone off"} className={micOn ? "text-brand-600" : "text-ink-300"}><Mic size={17} /></span></span></div>{cameraOn ? <video ref={(el) => { videoRef.current = el; if (el && mediaRef.current) el.srcObject = mediaRef.current; }} autoPlay muted playsInline className="aspect-video w-full bg-forest-900 object-cover" /> : <div className="grid aspect-video place-items-center bg-sage-50 text-center"><div><Camera size={26} className="mx-auto text-sage-400" /><p className="mt-2 text-xs text-ink-500">Camera is off</p></div></div>}<div className="grid grid-cols-2 gap-2 p-3"><div className="flex items-center gap-2 rounded-lg bg-sage-50 p-2.5 text-xs"><span className={`h-2 w-2 rounded-full ${micOn ? "bg-brand-500" : "bg-ink-300"}`} />Microphone {micOn ? "on" : "off"}</div><div className="flex items-center gap-2 rounded-lg bg-sage-50 p-2.5 text-xs"><span className={`h-2 w-2 rounded-full ${cameraOn ? "bg-brand-500" : "bg-ink-300"}`} />Camera {cameraOn ? "on" : "off"}</div></div></Card>
        <Card className="p-4"><h3 className="flex items-center gap-2 text-sm font-bold"><Activity size={16} className="text-brand-600" />Interview focus</h3><div className="mt-3 space-y-2.5">{Object.entries(session.focus).map(([key, value]) => <div key={key}><div className="flex justify-between text-xs"><span className="text-ink-600">{AREA_LABEL[key] ?? key}</span><span className="font-semibold tabular-nums">{value}%</span></div><div className="mt-1 h-1.5 overflow-hidden rounded-full bg-sage-100"><div className="h-full rounded-full bg-brand-500" style={{ width: `${value}%` }} /></div></div>)}</div><p className="mt-3 text-2xs text-ink-400">Flexible session · end whenever you’re ready</p></Card>
        {session.consent_media && <Card className="p-4"><h3 className="flex items-center gap-2 text-sm font-bold"><Shield size={16} className="text-brand-600" />Integrity indicators</h3><p className="mt-2 text-xs leading-relaxed text-ink-500">Signals are indicators only, stored separately from performance and not treated as proof of misconduct.</p><p className="mt-2 text-xs font-semibold text-ink-700">{signals.length} signal{signals.length === 1 ? "" : "s"} observed</p></Card>}
      </div>
    </div>
  </AppShell>;

  if (selectedReport) return <AppShell title="Interview report" subtitle={`${selectedReport.domain} · ${formatDate(selectedReport.started_at)}`} actions={<Button variant="outline" size="sm" icon={<ArrowLeft size={15} />} onClick={() => { setSelectedReport(null); setSession(null); }}>Arena home</Button>}>
    <ReportView item={selectedReport} />
  </AppShell>;

  return <AppShell title="Interview Arena" subtitle="Practice realistic interviews tailored to your profile and career goals.">
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="space-y-5">
        <Card className="overflow-hidden p-0"><div className="mesh-forest p-6 text-white sm:p-8"><div className="flex items-center gap-2 text-brand-300"><Activity size={17} /><span className="text-2xs font-semibold uppercase tracking-[0.16em]">Arjuna Interview Arena</span></div><h2 className="mt-3 max-w-2xl font-display text-3xl font-extrabold text-white sm:text-4xl">Walk into your next interview prepared.</h2><p className="mt-3 max-w-2xl text-sm leading-relaxed text-white/70">Practice with adaptive AI interviewers using your profile, resume, projects, experience, and readiness insights. No job description needed.</p><div className="mt-5 flex flex-wrap gap-2 text-xs text-white/70"><span className="rounded-full bg-white/10 px-3 py-1.5">Flexible duration · ~40 min typical</span><span className="rounded-full bg-white/10 px-3 py-1.5">Voice or text responses</span><span className="rounded-full bg-white/10 px-3 py-1.5">Personalized follow-ups</span></div></div>
          <div className="space-y-6 p-5 sm:p-7"><section><label htmlFor="domain" className="mb-2 block text-sm font-bold">Target role / domain</label><select id="domain" value={domain} onChange={(e) => setDomain(e.target.value)} className="input-base">{DOMAINS.map((d) => <option key={d}>{d}</option>)}</select><p className="mt-1.5 text-xs text-ink-400">Interview questions adapt to the domain you select.</p></section>
            <section><div className="mb-2 flex items-end justify-between gap-3"><div><p className="text-sm font-bold">AI interviewer personas</p><p className="text-xs text-ink-400">Select 1–3 personas</p></div><span className="text-xs font-semibold text-brand-700">{personas.length}/3</span></div><div className="grid gap-2 sm:grid-cols-2">{PERSONAS.map((p) => <button type="button" key={p} onClick={() => togglePersona(p)} className={`flex items-center gap-2 rounded-xl border p-3 text-left text-sm font-medium transition-colors ${personas.includes(p) ? "border-brand-300 bg-brand-50 text-brand-800" : "border-line bg-white text-ink-600 hover:bg-sage-50"}`}><span className={`grid h-5 w-5 place-items-center rounded-full border ${personas.includes(p) ? "border-brand-600 bg-brand-600 text-white" : "border-line-strong"}`}>{personas.includes(p) && <CheckCircle2 size={14} />}</span>{p}</button>)}</div></section>
            <section><label htmlFor="seniority" className="mb-2 block text-sm font-bold">Interviewer seniority</label><select id="seniority" value={seniority} onChange={(e) => setSeniority(e.target.value)} className="input-base">{SENIORITY_LEVELS.map((level) => <option key={level}>{level}</option>)}</select><p className="mt-1.5 text-xs text-ink-400">Sets question complexity, expected depth, and follow-up rigor independently of persona.</p></section>
            <section className="space-y-3"><div><label htmlFor="job-description" className="block text-sm font-bold">Job description <span className="font-normal text-ink-400">(optional)</span></label><p className="mt-1 text-xs text-ink-400">Paste the role details or upload a PDF/DOCX to tailor questions to its responsibilities and requirements.</p></div><textarea id="job-description" rows={5} maxLength={20000} value={jobDescription} onChange={(e) => setJobDescription(e.target.value)} placeholder="Paste a job description here…" className="input-base resize-y" /><div className="flex flex-wrap items-center justify-between gap-3"><label className="inline-flex cursor-pointer items-center rounded-lg border border-line px-3 py-2 text-sm font-medium text-ink-700 hover:bg-sage-50"><input type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" disabled={uploadingJd} className="sr-only" onChange={async (event) => { const file = event.currentTarget.files?.[0]; event.currentTarget.value = ""; if (!file) return; setUploadingJd(true); setError(null); try { const result = await api.extractInterviewJobDescription(file); setJobDescription(result.text); } catch (e) { setError(e instanceof ApiError ? e.message : "Could not read that job description file."); } finally { setUploadingJd(false); } }} />{uploadingJd ? "Reading file…" : "Upload PDF or DOCX"}</label><span className="text-xs text-ink-400">{jobDescription.length.toLocaleString()} / 20,000</span>{jobDescription && <button type="button" onClick={() => setJobDescription("")} className="text-xs font-semibold text-brand-700 hover:text-brand-800">Clear description</button>}</div></section>
            <section><div className="flex flex-wrap items-end justify-between gap-2"><div><p className="text-sm font-bold">Interview focus</p><p className="text-xs text-ink-400">Recommended mix for {domain}</p></div><button type="button" onClick={() => setFocus(DEFAULTS[domain])} className="text-xs font-semibold text-brand-700 transition-colors hover:text-brand-800">Reset to Recommended</button></div>
              <div className="mt-4 overflow-hidden rounded-full bg-sage-100" role="img" aria-label={`Focus distribution: ${AREAS.map(({ key, label }) => `${label} ${focus[key]} percent`).join(", ")}`}><div className="flex h-3 w-full">{AREAS.map(({ key, label }) => <div key={key} title={`${label}: ${focus[key]}%`} style={{ width: `${focus[key]}%`, backgroundColor: FOCUS_COLORS[key] }} />)}</div></div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">{AREAS.map(({ key, label }) => <span key={key} className="inline-flex items-center gap-1.5 text-2xs text-ink-500"><span className="h-2 w-2 rounded-full" style={{ backgroundColor: FOCUS_COLORS[key] }} />{label} {focus[key]}%</span>)}</div>
              <div className="mt-4 space-y-4">{AREAS.map(({ key, label }) => <label key={key} className="block rounded-xl border border-line bg-white px-4 py-3"><span className="flex items-center justify-between gap-3 text-sm font-medium text-ink-700"><span>{label}</span><span className="min-w-10 text-right font-semibold tabular-nums text-brand-700">{focus[key]}%</span></span><input aria-label={`${label} focus`} type="range" min={0} max={100} step={1} value={focus[key]} onChange={(e) => updateFocus(key, Number(e.target.value))} className={`focus-slider focus-slider-${key} mt-3 h-5 w-full cursor-pointer`} /></label>)}</div>
              <p className="mt-2 text-xs text-ink-400">Resume and project questions, along with role-specific cases and problem-solving, are included under Technical.</p></section>
            <section className="rounded-xl border border-line bg-surface-muted p-4"><label className="flex cursor-pointer items-start gap-3"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-1 h-4 w-4 accent-brand-600" /><span><span className="flex items-center gap-2 text-sm font-semibold text-ink-800"><Shield size={15} className="text-brand-600" />Allow camera/microphone integrity signals</span><span className="mt-1 block text-xs leading-relaxed text-ink-500">Optional and off by default. If enabled, camera/mic disconnection and hidden-tab signals may be recorded. Signals are indicators only, kept separate from your performance report.</span></span></label></section>
            {error && <p role="alert" className="rounded-xl border border-danger-500/25 bg-danger-50 p-3 text-sm text-danger-700">{error}</p>}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5"><p className="max-w-md text-xs leading-relaxed text-ink-500">Your completed answers will be evaluated. Ending early never lowers your score; very short sessions receive no unreliable score.</p><Button size="lg" icon={<Play size={17} />} loading={busy} onClick={start}>Start interview</Button></div>
          </div>
        </Card>
      </div>
      <div className="space-y-5"><Card className="p-5"><div className="flex items-center justify-between"><div><h3 className="flex items-center gap-2 font-bold"><History size={17} className="text-brand-600" />Previous interviews</h3><p className="mt-1 text-xs text-ink-500">Review saved transcripts and reports</p></div><button onClick={() => void reloadHistory()} className="text-xs font-semibold text-brand-700 hover:text-brand-800">Refresh</button></div>
          <div className="mt-4 space-y-2">{loading ? <p className="py-6 text-center text-sm text-ink-400">Loading interview history…</p> : history.length ? history.map((item) => <button key={item.id} onClick={() => showSession(item)} className="flex w-full items-center justify-between gap-3 rounded-xl border border-line p-3 text-left transition-colors hover:border-brand-200 hover:bg-brand-50/40"><span className="min-w-0"><span className="block truncate text-sm font-semibold text-ink-800">{item.domain}</span><span className="mt-1 block text-xs text-ink-400">{formatDate(item.started_at)} · {item.attempted_count} attempted</span></span><Badge tone={item.status === "completed" ? "brand" : "warn"}>{item.status === "completed" ? (item.report?.sufficient_data ? `${item.report.overall_score ?? "Report"}` : "Saved") : "Active"}</Badge></button>) : <div className="rounded-xl bg-surface-muted px-4 py-8 text-center"><History size={22} className="mx-auto text-sage-400" /><p className="mt-2 text-sm font-semibold text-ink-700">Your history starts here</p><p className="mt-1 text-xs text-ink-500">Completed interview reports will appear in this space.</p></div>}</div>
        </Card><Card className="p-5"><h3 className="flex items-center gap-2 text-sm font-bold"><AlertTriangle size={16} className="text-brand-600" />Designed for practice</h3><p className="mt-2 text-xs leading-relaxed text-ink-500">Questions adapt to your answers and profile. Your existing readiness scores remain unchanged; Arena insights are stored with each session.</p></Card></div>
    </div>
  </AppShell>;
}

function TranscriptTurn({ message }: { message: InterviewMessage }) {
  const student = message.role === "student";
  return <div className={`rounded-xl p-3.5 ${student ? "ml-5 bg-brand-50" : "mr-5 bg-surface-muted"}`}><div className="flex items-center justify-between gap-2"><p className="text-xs font-bold text-ink-700">{student ? "You" : message.persona ?? "Interviewer"}</p>{message.category && <Badge>{AREA_LABEL[message.category] ?? message.category}</Badge>}</div>{!student && <p className="mt-1.5 text-sm leading-relaxed text-ink-800">{message.text}</p>}{student && <><p className="mt-1.5 text-sm leading-relaxed text-ink-700">{message.text}</p>{message.evaluation && <div className="mt-3 border-t border-brand-100 pt-2.5"><p className="text-xs font-semibold text-brand-800">Answer feedback · {message.evaluation.score ?? "-"}/100</p><p className="mt-1 text-xs leading-relaxed text-ink-600">{message.evaluation.feedback}</p></div>}</>}</div>;
}

function ReportView({ item }: { item: InterviewSession }) {
  const report = item.report;
  const attempted = item.transcript.filter((m) => m.role === "student");
  if (!report?.sufficient_data) return <div className="mx-auto max-w-3xl space-y-5"><Card className="p-6"><div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 text-warn-600" /><div><h2 className="font-bold">Not enough data for a reliable score</h2><p className="mt-2 text-sm leading-relaxed text-ink-600">{report?.message ?? "This interview ended before enough responses were attempted to provide a reliable evaluation."}</p><p className="mt-2 text-xs text-ink-400">{attempted.length} response(s) saved · ending early was not penalized</p></div></div></Card><Card className="p-5"><h3 className="font-bold">Saved transcript</h3><div className="mt-3 space-y-3">{item.transcript.map((m, i) => <TranscriptTurn key={i} message={m} />)}</div></Card><Integrity item={item} /></div>;
  const score = typeof report.overall_score === "number" ? report.overall_score : null;
  const categories = report.category_scores && typeof report.category_scores === "object" ? Object.entries(report.category_scores) : [];
  const qFeedback = Array.isArray(report.question_feedback) ? report.question_feedback : attempted.map((m) => ({ question: m.question, answer: m.text, ...m.evaluation }));
  const lists: [string, any[]][] = [["Strengths", report.strengths], ["Areas to improve", report.weaknesses ?? report.improvement_areas], ["Role-specific skill gaps", report.skill_gaps], ["Preparation recommendations", report.preparation_recommendations]];
  return <div className="space-y-5"><Card className="p-6"><div className="flex flex-wrap items-center gap-6"><div className="grid h-28 w-28 place-items-center rounded-full border-[8px] border-brand-100 bg-brand-50"><div className="text-center"><p className="font-display text-3xl font-extrabold text-forest-800">{score ?? "—"}</p><p className="text-2xs text-ink-500">out of 100</p></div></div><div className="min-w-[200px] flex-1"><Badge tone="brand">{item.domain}</Badge><h2 className="mt-2 text-xl font-bold">Interview performance</h2><p className="mt-1 text-sm text-ink-500">Based on {report.attempted_count ?? attempted.length} attempted response(s). Ending early is not penalized.</p><p className="mt-2 text-xs text-ink-400">{formatDate(item.started_at)} · {item.personas.join(" · ")}</p></div></div>{categories.length >= 3 && <div className="mt-6 rounded-xl border border-line p-3"><p className="text-xs font-bold text-ink-500">Skill profile</p><SkillRadar height={260} data={categories.map(([k, v]) => ({ label: AREA_LABEL[k] ?? k.replaceAll("_", " "), value: Number(typeof v === "object" ? (v as any).score ?? 0 : v) || 0 }))} /></div>}{categories.length > 0 && <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{categories.map(([key, value]) => <div key={key} className="rounded-xl bg-surface-muted p-3"><p className="text-xs text-ink-500">{AREA_LABEL[key] ?? key.replaceAll("_", " ")}</p><p className="mt-1 text-xl font-bold text-ink-900">{typeof value === "object" ? (value as any).score ?? "—" : value}<span className="ml-1 text-xs font-medium text-ink-400">/100</span></p></div>)}</div>}{report.report_note && <p className="mt-4 rounded-lg bg-surface-muted p-3 text-xs leading-relaxed text-ink-500">{report.report_note}</p>}</Card>
    <div className="grid gap-5 lg:grid-cols-2">{lists.map(([title, entries]) => <Card key={title} className="p-5"><h3 className="font-bold">{title}</h3>{Array.isArray(entries) && entries.length ? <ul className="mt-3 space-y-2">{entries.map((entry, i) => <li key={i} className="flex gap-2 text-sm leading-relaxed text-ink-600"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />{typeof entry === "string" ? entry : entry.recommendation ?? entry.skill ?? JSON.stringify(entry)}</li>)}</ul> : <p className="mt-2 text-xs text-ink-400">No observations were returned for this area.</p>}</Card>)}</div>
    {(report as any).communication ? <CommunicationReport data={(report as any).communication as Communication} /> : null}
    <Card className="p-5"><h3 className="font-bold">Question-by-question feedback</h3><div className="mt-4 space-y-3">{qFeedback.map((q: any, i: number) => <details key={i} className="rounded-xl border border-line p-4" open={i === 0}><summary className="cursor-pointer list-none"><span className="mr-2 text-xs font-bold text-brand-700">Q{i + 1}</span><span className="text-sm font-semibold text-ink-800">{q.question ?? "Interview question"}</span>{typeof q.score === "number" && <Badge className="ml-2">{q.score}/100</Badge>}</summary><div className="mt-3 space-y-2 text-sm"><p className="text-xs font-semibold text-ink-500">Your answer</p><p className="whitespace-pre-wrap text-ink-600">{q.answer ?? "No answer text available."}</p>{q.feedback && <p className="leading-relaxed text-ink-700"><b>Feedback:</b> {q.feedback}</p>}{q.strengths?.length > 0 && <p className="text-ink-600"><b>Strengths:</b> {q.strengths.join(" · ")}</p>}{q.improvements?.length > 0 && <p className="text-ink-600"><b>Improve:</b> {q.improvements.join(" · ")}</p>}{q.better_answer && <p className="whitespace-pre-wrap leading-relaxed text-ink-600"><b>Suggested answer:</b> {q.better_answer}</p>}{q.explanation && <p className="leading-relaxed text-ink-600"><b>Why:</b> {q.explanation}</p>}</div></details>)}</div></Card><Integrity item={item} /></div>;
}

function Integrity({ item }: { item: InterviewSession }) {
  const signals = item.integrity_signals ?? [];
  return <Card className="p-5"><h3 className="flex items-center gap-2 font-bold"><Shield size={17} className="text-ink-500" />Integrity signals · separate from performance</h3><p className="mt-1 text-xs text-ink-500">These technical signals are indicators only and are not proof of misconduct.</p>{signals.length ? <ul className="mt-3 space-y-2">{signals.map((s, i) => <li key={i} className="flex items-center justify-between gap-2 rounded-lg bg-surface-muted px-3 py-2 text-xs"><span>{s.type.replaceAll("_", " ")}{s.detail ? ` · ${s.detail}` : ""}</span><span className="shrink-0 text-ink-400">{formatDate(s.at)}</span></li>)}</ul> : <p className="mt-3 text-xs text-ink-400">No integrity signals recorded.</p>}</Card>;
}
