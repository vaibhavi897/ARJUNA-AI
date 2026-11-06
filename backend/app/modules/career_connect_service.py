"""Permitted, server-side discovery adapters for Career Connect."""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

import httpx

from app.core.config import settings

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
JOB_HOSTS = {"linkedin.com": "LinkedIn", "naukri.com": "Naukri", "indeed.com": "Indeed", "internshala.com": "Internshala", "foundit.in": "Foundit"}


def safe_linkedin_profile(url: str) -> str | None:
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    if host not in {"linkedin.com", "m.linkedin.com"} or not re.fullmatch(r"/in/[\w%-]+", path, re.I):
        return None
    return f"https://www.linkedin.com{path}"


def source_for_url(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    for domain, name in JOB_HOSTS.items():
        if host == domain or host.endswith("." + domain):
            return name
    return "Company careers"


def _brave(query: str, count: int = 20) -> list[dict]:
    if not settings.BRAVE_SEARCH_API_KEY:
        return []
    response = httpx.get(BRAVE_URL, params={"q": query, "count": count}, headers={"X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY, "Accept": "application/json"}, timeout=15)
    response.raise_for_status()
    return response.json().get("web", {}).get("results", [])


def search_people(company: str, designation: str, department: str, location: str) -> dict:
    configured = bool(settings.BRAVE_SEARCH_API_KEY)
    query = " ".join(x for x in ["site:linkedin.com/in", company, designation, department, location] if x)
    rows = []
    if configured:
        for item in _brave(query):
            url = safe_linkedin_profile(item.get("url", ""))
            if not url:
                continue
            title = re.sub(r"\s*\|\s*LinkedIn\s*$", "", item.get("title", ""), flags=re.I)
            rows.append({"profile_url": url, "name": title.split(" - ")[0][:200] or None, "designation": title[:200] or None, "company": company or None, "location": location or None, "preview": item.get("description", "")[:500], "source": "Brave public web index"})
    return {"results": rows, "providers": {"brave": configured}, "message": None if configured else "Public profile discovery is unavailable until BRAVE_SEARCH_API_KEY is configured. CSV import remains available."}


def search_jobs(role: str, company: str, location: str, employment_type: str) -> dict:
    brave_ready = bool(settings.BRAVE_SEARCH_API_KEY)
    adzuna_ready = bool(settings.ADZUNA_APP_ID and settings.ADZUNA_APP_KEY)
    grouped: dict[str, dict] = {}
    if adzuna_ready and role:
        params = {"app_id": settings.ADZUNA_APP_ID, "app_key": settings.ADZUNA_APP_KEY, "what": " ".join(x for x in (role, company) if x), "where": location, "results_per_page": 20, "content-type": "application/json"}
        if employment_type.lower() in {"full-time", "full time"}: params["full_time"] = 1
        if employment_type.lower() in {"part-time", "part time"}: params["part_time"] = 1
        response = httpx.get("https://api.adzuna.com/v1/api/jobs/in/search/1", params=params, timeout=15)
        response.raise_for_status()
        for item in response.json().get("results", []):
            url = item.get("redirect_url")
            if not url:
                continue
            title = item.get("title", "")[:300]
            company_name = (item.get("company") or {}).get("display_name")
            place = (item.get("location") or {}).get("display_name")
            key = hashlib.sha256((re.sub(r"\W+", " ", title.lower()) + "|" + str(company_name).lower() + "|" + str(place).lower()).encode()).hexdigest()
            row = grouped.setdefault(key, {"external_key": key, "title": title, "company": company_name, "location": place, "experience": None, "employment_type": employment_type or None, "description": item.get("description", "")[:1500], "sources": []})
            row["sources"].append({"name": "Adzuna", "url": url})
    if brave_ready:
        terms = [role, company, location, employment_type]
        query = " ".join(x for x in terms if x) + " (site:linkedin.com/jobs OR site:naukri.com OR site:indeed.com OR site:internshala.com OR site:foundit.in OR careers)"
        for item in _brave(query):
            url = item.get("url", "")
            if not url.startswith("https://"):
                continue
            source = source_for_url(url)
            title = item.get("title", "")[:300]
            desc = item.get("description", "")[:1500]
            # Search snippets do not reliably expose structured employer/location fields;
            # preserve the real title and URL without guessing missing values.
            key = hashlib.sha256((re.sub(r"\W+", " ", title.lower()) + "|" + urlparse(url).hostname).encode()).hexdigest()
            grouped[key] = {"external_key": key, "title": title, "company": None, "location": None, "experience": None, "employment_type": None, "description": desc, "sources": [{"name": source, "url": url}]}
    return {"results": list(grouped.values()), "providers": {"brave": brave_ready, "adzuna": adzuna_ready}, "message": None if brave_ready or adzuna_ready else "Live job search needs BRAVE_SEARCH_API_KEY and/or ADZUNA_APP_ID plus ADZUNA_APP_KEY in the backend environment. No listings are fabricated."}
