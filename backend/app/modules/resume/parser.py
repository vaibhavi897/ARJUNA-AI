"""Deterministic resume parsing.

This is heuristic text analysis, not a trained model. It segments the resume
into sections, then pulls candidate skills, education, projects, experience,
certifications and achievements out of each. Output is always presented to the
student for review before anything is merged into their profile.

The hard part is grouping, not matching. A PDF or DOCX gives back visual
lines, and one logical bullet is often spread over two or three of them. Three
rules do the grouping, in order:

1. A line that starts with a bullet marker opens a new bullet.
2. A line that continues the previous one (wrapped mid-sentence, hyphenated,
   or starting lower-case) is folded back into it - never promoted to an entry.
3. Only a line that survives both tests can start, or extend, an entry heading.

Without rule 2 every wrapped line becomes its own "project" or "job", which is
exactly the failure this module is written to avoid.
"""

from __future__ import annotations

import re
from typing import Any

# ``positions`` is matched before ``experience`` so that a "Leadership
# Experience" heading is not swallowed by the generic experience pattern.
SECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "summary": re.compile(r"^\s*(professional\s+)?(summary|objective|profile|about\s+me)\s*:?\s*$", re.I),
    "education": re.compile(r"^\s*(education|academics?|academic\s+(background|qualifications?)|educational\s+qualifications?)\s*:?\s*$", re.I),
    "skills": re.compile(r"^\s*(technical\s+)?(skills?|core\s+competenc(y|ies)|technologies|technical\s+expertise)\s*(&|and)?\s*(interests?)?\s*:?\s*$", re.I),
    "projects": re.compile(r"^\s*(academic\s+|key\s+|personal\s+|selected\s+)?projects?(\s+(&|and)\s+\w+)?\s*:?\s*$", re.I),
    "certifications": re.compile(r"^\s*(certifications?|licenses?|courses?|certificates?)(\s+(&|and)\s+\w+)?\s*:?\s*$", re.I),
    "achievements": re.compile(r"^\s*(achievements?|awards?|honors?|honours?|accomplishments?)(\s+(&|and)\s+\w+)?\s*:?\s*$", re.I),
    "positions": re.compile(
        r"^\s*("
        r"positions?\s+of\s+responsibility"
        r"|leadership(\s+(experience|roles?|positions?|activities))?"
        r"|volunteer(ing)?(\s+(experience|work))?"
        r"|extra[\s-]?curricular(\s+\w+)*"
        r"|co[\s-]?curricular(\s+\w+)*"
        r"|activities(\s+(&|and)\s+\w+)?"
        r")\s*:?\s*$",
        re.I,
    ),
    "experience": re.compile(r"^\s*(work\s+|professional\s+|industry\s+|relevant\s+)?(experience|employment|internships?|work\s+history)\s*:?\s*$", re.I),
    "contact": re.compile(r"^\s*(contact|personal\s+details?)\s*:?\s*$", re.I),
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:(?:\+|00)\d{1,3}[\s-]?)?(?:\(?\d{2,5}\)?[\s-]?)?\d{3}[\s-]?\d{4}\b")
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?/?", re.I)
GITHUB_PROFILE_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_.-]+/?$", re.I)
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_%.-]+/?", re.I)
URL_RE = re.compile(r"https?://[^\s,;)]+", re.I)
CGPA_RE = re.compile(r"(?:cgpa|gpa|cpi|sgpa)\s*[:\-]?\s*(\d{1,2}(?:\.\d{1,2})?)\s*(?:/\s*(\d{1,2}))?", re.I)
PERCENT_RE = re.compile(r"(\d{2,3}(?:\.\d{1,2})?)\s*%")
YEAR_RE = re.compile(r"(19|20)\d{2}")
GRAD_YEAR_RE = re.compile(r"(?:expected\s+)?(?:graduation|batch|class\s+of)\s*[:\-]?\s*((?:19|20)\d{2})", re.I)
MONTH_YEAR = (
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*,?\s*(?:19|20)\d{2}"
)
DURATION_RE = re.compile(
    rf"({MONTH_YEAR}|(?:19|20)\d{{2}})"
    r"\s*(?:-|–|—|to)\s*"
    rf"({MONTH_YEAR}|(?:19|20)\d{{2}}|present|current|ongoing)",
    re.I,
)
BULLET_RE = re.compile(r"^\s*(?:[-*•●▪‣⁃>]|\d+[.)])\s*")

# Lines that elaborate on the heading above them rather than starting a new
# entry: "Technologies used: ...", "Duration: 3 months", "Role: ...".
HEADER_LABEL_RE = re.compile(
    r"^\s*(tech(?:nologies|nology|\s+stack)?|stack|tools|built\s+with|duration|period|"
    r"role|team(\s+size)?|location|organi[sz]ation|company|employer|client|link|links|repo(sitory)?)"
    r"\s*(used)?\s*[:\-–]",
    re.I,
)
TECH_INLINE_RE = re.compile(
    r"(?:tech(?:nologies|nology)?|stack|tools|built\s+with)\s*(?:used)?\s*[:\-–]\s*(.+)",
    re.I,
)
# Anchor words that stand in for a hyperlink in a PDF heading.
LINK_WORD_RE = re.compile(
    r"\b(github|gitlab|bitbucket|live\s*(demo|site|link)?|demo|repo(sitory)?|source(\s+code)?|"
    r"code|link|website|deployed|view\s+project|project\s+link)\b\s*[:\-–]?\s*",
    re.I,
)
SENTENCE_END_RE = re.compile(r"[.!?;:…]\s*$")

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
# Club / committee style organisations that appear in leadership sections.
BODY_HINT_RE = re.compile(
    r"\b(club|society|committee|chapter|council|cell|forum|association|union|team|ngo|foundation|trust)\b",
    re.I,
)

ROLE_TITLE_HINT_RE = re.compile(
    r"\b(intern|internship|analyst|engineer|developer|consultant|associate|trainee|"
    r"manager|scientist|researcher|lead|president|secretary|coordinator|head|volunteer|"
    r"treasurer|captain|mentor|ambassador|convenor|convener|chair(person)?|member)\b",
    re.I,
)
VOLUNTEER_HINT_RE = re.compile(
    r"\b(volunteer|ncc|nss|sport|cultural|drama|music|dance|social\s+impact|outreach\s+drive)\b",
    re.I,
)
LEADERSHIP_HINT_RE = re.compile(
    r"\b(president|secretary|coordinator|head|lead|captain|treasurer|convenor|convener|"
    r"chair(person)?|club|society|committee|chapter|council)\b",
    re.I,
)

# Split a skills line on separators but keep multi-word skills intact.
SKILL_SPLIT_RE = re.compile(r"[,;|/•·]|\s{2,}|\n")
# One-character skill names that are genuine languages, not stray letters.
SHORT_SKILL_RE = re.compile(r"[CRcr][+#]*")

ACTION_VERBS = (
    "built", "designed", "developed", "implemented", "led", "created", "analysed",
    "analyzed", "optimised", "optimized", "automated", "deployed", "improved",
    "reduced", "increased", "managed", "modelled", "modeled", "forecasted",
    "valued", "audited", "researched", "delivered", "launched", "migrated",
    "engineered",
)

METRIC_RE = re.compile(r"(\d+(?:\.\d+)?\s*(?:%|percent|x|k|lakh|crore|million|bn|billion)|\$\s?\d)", re.I)

MAX_TEXT_CHARS = 120_000
MAX_HEADER_LINES = 3
MIN_TITLE_CHARS = 3


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


def _clean(value: str) -> str:
    return " ".join(value.split()).strip(" •-–—|,;:.")


# ---------------------------------------------------------------------------
# Line grouping
# ---------------------------------------------------------------------------
def _is_continuation(previous: str, line: str) -> bool:
    """Is ``line`` the wrapped remainder of ``previous`` rather than new content?"""
    previous = previous.rstrip()
    if not previous or not line:
        return False
    if DURATION_RE.search(line) or HEADER_LABEL_RE.match(line):
        return False
    if previous.endswith("-"):
        return True
    if line[:1].islower():
        return True
    # A heading ends cleanly; a sentence cut by the page width does not.
    return not SENTENCE_END_RE.search(previous)


def _join_wrapped(previous: str, line: str) -> str:
    if previous.endswith("-") and line[:1].islower():
        # "struc-" + "tures" -> "structures"
        return previous[:-1] + line
    return f"{previous} {line}"


def logical_lines(lines: list[str]) -> list[tuple[bool, str]]:
    """``(is_bullet, text)`` with layout line wraps folded back together."""
    out: list[list[Any]] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if BULLET_RE.match(line):
            out.append([True, BULLET_RE.sub("", line).strip()])
            continue
        if out:
            was_bullet, previous = out[-1][0], out[-1][1]
            # After a bullet any wrapped remainder belongs to it. After a plain
            # line only an obvious mid-sentence wrap does, so that a two-line
            # "Title / Company" heading is not welded into one string.
            if (was_bullet or line[:1].islower()) and _is_continuation(previous, line):
                out[-1][1] = _join_wrapped(previous, line)
                continue
        out.append([False, line])
    return [(bool(flag), str(text)) for flag, text in out]


def _absorbs_into_header(header: list[str], line: str) -> bool:
    """Does ``line`` extend the heading above it (company, tech list, dates)?"""
    if not header or len(header) >= MAX_HEADER_LINES:
        return False
    if HEADER_LABEL_RE.match(line):
        return True
    if DURATION_RE.search(line):
        return False
    if COMPANY_SUFFIX_RE.search(line) or INSTITUTION_HINT_RE.search(line):
        return True
    if BODY_HINT_RE.search(line):
        return True
    # Classic two-line heading: "Role  <dates>" followed by the organisation.
    return len(header) == 1 and bool(DURATION_RE.search(header[0]))


def group_entries(lines: list[str]) -> list[dict[str, Any]]:
    """Group a section's lines into ``{"header": [...], "bullets": [...]}``."""
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for is_bullet, text in logical_lines(lines):
        if is_bullet:
            if current is None:
                current = {"header": [], "bullets": []}
                entries.append(current)
            current["bullets"].append(text)
            continue
        if current is not None and not current["bullets"] and _absorbs_into_header(
            current["header"], text
        ):
            current["header"].append(text)
            continue
        current = {"header": [text], "bullets": []}
        entries.append(current)

    # A section that opens straight into bullets ("Technical Lead, ACM - ...")
    # has no heading line; promote the first bullet so the entry has a title.
    for entry in entries:
        if not entry["header"] and entry["bullets"]:
            entry["header"] = [entry["bullets"].pop(0)]
    return [entry for entry in entries if entry["header"] or entry["bullets"]]


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------
def _best_url(candidates: list[str]) -> str | None:
    """Prefer a real href over the visible, often truncated, anchor text."""
    if not candidates:
        return None
    absolute = [c for c in candidates if c.lower().startswith("http")]
    pool = absolute or candidates
    return _normalise_url(max(pool, key=len))


def extract_contact(text: str, sections: dict[str, list[str]]) -> dict[str, Any]:
    head = "\n".join(sections.get("header", [])[:12]) or text[:800]
    emails = EMAIL_RE.findall(text)
    phones = [p for p in PHONE_RE.findall(text[:2000]) if len(re.sub(r"\D", "", p)) >= 10]

    github_candidates = [m.group(0) for m in GITHUB_RE.finditer(text)]
    profile_github = [m for m in github_candidates if GITHUB_PROFILE_RE.match(m)]
    linkedin_candidates = [m.group(0) for m in LINKEDIN_RE.finditer(text)]

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
        "github_url": _best_url(profile_github or github_candidates),
        "linkedin_url": _best_url(linkedin_candidates),
        "other_urls": other_urls,
        "header_preview": head[:400],
    }


def _normalise_url(value: str) -> str:
    value = value.rstrip("/.,;)")
    if not value.lower().startswith("http"):
        value = "https://" + value
    return value


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------
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
            if token.isdigit() or len(token) > 60:
                continue
            # "Java, C, Python": single-letter languages are real skills.
            if len(token) > 1 or SHORT_SKILL_RE.fullmatch(token):
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


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------
def extract_education(sections: dict[str, list[str]], text: str) -> list[dict[str, Any]]:
    lines = [line for _, line in logical_lines(sections.get("education", []))]
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
            "institution": _strip_duration(institution) if institution else None,
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


# ---------------------------------------------------------------------------
# Heading analysis shared by projects and experience
# ---------------------------------------------------------------------------
def _strip_duration(value: str) -> str:
    return _clean(DURATION_RE.sub(" ", value))


def _is_fragment(title: str) -> bool:
    """Reject sentence pieces that a layout wrap left behind."""
    if len(title) < MIN_TITLE_CHARS:
        return True
    if title[:1].islower():
        return True
    if title.endswith(","):
        return True
    # A heading is a label, not prose.
    return len(title.split()) > 18


def _split_header(header: str) -> list[str]:
    parts = [
        _clean(part)
        for part in re.split(r"\s*[|–—]\s*|\s+-\s+", header)
        if _clean(part)
    ]
    return parts or [_clean(header)]


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
def extract_projects(sections: dict[str, list[str]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for entry in group_entries(sections.get("projects", [])):
        header_lines = entry["header"]
        bullets = entry["bullets"]
        blob = " ".join(header_lines + bullets)

        label_lines = [line for line in header_lines if HEADER_LABEL_RE.match(line)]
        title_lines = [line for line in header_lines if not HEADER_LABEL_RE.match(line)]
        heading = " ".join(title_lines) or " ".join(header_lines)

        duration = DURATION_RE.search(heading) or DURATION_RE.search(blob)
        heading = URL_RE.sub(" ", heading)
        heading = _strip_duration(heading)

        # "Name - subtitle  Github | React, Node" -> title / technologies.
        segments = [seg for seg in re.split(r"\s*\|\s*", heading) if seg.strip()]
        title = _clean(LINK_WORD_RE.sub(" ", segments[0])) if segments else ""
        tech: list[str] = []
        if len(segments) > 1:
            tech = [
                _clean(token)
                for token in SKILL_SPLIT_RE.split(" , ".join(segments[1:]))
                if 1 < len(_clean(token)) <= 40
            ]

        inline = TECH_INLINE_RE.search(" ".join(label_lines) or blob)
        if inline:
            tech += [
                _clean(token)
                for token in SKILL_SPLIT_RE.split(inline.group(1))
                if 1 < len(_clean(token)) <= 40
            ]

        description = " ".join(bullets).strip()
        if not description:
            description = " ".join(
                line for line in header_lines if line not in title_lines[:1]
            ).strip()

        if not title or _is_fragment(title):
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)

        urls = _dedupe(URL_RE.findall(" ".join(header_lines + bullets)), 3)
        github = next((url for url in urls if "github.com" in url.lower()), None)
        results.append(
            {
                "title": title[:180],
                "description": (description or title)[:1200],
                "technologies": _dedupe(tech, 15),
                "links": urls,
                "github_url": github,
                "live_url": next((url for url in urls if url != github), None),
                "duration": duration.group(0) if duration else None,
                "start_raw": duration.group(1) if duration else None,
                "end_raw": duration.group(2) if duration else None,
                "highlights": bullets[:10],
            }
        )
    return results[:12]


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------
def _experience_type(section: str, title: str, blob: str) -> str:
    lowered = f"{title} {blob}".lower()
    if section == "positions":
        # Leadership and volunteering are never employment, whatever the
        # wording - they are classified only within those two kinds.
        if VOLUNTEER_HINT_RE.search(lowered):
            return "extracurricular"
        return "position_of_responsibility"
    if re.search(r"\bintern(ship)?\b|\btrainee\b|\bapprentice\b", lowered):
        return "internship"
    if LEADERSHIP_HINT_RE.search(title.lower()) and not COMPANY_SUFFIX_RE.search(blob):
        return "position_of_responsibility"
    return "job"


def _experience_from_entry(entry: dict[str, Any], section: str) -> dict[str, Any] | None:
    header_lines = entry["header"]
    bullets = entry["bullets"]
    if not header_lines:
        return None

    label_lines = [line for line in header_lines if HEADER_LABEL_RE.match(line)]
    plain_lines = [line for line in header_lines if not HEADER_LABEL_RE.match(line)]
    blob = " ".join(header_lines + bullets)
    duration = DURATION_RE.search(" ".join(header_lines)) or DURATION_RE.search(blob)

    primary = _strip_duration(URL_RE.sub(" ", plain_lines[0] if plain_lines else header_lines[0]))
    secondary = (
        _strip_duration(URL_RE.sub(" ", plain_lines[1])) if len(plain_lines) > 1 else None
    )

    trailing_description = ""
    parts = _split_header(primary)
    # A heading that opens straight into prose ("Technical Lead, ACM - Ran
    # weekly sessions...") carries its description in the tail segment.
    if len(parts) > 1 and len(parts[-1].split()) > 10:
        trailing_description = parts.pop()

    if len(parts) == 1 and "," in parts[0] and secondary is None:
        parts = [_clean(piece) for piece in parts[0].split(",", 1) if _clean(piece)]

    title = next((part for part in parts if ROLE_TITLE_HINT_RE.search(part)), None) or parts[0]
    organization = secondary
    if not organization:
        organization = next(
            (
                part
                for part in parts
                if part != title
                and (
                    COMPANY_SUFFIX_RE.search(part)
                    or INSTITUTION_HINT_RE.search(part)
                    or BODY_HINT_RE.search(part)
                )
            ),
            None,
        )
    if not organization:
        organization = next((part for part in parts if part != title), None)

    title = _clean(title)
    if not title or _is_fragment(title):
        return None

    description_bits = [*bullets]
    if trailing_description:
        description_bits.insert(0, trailing_description)
    for line in label_lines:
        if not TECH_INLINE_RE.match(line):
            description_bits.append(line)
    description = " ".join(description_bits).strip()

    skills_used: list[str] = []
    inline = TECH_INLINE_RE.search(" ".join(label_lines))
    if inline:
        skills_used = [
            _clean(token)
            for token in SKILL_SPLIT_RE.split(inline.group(1))
            if 1 < len(_clean(token)) <= 40
        ]

    return {
        "title": title[:180],
        "organization": (_clean(organization) or title)[:180],
        "experience_type": _experience_type(section, title, blob),
        "description": description[:1500] or None,
        "duration": duration.group(0) if duration else None,
        "start_raw": duration.group(1) if duration else None,
        "end_raw": duration.group(2) if duration else None,
        "skills_used": _dedupe(skills_used, 15),
        "highlights": bullets[:10],
        "source_section": section,
    }


def extract_experience(sections: dict[str, list[str]]) -> list[dict[str, Any]]:
    """Employment and leadership, grouped per organisation and kept distinct.

    Entries from a leadership / volunteering heading are never typed as a job,
    even when the title alone would read like one ("Research Analyst").
    """
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for section in ("experience", "positions"):
        for entry in group_entries(sections.get(section, [])):
            item = _experience_from_entry(entry, section)
            if item is None:
                continue
            key = f"{item['title']}|{item['organization']}".lower()
            if key in seen:
                continue
            seen.add(key)
            results.append(item)
    return results[:12]


# ---------------------------------------------------------------------------
# Certifications and achievements
# ---------------------------------------------------------------------------
def _section_items(sections: dict[str, list[str]], name: str) -> list[str]:
    return [text for _, text in logical_lines(sections.get(name, []))]


def extract_certifications(sections: dict[str, list[str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in _section_items(sections, "certifications"):
        cleaned = BULLET_RE.sub("", line).strip(" .")
        if len(cleaned) < 4:
            continue
        # "AWS Certified Cloud Practitioner - Amazon Web Services - 2025"
        parts = [
            _clean(part)
            for part in re.split(r"\s*[|–—]\s*|\s+-\s+|,\s*by\s+", cleaned)
            if _clean(part)
        ]
        year = YEAR_RE.search(cleaned)
        name = (parts[0] if parts else cleaned)[:200]
        issuer = next(
            (
                part
                for part in parts[1:]
                if not YEAR_RE.fullmatch(part) and not part.isdigit() and len(part) > 2
            ),
            None,
        )
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "name": name,
                "issuer": issuer,
                "year": int(year.group(0)) if year else None,
                "raw": cleaned[:240],
            }
        )
    return out[:15]


def extract_achievements(sections: dict[str, list[str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in _section_items(sections, "achievements"):
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
        title = cleaned[:200]
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "title": title,
                "category": category,
                "year": int(year.group(0)) if year else None,
            }
        )
    return out[:15]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
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
