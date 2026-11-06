/** Live microphone waveform (wavesurfer.js). Renders only while `active`; never blocks the answer box if the mic is unavailable. */
import { useEffect, useRef } from "react";
import WaveSurfer from "wavesurfer.js";
import RecordPlugin from "wavesurfer.js/dist/plugins/record.esm.js";

export default function Waveform({ active, height = 56 }: { active: boolean; height?: number }) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!active || !box.current) return;
    let ws: WaveSurfer | null = null, rec: ReturnType<typeof RecordPlugin.create> | null = null, dead = false;
    try {
      ws = WaveSurfer.create({ container: box.current, height, waveColor: "#2D9A68", progressColor: "#187C4F", barWidth: 3, barGap: 2, barRadius: 3, interact: false, cursorWidth: 0 });
      rec = ws.registerPlugin(RecordPlugin.create({ renderRecordedAudio: false, scrollingWaveform: true, scrollingWaveformWindow: 8 }));
      rec.startMic().catch(() => undefined);
    } catch { /* decorative: ignore */ }
    return () => { dead = true; try { rec?.stopMic(); ws?.destroy(); } catch { /* already gone */ } void dead; };
  }, [active, height]);
  if (!active) return null;
  return <div ref={box} aria-hidden className="mt-3 overflow-hidden rounded-xl border border-brand-200 bg-brand-50/50 px-2 py-1" />;
}
