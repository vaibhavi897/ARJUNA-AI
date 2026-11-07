"""Supabase Storage client for private interview recordings.

Only the backend talks to Supabase Storage. The service-role key never leaves
the server, and the bucket is private: the browser is handed a short-lived
signed URL instead of the object itself.

Uses the Storage REST API over ``httpx``, which the project already depends on,
so there is no new package to install.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

TIMEOUT = 120.0


class StorageUnavailable(RuntimeError):
    """Storage not configured or failing. The message is safe to show the user."""


def is_configured() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)


def _base() -> str:
    return (settings.SUPABASE_URL or "").rstrip("/")


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    key = settings.SUPABASE_SERVICE_ROLE_KEY or ""
    headers = {"Authorization": f"Bearer {key}", "apikey": key}
    if extra:
        headers.update(extra)
    return headers


def _require() -> None:
    if not is_configured():
        raise StorageUnavailable("Recording storage is not configured on this server.")


def _fail(action: str, response: httpx.Response) -> StorageUnavailable:
    """Turn a Supabase error into something an operator can act on.

    Supabase wraps storage errors in HTTP 400 with the real status inside the
    body, so the nested code matters more than ``response.status_code``.
    """
    logger.warning("Supabase storage %s failed: HTTP %s %s", action, response.status_code, response.text[:300])
    body: dict[str, object] = {}
    try:
        parsed = response.json()
        if isinstance(parsed, dict):
            body = parsed
    except ValueError:
        pass
    inner = str(body.get("statusCode") or response.status_code)
    message = str(body.get("message") or "")

    if "row-level security" in message.lower():
        return StorageUnavailable(
            "Supabase refused the upload under row-level security. The server is using a publishable "
            "key; set SUPABASE_SERVICE_ROLE_KEY to the project's secret key (sb_secret_...)."
        )
    if inner in ("401", "403") or response.status_code in (401, 403):
        return StorageUnavailable("The storage service rejected the server's credentials.")
    if inner == "404" or response.status_code == 404:
        return StorageUnavailable(
            f"The bucket '{settings.SUPABASE_RECORDINGS_BUCKET}' was not found. Create it in Supabase Storage."
        )
    if inner == "413" or response.status_code == 413:
        return StorageUnavailable("That recording is too large for the storage service.")
    return StorageUnavailable(f"The storage service returned an error{': ' + message if message else ''}.")


def upload(path: str, data: bytes, content_type: str = "video/webm") -> str:
    """Upload (or replace) an object and return its storage path."""
    _require()
    bucket = settings.SUPABASE_RECORDINGS_BUCKET
    url = f"{_base()}/storage/v1/object/{bucket}/{path}"
    headers = _headers({"Content-Type": content_type, "x-upsert": "true", "cache-control": "3600"})
    try:
        r = httpx.post(url, content=data, headers=headers, timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        logger.warning("Supabase upload transport error: %s", type(exc).__name__)
        raise StorageUnavailable("Could not reach the storage service. Please try again.") from exc
    if r.status_code >= 400:
        raise _fail("upload", r)
    return path


def signed_url(path: str, expires_in: int | None = None) -> str:
    """Return a time-limited URL the browser can stream the object from."""
    _require()
    bucket = settings.SUPABASE_RECORDINGS_BUCKET
    ttl = expires_in or settings.RECORDING_SIGNED_URL_TTL
    url = f"{_base()}/storage/v1/object/sign/{bucket}/{path}"
    try:
        r = httpx.post(url, json={"expiresIn": ttl}, headers=_headers(), timeout=30)
    except httpx.HTTPError as exc:
        raise StorageUnavailable("Could not reach the storage service. Please try again.") from exc
    if r.status_code >= 400:
        raise _fail("sign", r)
    try:
        signed = r.json().get("signedURL") or r.json().get("signedUrl")
    except ValueError:
        signed = None
    if not isinstance(signed, str) or not signed:
        raise StorageUnavailable("The storage service did not return a playable link.")
    # the API answers with a path relative to /storage/v1
    return signed if signed.startswith("http") else f"{_base()}/storage/v1{signed if signed.startswith('/') else '/' + signed}"


def delete(path: str) -> bool:
    """Remove an object. Returns False instead of raising when it cannot be removed."""
    if not is_configured():
        return False
    bucket = settings.SUPABASE_RECORDINGS_BUCKET
    url = f"{_base()}/storage/v1/object/{bucket}/{path}"
    try:
        r = httpx.request("DELETE", url, headers=_headers(), timeout=30)
    except httpx.HTTPError:
        return False
    if r.status_code >= 400:
        logger.warning("Supabase delete failed for %s: HTTP %s", path, r.status_code)
        return False
    return True
