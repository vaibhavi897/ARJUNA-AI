"""External occupational data: O*NET, BLS and Adzuna (all optional).

Each client fails soft: when a key is missing or the service is down it
returns ``None`` so CareerVerse keeps working from the seeded dataset.
BLS figures are US labour-market data and are always labelled as such.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
TIMEOUT = httpx.Timeout(15.0, connect=8.0)

ONET_BASE = "https://services.onetcenter.org/ws/online/occupations"
BLS_V1 = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
BLS_V2 = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"

# OEWS datatype codes used in series ids.
OEWS_DATATYPES = {"employment": "01", "p10": "11", "median": "13", "p90": "15"}


# --------------------------------------------------------------------------- O*NET
def onet_enabled() -> bool:
    return bool(settings.ONET_USERNAME and settings.ONET_PASSWORD)


def _flatten(node: Any, keys: tuple[str, ...] = ("statement", "name", "title", "element_name")) -> list[str]:
    """Pull human-readable strings out of an O*NET JSON report defensively."""
    out: list[str] = []
    if isinstance(node, dict):
        for k in keys:
            if isinstance(node.get(k), str):
                out.append(node[k])
                break
        else:
            for v in node.values():
                out.extend(_flatten(v, keys))
    elif isinstance(node, list):
        for v in node:
            out.extend(_flatten(v, keys))
    return out


def fetch_onet_profile(onet_code: str) -> dict[str, Any] | None:
    """Tasks, skills, knowledge, work activities and abilities for one occupation."""
    if not onet_enabled() or not onet_code:
        return None
    reports = ["tasks", "skills", "knowledge", "work_activities", "abilities", "work_context"]
    profile: dict[str, Any] = {"onet_code": onet_code}
    auth = (settings.ONET_USERNAME, settings.ONET_PASSWORD)  # type: ignore[arg-type]
    try:
        with httpx.Client(timeout=TIMEOUT, auth=auth, headers={"Accept": "application/json"}) as client:
            for report in reports:
                resp = client.get(f"{ONET_BASE}/{onet_code}/summary/{report}")
                if resp.status_code == 200:
                    profile[report] = _flatten(resp.json())[:15]
                else:
                    logger.warning("O*NET %s %s -> HTTP %s", onet_code, report, resp.status_code)
    except httpx.HTTPError as exc:
        logger.warning("O*NET unavailable: %s", exc)
        return None
    return profile if len(profile) > 1 else None


# --------------------------------------------------------------------------- BLS
def _series_id(soc_code: str, datatype: str) -> str:
    # OE + U + N(national) + area 0000000 + industry 000000 + SOC(6) + datatype(2)
    return f"OEUN0000000000000{soc_code.replace('-', '')}{datatype}"


def fetch_bls_oews(soc_codes: list[str]) -> dict[str, dict[str, Any]]:
    """National US wage percentiles and employment keyed by SOC code.

    Returns ``{soc: {"median": 123, "p10": .., "p90": .., "employment": .., "year": 2024}}``.
    Works keyless (BLS v1, low daily quota) or with BLS_API_KEY (v2).
    """
    wanted = sorted({s for s in soc_codes if s})
    if not wanted:
        return {}
    series_ids = [_series_id(s, dt) for s in wanted for dt in OEWS_DATATYPES.values()]
    url = BLS_V2 if settings.BLS_API_KEY else BLS_V1
    results: dict[str, dict[str, Any]] = {}
    inverse = {v: k for k, v in OEWS_DATATYPES.items()}
    year_now = time.gmtime().tm_year
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            for i in range(0, len(series_ids), 25 if not settings.BLS_API_KEY else 50):
                batch = series_ids[i : i + (25 if not settings.BLS_API_KEY else 50)]
                body: dict[str, Any] = {"seriesid": batch, "startyear": str(year_now - 4), "endyear": str(year_now)}
                if settings.BLS_API_KEY:
                    body["registrationkey"] = settings.BLS_API_KEY
                resp = client.post(url, json=body)
                payload = resp.json()
                if payload.get("status") != "REQUEST_SUCCEEDED":
                    logger.warning("BLS: %s", "; ".join(payload.get("message", [])) or payload.get("status"))
                    if not payload.get("Results"):
                        continue
                for series in payload.get("Results", {}).get("series", []):
                    sid = series["seriesID"]
                    soc = f"{sid[17:19]}-{sid[19:23]}"
                    kind = inverse.get(sid[-2:])
                    data = [d for d in series.get("data", []) if d.get("value") not in (None, "-", "")]
                    if not kind or not data:
                        continue
                    latest = max(data, key=lambda d: d["year"])
                    try:
                        value = float(str(latest["value"]).replace(",", ""))
                    except ValueError:
                        continue
                    entry = results.setdefault(soc, {})
                    entry[kind] = value
                    entry["year"] = int(latest["year"])
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("BLS unavailable: %s", exc)
    return results


# --------------------------------------------------------------------------- Adzuna
_ADZUNA_CACHE: dict[tuple, tuple[float, dict[str, Any]]] = {}
ADZUNA_TTL = 6 * 3600


def adzuna_enabled() -> bool:
    return bool(settings.ADZUNA_APP_ID and settings.ADZUNA_APP_KEY)


def fetch_adzuna_jobs(title: str, country: str = "in", limit: int = 5) -> dict[str, Any] | None:
    """Live listings for a title. Cached; None when unconfigured or unavailable."""
    if not adzuna_enabled():
        return None
    key = (title.lower(), country, limit)
    hit = _ADZUNA_CACHE.get(key)
    if hit and time.time() - hit[0] < ADZUNA_TTL:
        return hit[1]
    try:
        resp = httpx.get(
            f"{ADZUNA_BASE}/{country}/search/1",
            params={"app_id": settings.ADZUNA_APP_ID, "app_key": settings.ADZUNA_APP_KEY, "what": title, "results_per_page": limit, "content-type": "application/json"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        raw = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Adzuna unavailable: %s", exc)
        return None
    data = {
        "total": raw.get("count"),
        "country": country,
        "listings": [
            {
                "title": j.get("title"),
                "company": (j.get("company") or {}).get("display_name"),
                "location": (j.get("location") or {}).get("display_name"),
                "url": j.get("redirect_url"),
                "salary_min": j.get("salary_min"),
                "salary_max": j.get("salary_max"),
                "salary_is_predicted": j.get("salary_is_predicted"),
            }
            for j in raw.get("results", [])
        ],
        "attribution": "Job data from Adzuna",
    }
    _ADZUNA_CACHE[key] = (time.time(), data)
    return data
