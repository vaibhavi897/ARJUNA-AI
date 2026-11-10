/**
 * Plays back an interview recording inside the report.
 *
 * The bucket is private, so the player asks the backend for a short-lived
 * signed URL only when the student chooses to watch. Nothing is requested, and
 * no control is shown, when the session has no recording.
 */
import { useCallback, useState } from "react";
import { Film, Loader2, Play, Trash2 } from "lucide-react";
import { Button, Card } from "./ui";
import { api, ApiError, type InterviewRecording } from "../lib/api";

function prettyBytes(n: number | null): string {
  if (!n) return "";
  const mb = n / 1024 / 1024;
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.round(n / 1024)} KB`;
}

function prettyDuration(s: number | null): string {
  if (!s) return "";
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return m ? `${m} min ${sec}s` : `${sec}s`;
}

function prettyExpiry(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const days = Math.ceil((d.getTime() - Date.now()) / 86_400_000);
  if (days <= 0) return "expires today";
  return `kept until ${d.toLocaleDateString()} (${days} day${days === 1 ? "" : "s"})`;
}

export function RecordingPlayer({
  sessionId,
  recording,
  onDeleted,
}: {
  sessionId: number;
  recording: InterviewRecording | undefined;
  onDeleted?: () => void;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [removed, setRemoved] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.recordingUrl(sessionId);
      setUrl(data.url);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load the recording.");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const remove = useCallback(async () => {
    if (!window.confirm("Delete this recording permanently? The rest of the report is kept.")) return;
    setLoading(true);
    try {
      await api.recordingDelete(sessionId);
      setUrl(null);
      setRemoved(true);
      onDeleted?.();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not delete the recording.");
    } finally {
      setLoading(false);
    }
  }, [sessionId, onDeleted]);

  if (!recording?.available || removed) return null;

  const meta = [prettyDuration(recording.seconds), prettyBytes(recording.bytes), prettyExpiry(recording.expires_at)]
    .filter(Boolean)
    .join(" · ");

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-2 font-bold">
            <Film size={17} className="text-ink-500" />
            Interview recording
          </h3>
          <p className="mt-1 text-xs text-ink-500">{meta || "Saved with this session."}</p>
        </div>
        <div className="flex gap-2">
          {!url ? (
            <Button size="sm" icon={loading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />} disabled={loading} onClick={load}>
              Watch recording
            </Button>
          ) : null}
          <Button size="sm" variant="outline" icon={<Trash2 size={14} />} disabled={loading} onClick={remove}>
            Delete
          </Button>
        </div>
      </div>

      {error ? <p className="mt-3 text-xs font-medium text-danger-500">{error}</p> : null}

      {url ? (
        <video
          src={url}
          controls
          playsInline
          preload="metadata"
          className="mt-4 aspect-video w-full rounded-xl bg-forest-900"
        />
      ) : null}
    </Card>
  );
}
