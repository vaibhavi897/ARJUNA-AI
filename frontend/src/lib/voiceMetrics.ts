/**
 * Measures HOW an answer was spoken (pace, pauses, volume steadiness) while the candidate dictates.
 * Audio never leaves the browser: only these few numbers are sent with the answer.
 */
export type VoiceMetrics = { spoken: boolean; words: number; spoken_seconds: number; total_seconds: number; long_pauses: number; volume_mean: number | null; volume_cv: number | null };

const FRAME_MS = 100;
const VOICED = 0.012;      // RMS above this counts as speech
const LONG_PAUSE_MS = 1500;

export class VoiceMeter {
  private ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private timer: number | null = null;
  private frames = 0; private voiced = 0; private silentRun = 0; private pauses = 0; private seenSpeech = false;
  private sum = 0; private sumSq = 0; words = 0;

  async start(): Promise<void> {
    if (this.timer !== null) return;
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      const Ctx = window.AudioContext || (window as any).webkitAudioContext;
      this.ctx = new Ctx();
      const src = this.ctx.createMediaStreamSource(this.stream);
      const an = this.ctx.createAnalyser();
      an.fftSize = 1024;
      src.connect(an);
      const buf = new Float32Array(an.fftSize);
      this.timer = window.setInterval(() => {
        an.getFloatTimeDomainData(buf);
        let s = 0;
        for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i];
        const rms = Math.sqrt(s / buf.length);
        this.frames++;
        if (rms > VOICED) {
          this.voiced++; this.sum += rms; this.sumSq += rms * rms; this.seenSpeech = true; this.silentRun = 0;
        } else if (this.seenSpeech) {
          this.silentRun++;
          if (this.silentRun * FRAME_MS === LONG_PAUSE_MS) this.pauses++;
        }
      }, FRAME_MS);
    } catch { /* microphone unavailable: delivery metrics simply stay empty */ }
  }

  pause(): void {
    if (this.timer !== null) { clearInterval(this.timer); this.timer = null; }
    this.stream?.getTracks().forEach((t) => t.stop()); this.stream = null;
    void this.ctx?.close().catch(() => undefined); this.ctx = null;
    this.silentRun = 0;
  }

  addWords(text: string): void { this.words += (text.trim().match(/\S+/g) ?? []).length; }

  snapshot(): VoiceMetrics | null {
    if (!this.voiced || !this.words) return null;
    const mean = this.sum / this.voiced;
    const variance = Math.max(0, this.sumSq / this.voiced - mean * mean);
    return {
      spoken: true, words: this.words, spoken_seconds: +(this.voiced * FRAME_MS / 1000).toFixed(1), total_seconds: +(this.frames * FRAME_MS / 1000).toFixed(1),
      long_pauses: this.pauses, volume_mean: +mean.toFixed(4), volume_cv: mean ? +(Math.sqrt(variance) / mean).toFixed(3) : null,
    };
  }

  reset(): void { this.pause(); this.frames = 0; this.voiced = 0; this.silentRun = 0; this.pauses = 0; this.seenSpeech = false; this.sum = 0; this.sumSq = 0; this.words = 0; }
}
