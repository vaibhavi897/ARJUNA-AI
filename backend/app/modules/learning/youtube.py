"""YouTube import: metadata via oEmbed, captions via youtube-transcript-api.

Transcripts are NOT assumed to exist. When captions are unavailable the learner
is told so and can paste their own transcript instead.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from app.core.logging_config import get_logger

logger = get_logger(__name__)
ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def parse_video_id(url: str) -> str | None:
    url = (url or "").strip()
    if ID_RE.match(url):
        return url
    try:
        u = urlparse(url if "://" in url else f"https://{url}")
    except ValueError:
        return None
    host = (u.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if host == "youtu.be":
        vid = u.path.strip("/").split("/")[0]
    elif host in ("youtube.com", "music.youtube.com", "youtube-nocookie.com"):
        if u.path == "/watch":
            vid = parse_qs(u.query).get("v", [""])[0]
        else:
            m = re.match(r"^/(shorts|embed|live|v)/([^/?]+)", u.path)
            vid = m.group(2) if m else ""
    else:
        return None
    return vid if ID_RE.match(vid or "") else None


def fetch_metadata(video_id: str) -> dict[str, Any]:
    try:
        r = httpx.get("https://www.youtube.com/oembed", params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"}, timeout=12)
        if r.status_code == 200:
            d = r.json()
            return {"title": d.get("title"), "channel": d.get("author_name"), "thumbnail": d.get("thumbnail_url")}
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("oembed failed: %s", exc)
    return {"title": None, "channel": None, "thumbnail": None}


def fetch_transcript(video_id: str) -> tuple[str, list[dict[str, Any]], str | None]:
    """Return (status, segments, reason). status is 'available' or 'unavailable'."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        fetched = YouTubeTranscriptApi().fetch(video_id, languages=["en", "en-IN", "en-US", "en-GB", "hi"])
        segs = [{"start": float(s.start), "text": s.text.replace("\n", " ").strip()} for s in fetched if s.text.strip()]
        if not segs:
            return "unavailable", [], "The video has no caption text."
        return "available", segs, None
    except ImportError:
        return "unavailable", [], "Transcript support is not installed on the server."
    except Exception as exc:  # noqa: BLE001 - the library raises many specific errors
        name = type(exc).__name__
        reason = {
            "TranscriptsDisabled": "The uploader has disabled captions for this video.",
            "NoTranscriptFound": "No English captions were found for this video.",
            "VideoUnavailable": "This video is unavailable (private, removed or region-locked).",
            "IpBlocked": "YouTube is blocking transcript requests from this server right now.",
            "RequestBlocked": "YouTube is blocking transcript requests from this server right now.",
        }.get(name, "Captions could not be retrieved for this video.")
        logger.info("transcript unavailable for %s: %s", video_id, name)
        return "unavailable", [], reason


TS = re.compile(r"^\s*\[?(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\]?\s*[-:]?\s*(.*)$")


def parse_pasted(text: str) -> list[dict[str, Any]]:
    """Accept timestamped lines ('12:30 text' / '[01:02:03] text') or plain prose."""
    segs: list[dict[str, Any]] = []
    plain: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = TS.match(line)
        if m and m.group(4):
            h, mnt, sec = int(m.group(1) or 0), int(m.group(2)), int(m.group(3))
            segs.append({"start": float(h * 3600 + mnt * 60 + sec), "text": m.group(4)})
        else:
            plain.append(line)
    if segs:
        return segs
    words = " ".join(plain).split()
    return [{"start": float(i // 150 * 60), "text": " ".join(words[i : i + 150])} for i in range(0, len(words), 150)]


def to_prompt_text(segments: list[dict[str, Any]], chunk_seconds: int = 20) -> str:
    """Compact transcript for the model: merge lines into ~20s chunks tagged with seconds."""
    out: list[str] = []
    cur_start, buf = None, []
    for s in segments:
        if cur_start is None:
            cur_start = s["start"]
        buf.append(s["text"])
        if s["start"] - cur_start >= chunk_seconds:
            out.append(f"[{int(cur_start)}] {' '.join(buf)}")
            cur_start, buf = None, []
    if buf:
        out.append(f"[{int(cur_start or 0)}] {' '.join(buf)}")
    return "\n".join(out)
