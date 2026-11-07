/**
 * Records the interview from the stream the Arena already opened.
 *
 *  - pieces are posted to the backend every few seconds, so a closed tab or a
 *    crash loses seconds rather than the whole session;
 *  - the backend buffers them and uploads one WebM to private storage at the end;
 *  - entirely optional: when the server reports recording as disabled, or the
 *    browser cannot record, nothing happens and the interview is unaffected.
 */
import { request } from "./api";

/** Keep an hour of interview well inside the server's size ceiling. */
const VIDEO_BITS_PER_SECOND = 600_000;
const AUDIO_BITS_PER_SECOND = 32_000;
const CHUNK_MS = 5_000;

/** First container the browser actually supports. */
function pickMimeType(): string | null {
  const candidates = [
    "video/webm;codecs=vp9,opus",
    "video/webm;codecs=vp8,opus",
    "video/webm",
  ];
  if (typeof MediaRecorder === "undefined") return null;
  return candidates.find((t) => MediaRecorder.isTypeSupported(t)) ?? null;
}

export function recordingSupported(): boolean {
  return pickMimeType() !== null;
}

export class InterviewRecorder {
  private recorder: MediaRecorder | null = null;
  private queue: Promise<void> = Promise.resolve();
  private startedAt = 0;
  private failed = false;

  constructor(private sessionId: number) {}

  /** Returns false when this browser cannot record; the caller just carries on. */
  start(stream: MediaStream): boolean {
    const mimeType = pickMimeType();
    if (!mimeType) return false;
    try {
      const recorder = new MediaRecorder(stream, {
        mimeType,
        videoBitsPerSecond: VIDEO_BITS_PER_SECOND,
        audioBitsPerSecond: AUDIO_BITS_PER_SECOND,
      });
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) this.enqueue(e.data);
      };
      recorder.onerror = () => {
        this.failed = true;
      };
      recorder.start(CHUNK_MS);
      this.recorder = recorder;
      this.startedAt = Date.now();
      return true;
    } catch {
      return false;
    }
  }

  /** Upload chunks strictly in order — the server appends them to one file. */
  private enqueue(blob: Blob) {
    this.queue = this.queue
      .then(async () => {
        if (this.failed) return;
        const buffer = await blob.arrayBuffer();
        await request<{ buffered_bytes: number }>(`/interviews/${this.sessionId}/recording/chunk`, {
          method: "POST",
          rawBody: buffer,
          contentType: "application/octet-stream",
        });
      })
      .catch(() => {
        // One failed chunk would corrupt the file, so stop trying and let the
        // interview continue without a recording.
        this.failed = true;
      });
  }

  /** Elapsed recording time in seconds. */
  get seconds(): number {
    return this.startedAt ? Math.round((Date.now() - this.startedAt) / 1000) : 0;
  }

  get broken(): boolean {
    return this.failed;
  }

  /** Flush the last chunk and wait for every upload to land. */
  async stop(): Promise<{ ok: boolean; seconds: number }> {
    const seconds = this.seconds;
    const recorder = this.recorder;
    this.recorder = null;
    if (!recorder) return { ok: false, seconds };

    await new Promise<void>((resolve) => {
      recorder.onstop = () => resolve();
      try {
        if (recorder.state !== "inactive") recorder.stop();
        else resolve();
      } catch {
        resolve();
      }
    });

    await this.queue;
    return { ok: !this.failed, seconds };
  }
}
