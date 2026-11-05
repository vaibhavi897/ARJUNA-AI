"""Deterministic resume parsing.

This is heuristic text analysis, not a trained model. It segments the resume
into sections, then pulls candidate skills, education, projects, experience,
certifications and achievements out of each. Output is always presented to the
student for review before anything is merged into their profile.
"""

from __future__ import annotations

import re
from typing import Any

SECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "summary": re.compile(r"^\s*(professional\s+)?(summary|objective|profile|about\s+me)\s*:?\s*$", re.I),
    "education": re.compile(r"^\s*(education|academics?|academic\s+(background|qualifications?)|educational\s+qualifications?)\s*:?\s*$", re.I),
    "skills": re.compile(r"^\s*(technical\s+)?(skills?|core\s+competenc(y|ies)|technologies|technical\s+expertise)\s*:?\s*$", re.I),
    "projects": re.compile(r"^\s*(academic\s+|key\s+|personal\s+)?projects?\s*:?\s*$", re.I),
    "experience": re.compile(r"^\s*(work\s+)?(experience|employment|internships?|professional\s+experience|work\s+history)\s*:?\s*$", re.I),
    "certifications": re.compile(r"^\s*(certifications?|licenses?|courses?|certificates?)\s*:?\s*$", re.I),
    "achievements": re.compile(r"^\s*(achievements?|awards?|honors?|honours?|accomplishments?|extra[\s-]?curricular.*)\s*:?\s*$", re.I),
    "positions": re.compile(r"^\s*(positions?\s+of\s+responsibility|leadership|volunteer.*)\s*:?\s*$", re.I),
    "contact": re.compile(r"^\s*(contact|personal\s+details?)\s*:?\s*$", re.I),
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:(?:\+|00)\d{1,3}[\s-]?)?(?:\(?\d{2,5}\)?[\s-]?)?\d{3}[\s-]?\d{4}\b")
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_.-]+/?", re.I)
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_%.-]+/?", re.I)
URL_RE = re.compile(r"https?://[^\s,;)]+", re.I)
CGPA_RE = re.compile(r"(?:cgpa|gpa|cpi|sgpa)\s*[:\-]?\s*(\d{1,2}(?:\.\d{1,2})?)\s*(?:/\s*(\d{1,2}))?", re.I)
PERCENT_RE = re.compile(r"(\d{2,3}(?:\.\d{1,2})?)\s*%")
YEAR_RE = re.compile(r"(19|20)\d{2}")
GRAD_YEAR_RE = re.compile(r"(?:expected\s+)?(?:graduation|batch|class\s+of)\s*[:\-]?\s*((?:19|20)\d{2})", re.I)
DURATION_RE = re.compile(
    r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*,?\s*(?:19|20)\d{2})"
    r"\s*(?:-|–|—|to)\s*"
    r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*,?\s*(?:19|20)\d{2}|present|current|ongoing)",
    re.I,
)
BULLET_RE = re.compile(r"^\s*(?:[-*•●▪‣⁃>]|\d+[.)])\s*")

DEGREE_RE = re.compile(
    r"\b(b\.?\s?tech|b\.?\s?e\.?|b\.?\s?sc|bca|b\.?\s?com|bba|b\.?\s?a\.?|"
    r"m\.?\s?tech|m\.?\s?e\.?|m\.?\s?sc|mca|m\.?\s?com|mba|m\.?\s?a\.?|"
    r"ph\.?\s?d|bachelor[s]?|master[s]?|diploma)\b",
    re.I,
)
INSTITUTION_HINT_RE = re.compile(
    r"\b(institute|university|college|school|academy|iit|nit|iiit|bits|vit|srm|ies)\b", re.I
)
COMPANY_SUFFIX_RE = re.compile(
    r"\b(pvt|private|limited|ltd|llp|inc|corp|technologies|solutions|systems|labs|consulting|capital|bank|partners|group|services)\b",
    re.I,
)

ROLE_TITLE_HINT_RE = re.compile(
    r"\b(intern|internship|analyst|engineer|developer|consultant|associate|trainee|"
    r"manager|scientist|researcher|lead|president|secretary|coordinator|head|volunteer)\b",
    re.I,
)

# Split a skills line on separators but keep multi-word skills intact.
SKILL_SPLIT_RE = re.compile(r"[,;|/•·•]|\s{2,}|\n")

ACTION_VERBS = (
    "built", "designed", "developed", "implemented", "led", "created", "analysed",
    "analyzed", "optimised", "optimized", "automated", "deployed", "improved",
    "reduced", "increased", "managed", "modelled", "modeled", "forecasted",
    "valued", "audited", "researched", "delivered", "launched", "migrated",
)

METRIC_RE = re.compile(r"(\d+(?:\.\d+)?\s*(?:%|percent|x|k|lakh|crore|million|bn|billion)|\$\s?\d)", re.I)

MAX_TEXT_CHARS = 120_000


def _lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.split("\n")]


def split_sections(text: str) -> dict[str, list[str]]:
    """Bucket the resume's lines under the headings it declares."""
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in _lines(text):
        stripped = line.strip()
        if not stripped:
            continue
        matched: str | None = None
        if len(stripped) <= 60:
            for name, pattern in SECTION_PATTERNS.items():
                if pattern.match(stripped):
                    matched = name
                    break
        if matched:
            current = matched
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(stripped)
    return sections


def _dedupe(values: list[str], limit: int | None = None) -> list[str]:
    seen: dict[str, str] = {}
    for value in values:
        cleaned = " ".join(value.split())
        if not cleaned:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen[key] = cleaned
    out = list(seen.values())
    return out[:limit] if limit else out


def extract_contact(text: str, sections: dict[str, list[str]]) -> dict[str, Any]:
    head = "\n".join(sections.get("header", [])[:12]) or text[:800]
    emails = EMAIL_RE.findall(text)
    phones = [p for p in PHONE_RE.findall(text[:2000]) if len(re.sub(r"\D", "", p)) >= 10]
    github = GITHUB_RE.search(text)
    linkedin = LINKEDIN_RE.search(text)

    name: str | None = None
    for line in sections.get("header", [])[:5]:
        candidate = line.strip()
        if EMAIL_RE.search(candidate) or URL_RE.search(candidate):
            continue
        words = candidate.split()
        if 1 < len(words) <= 5 and all(
            re.fullmatch(r"[A-Za-z.'-]+", word) for word in words
        ):
            name = " ".join(word.capitalize() if word.isupper() else word for word in words)
            break

    other_urls = [
        url
        for url in _dedupe(URL_RE.findall(text), 8)
        if "github.com" not in url.lower() and "linkedin.com" not in url.lower()
    ]

    return {
        "name": name,
        "email": emails[0].lower() if emails else None,
        "phone": phones[0].strip() if phones else None,
        "github_url": _normalise_url(github.group(0)) if github else None,
        "linkedin_url": _normalise_url(linkedin.group(0)) if linkedin else None,
        "other_urls": other_urls,
        "header_preview": head[:400],
    }


def _normalise_url(value: str) -> str:
    value = value.rstrip("/.,;)")
    if not value.lower().startswith("http"):
        value = "https://" + value
    return value


def extract_skills(sections: dict[str, list[str]], catalogue: dict[str, str]) -> dict[str, Any]:
    """Pull skills from the skills section, plus catalogue hits anywhere in the text.

    ``catalogue`` maps a lowercase skill name/alias -> canonical display name.
    """
    declared: list[str] = []
    for line in sections.get("skills", []):
        body = BULLET_RE.sub("", line)
        if ":" in body and len(body.split(":")[0]) < 40:
            body = body.split(":", 1)[1]
        for token in SKILL_SPLIT_RE.split(body):
            token = token.strip(" .-")
            if 1 < len(token) <= 60 and not token.isdigit():
                declared.append(token)

    full_text = " \n".join(
        line for block in sections.values() for line in block
    ).lower()

    catalogue_hits: list[str] = []
    for needle, canonical in catalogue.items():
        if len(needle) < 2:
            continue
        pattern = r"(?<![a-z0-9+#])" + re.escape(needle) + r"(?![a-z0-9+#])"
        if re.search(pattern, full_text):
            catalogue_hits.append(canonical)

    declared_clean = _dedupe(declared, 60)
    return {
        "declared": declared_clean,
        "catalogue_matches": _dedupe(catalogue_hits, 60),
        "all": _dedupe(declared_clean + catalogue_hits, 80),
    }


def extract_education(sections: dict[str, list[str]], text: str) -> list[dict[str, Any]]:
    lines = sections.get("education", [])
    entries: list[dict[str, Any]] = []
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        blob = " ".join(buffer)
        degree_match = DEGREE_RE.search(blob)
        institution = next(
            (line for line in buffer if INSTITUTION_HINT_RE.search(line)), None
        )
        cgpa_match = CGPA_RE.search(blob)
        percent_match = PERCENT_RE.search(blob)
        years = [int(m.group(0)) for m in YEAR_RE.finditer(blob)]
        entry = {
            "raw": blob[:400],
            "degree": degree_match.group(0).strip() if degree_match else None,
            "institution": institution.strip() if institution else None,
            "score": float(cgpa_match.group(1)) if cgpa_match else (
                float(percent_match.group(1)) if percent_match else None
            ),
            "score_type": "cgpa" if cgpa_match else ("percentage" if percent_match else None),
            "score_scale": float(cgpa_match.group(2)) if cgpa_match and cgpa_match.group(2) else None,
            "start_year": min(years) if years else None,
            "end_year": max(years) if years else None,
        }
        if entry["degree"] or entry["institution"] or entry["score"]:
            entries.append(entry)
        buffer.clear()

    for line in lines:
        if INSTITUTION_HINT_RE.search(line) and buffer:
            flush()
        buffer.append(BULLET_RE.sub("", line))
    flush()

    grad = GRAD_YEAR_RE.search(text)
    if grad:
        for entry in entries:
            entry.setdefault("graduation_year", int(grad.group(1)))
    return entries[:6]


def _blocks(lines: list[str]) -> list[list[str]]:
    """Group lines into entries: a non-bullet line starts a new block."""
    blocks: list[list[str]] = []
    for line in lines:
        is_bullet = bool(BULLET_RE.match(line))
        if not is_bullet or not blocks:
            blocks.append([line])
        else:
            blocks[-1].append(line)
    return blocks


def extract_projects(sections: dict[str, list[str]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for block in _blocks(sections.get("projects", [])):
        title_line = BULLET_RE.sub("", block[0])
        body = " ".join(BULLET_RE.sub("", line) for line in block[1:])
        title = re.split(r"\s*[|–—\-:]\s*", title_line)[0].strip()
        tech: list[str] = []
        tech_match = re.search(
            r"(?:tech(?:nologies)?|stack|tools|built\s+with)\s*(?:used)?\s*[:\-]\s*(.+)",
            " ".join(block),
            re.I,
        )
        if tech_match:
            tech = [
                t.strip(" .")
                for t in SKILL_SPLIT_RE.split(tech_match.group(1))
                if 1 < len(t.strip()) <= 40
            ]
        urls = _dedupe(URL_RE.findall(" ".join(block)), 3)
        duration = DURATION_RE.search(" ".join(block))
        if title and len(title) > 2:
            results.append(
                {
                    "title": title[:180],
                    "description": (body or title_line)[:1200],
                    "technologies": _dedupe(tech, 15),
                    "links": urls,
                    "duration": duration.group(0) if duration else None,
                }
            )
    return results[:12]


def extract_experience(sections: dict[str, list[str]]) -> list[dict[str, Any]]:
    lines = sections.get("experience", []) + sections.get("positions", [])
    results: list[dict[str, Any]] = []
    for block in _blocks(lines):
        header = BULLET_RE.sub("", block[0])
        body = " ".join(BULLET_RE.sub("", line) for line in block[1:])
        blob = " ".join(block)
        duration = DURATION_RE.search(blob)
        parts = [p.strip() for p in re.split(r"\s*[|–—,]\s*", header) if p.strip()]
        title = next((p for p in parts if ROLE_TITLE_HINT_RE.search(p)), None)
        organization = next(
            (p for p in parts if COMPANY_SUFFIX_RE.search(p) or INSTITUTION_HINT_RE.search(p)),
            None,
        )
        if organization is None:
            organization = next((p for p in parts if p != title), None)
        if title is None and parts:
            title = parts[0]
        if not title:
            continue
        lowered = blob.lower()
        if "intern" in lowered:
            exp_type = "internship"
        elif re.search(r"president|secretary|coordinator|head|lead|volunteer|club|society", lowered):
            exp_type = "position_of_responsibility"
        else:
            exp_type = "job"
        results.append(
            {
                "title": title[:180],
                "organization": (organization or title)[:180],
                "experience_type": exp_type,
                "description": body[:1500] or None,
                "duration": duration.group(0) if duration else None,
                "start_raw": duration.group(1) if duration else None,
                "end_raw": duration.group(2) if duration else None,
            }
        )
    return results[:12]


def extract_certifications(sections: dict[str, list[str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in sections.get("certifications", []):
        cleaned = BULLET_RE.sub("", line).strip(" .")
        if len(cleaned) < 4:
            continue
        issuer = None
        issuer_match = re.search(
            r"(?:–|-|\||by|from)\s*([A-Z][A-Za-z0-9&.,\s]{2,60})$", cleaned
        )
        if issuer_match:
            issuer = issuer_match.group(1).strip(" .")
        year = YEAR_RE.search(cleaned)
        out.append(
            {
                "name": re.split(r"\s*(?:–|\||,\s*by)\s*", cleaned)[0][:200],
                "issuer": issuer,
                "year": int(year.group(0)) if year else None,
                "raw": cleaned[:240],
            }
        )
    return out[:15]


def extract_achievements(sections: dict[str, list[str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in sections.get("achievements", []):
        cleaned = BULLET_RE.sub("", line).strip(" .")
        if len(cleaned) < 5:
            continue
        lowered = cleaned.lower()
        if re.search(r"hackathon|contest|competition|rank|winner|runner|olympiad|case\s+comp", lowered):
            category = "competition"
        elif re.search(r"scholar|topper|dean|merit|gold medal|academic", lowered):
            category = "academic"
        elif re.search(r"club|sport|ncc|nss|volunteer|cultural|music|drama", lowered):
            category = "extracurricular"
        else:
            category = "other"
        year = YEAR_RE.search(cleaned)
        out.append(
            {
                "title": cleaned[:200],
                "category": category,
                "year": int(year.group(0)) if year else None,
            }
        )
    return out[:15]


def parse_resume(text: str, catalogue: dict[str, str]) -> dict[str, Any]:
    """Full deterministic parse. ``catalogue`` is lowercase name/alias -> display name."""
    text = text[:MAX_TEXT_CHARS]
    sections = split_sections(text)
    sections_found = [name for name in sections if name != "header" and sections[name]]

    words = re.findall(r"[A-Za-z][A-Za-z'+#.-]*", text)
    bullet_count = sum(1 for line in _lines(text) if BULLET_RE.match(line))
    lowered = text.lower()

    parsed = {
        "contact": extract_contact(text, sections),
        "skills": extract_skills(sections, catalogue),
        "education": extract_education(sections, text),
        "projects": extract_projects(sections),
        "experience": extract_experience(sections),
        "certifications": extract_certifications(sections),
        "achievements": extract_achievements(sections),
        "sections_found": sections_found,
        "stats": {
            "word_count": len(words),
            "line_count": len([line for line in _lines(text) if line.strip()]),
            "bullet_count": bullet_count,
            "action_verbs_used": sorted({v for v in ACTION_VERBS if v in lowered}),
            "quantified_statements": len(METRIC_RE.findall(text)),
            "character_count": len(text),
        },
    }
    return parsed
