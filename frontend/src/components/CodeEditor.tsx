/** Monaco code editor (loaded on demand) with a plain textarea fallback while loading or if it cannot load. */
import { lazy, Suspense } from "react";

const Monaco = lazy(() => import("@monaco-editor/react"));

function Fallback({ value, onChange, height }: { value: string; onChange: (v: string) => void; height: number }) {
  return <textarea value={value} onChange={(e) => onChange(e.target.value)} spellCheck={false} aria-label="Your code" style={{ height }} className="w-full rounded-xl bg-[#0F1B2D] p-4 font-mono text-[13px] leading-6 text-emerald-100 outline-none focus:ring-2 focus:ring-brand-400" />;
}

export default function CodeEditor({ value, onChange, language = "python", height = 320 }: { value: string; onChange: (v: string) => void; language?: string; height?: number }) {
  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-[#1e1e1e]" style={{ height }}>
      <Suspense fallback={<Fallback value={value} onChange={onChange} height={height} />}>
        <Monaco height={height} language={language} theme="vs-dark" value={value} loading={<Fallback value={value} onChange={onChange} height={height} />}
          onChange={(v) => onChange(v ?? "")}
          options={{ minimap: { enabled: false }, fontSize: 14, lineHeight: 22, tabSize: 4, insertSpaces: true, scrollBeyondLastLine: false, automaticLayout: true, padding: { top: 12 }, fontLigatures: true, smoothScrolling: true, cursorSmoothCaretAnimation: "on", renderLineHighlight: "all" }} />
      </Suspense>
    </div>
  );
}
