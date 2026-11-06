"""Deterministic resume parsing.

This is heuristic text analysis, not a trained model, and it never invents a
fact: every field it returns is a span of the student's own text. Output is
always presented to the student for review before anything is merged into
their profile.

The hard part is **grouping**, not matching. One logical entry - a project, an
internship - is spread over a heading line, an organisation line, and several
bullets that each wrap across two or three visual lines. Get the grouping
wrong and a single project becomes five meaningless records, which is exactly
the failure this module exists to prevent.

Four signals do the grouping, in order of reliability:

1. **Columns.** ``extract`` turns a wide horizontal gap into a tab, so
   ``Role <tab> Jun 2026 - Jul 2026`` arrives as two cells. A line that has a
   date in its own cell is a structured heading, never prose.
2. **Bullet markers.** A marked line is a detail of the entry above it. In an
   entry section it can never start a new entry.
3. **Indentation.** A line indented past the section's heading column is a
   wrapped continuation of the line before it.
4. **Sentence shape.** A heading ends cleanly; a line cut by the page width
   does not. Used last, and only where 1-3 are silent.

Anything that survives grouping still has to earn its place: an entry with no
usable title, or with nothing but a title, is dropped rather than published as
a half-record.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.modules.resume.extract import COLUMN_SEP

# ---------------------------------------------------------------------------
# Section headings
# ---------------------------------------------------------------------------
# A compound heading ("Skills, Certifications & Courses") names more than one
# section. Each fragment is matched separately and the winner is decided by
# SECTION_PRIORITY, so the heading does not have to be written our way.
SECTION_FRAGMENTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("summary", re.compile(r"^(professional\s+|career\s+)?(summary|objective|profile|about\s+me)$", re.I)),
    ("education", re.compile(r"^(education(al)?|academics?|academic\s+(background|qualifications?|details?)|qualifications?|scholastics?)$", re.I)),
    ("skills", re.compile(r"^((technical|core|key|professional|it|computer)\s+)?(skills?|competenc(y|ies)|technologies|tech\s+stack|expertise|proficienc(y|ies))$", re.I)),
    ("projects", re.compile(r"^((academic|key|personal|selected|major|technical|notable)\s+)?(projects?|project\s+work|case\s+stud(y|ies))$", re.I)),
    ("certifications", re.compile(r"^(certifications?|certificates?|licen[cs]es?|courses?|coursework|trainings?|moocs?)$", re.I)),
    ("achievements", re.compile(r"^(achievements?|awards?|honou?rs?|accomplishments?|accolades?|recognitions?|competitions?)$", re.I)),
    ("positions", re.compile(r"^(positions?(\s+of\s+responsibility)?|responsibilit(y|ies)|leadership|leadership\s+(experience|roles?|positions?|activities)|volunteer(ing)?(\s+(experience|work))?|extra[\s-]?curriculars?(\s+activities)?|co[\s-]?curriculars?(\s+activities)?|activities|clubs?(\s+(&|and)\s+societies)?)$", re.I)),
    ("experience", re.compile(r"^((work|professional|industry|relevant|research|internship)\s+)?(experience|employment|internships?|work\s+history|training)$", re.I)),
    ("publications", re.compile(r"^(publications?|papers?|research\s+papers?|patents?)$", re.I)),
    ("interests", re.compile(r"^(interests?|hobbies|languages?\s+known|personal\s+details?|references?|declaration)$", re.I)),
    ("contact", re.compile(r"^(contacts?|contact\s+details?|personal\s+information)$", re.I)),
)

# When a heading names several sections, the most specific one wins. "Skills,
# Certifications & Courses" is a skills block; "Extra Curricular &
# Achievements" is an achievements block; "Leadership Experience" is a
# positions block, not an employment one.
SECTION_PRIORITY = (
    "skills",
    "achievements",
    "certifications",
    "projects",
    "education",
    "publications",
    "summary",
    "interests",
    "contact",
    "positions",
    "experience",
)

# Sections whose content is a list of entries (heading + supporting bullets).
ENTRY_SECTIONS = ("experience", "positions", "projects")
# Sections whose content is a list of short items.
ITEM_SECTIONS = ("achievements", "certifications")

MAX_HEADING_CHARS = 64

# ---------------------------------------------------------------------------
# Field-level patterns
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:(?:\+|00)\d{1,3}[\s-]?)?(?:\(?\d{2,5}\)?[\s-]?)?\d{3}[\s-]?\d{4}\b")
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?/?", re.I)
GITHUB_PROFILE_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_.-]+/?$", re.I)
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_%.-]+/?", re.I)
URL_RE = re.compile(r"(?:https?://|www\.)[^\s,;)\]]+", re.I)
SCHEME_URL_RE = re.compile(r"\b(?:mailto|tel|ftp|file):\S+", re.I)
CGPA_RE = re.compile(r"(?:cgpa|gpa|cpi|sgpa|dgpa)\s*[:\-]?\s*(\d{1,2}(?:\.\d{1,3})?)\s*(?:/\s*(\d{1,2}(?:\.\d{1,2})?))?", re.I)
BARE_SCORE_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,3})?)\s*/\s*(\d{1,2}(?:\.\d{1,2})?)$")
PERCENT_RE = re.compile(r"(\d{2,3}(?:\.\d{1,2})?)\s*%")
YEAR_RE = re.compile(r"(?:19|20)\d{2}")
GRAD_YEAR_RE = re.compile(r"(?:expected\s+)?(?:graduation|batch|class\s+of)\s*[:\-]?\s*((?:19|20)\d{2})", re.I)

MONTH_YEAR = (
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*,?\s*'?(?:19|20)?\d{2}"
)
DURATION_RE = re.compile(
    rf"({MONTH_YEAR}|(?:19|20)\d{{2}})"
    r"\s*(?:-|–|—|to|until)\s*"
    rf"({MONTH_YEAR}|(?:19|20)\d{{2}}|present|current|ongoing|date|now)",
    re.I,
)
SINGLE_DATE_RE = re.compile(rf"\b({MONTH_YEAR})\b", re.I)
BULLET_RE = re.compile(r"^\s*(?:[•]|\d+[.)])\s*")

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
# A "Label: value" line opens a new item in a list section.
ITEM_LABEL_RE = re.compile(r"^[A-Z0-9][^:]{0,44}:\s*\S", re.S)
# Anchor words that stand in for a hyperlink in a PDF heading. Only matched at
# the very start or end of a heading segment: "Collaborative VS Code" is a
# project name, not a link, and "Github" at the end of a title is a link.
LINK_WORD_RE = re.compile(
    r"(?:^|\s)(github|gitlab|bitbucket|repo(?:sitory)?|live\s+(?:demo|site|link)|demo|"
    r"source\s+code|website|view\s+project|project\s+link|deployed)\s*[:\-–]?\s*$",
    re.I,
)
SENTENCE_END_RE = re.compile(r"[.!?;:…]\s*$")

DEGREE_RE = re.compile(
    r"\b(b\.?\s?tech|b\.?\s?e\.?|b\.?\s?sc|bca|b\.?\s?com|bba|b\.?\s?a\.?|"
    r"m\.?\s?tech|m\.?\s?e\.?|m\.?\s?sc|mca|m\.?\s?com|mba|m\.?\s?a\.?|"
    r"ph\.?\s?d|b\.?\s?s\b|m\.?\s?s\b|bachelor[s]?|master[s]?|"
    r"diploma|minor\s+in|higher\s+secondary|"
    r"secondary\s+(school|education)|hsc|ssc|intermediate|class\s+(x|xii|10|12))\b",
    re.I,
)
INSTITUTION_HINT_RE = re.compile(
    r"\b(institute|institution|university|college|school|academy|polytechnic|"
    r"iit|nit|iiit|bits|vit|srm|ies|vjti|spit)\b",
    re.I,
)
COMPANY_SUFFIX_RE = re.compile(
    r"\b(pvt|private|limited|ltd|llp|inc|incorporated|corp|corporation|gmbh|plc|"
    r"technologies|technology|solutions|systems|labs?|laboratories|consulting|consultancy|"
    r"capital|bank|banking|partners|group|services|industries|enterprises|ventures|"
    r"associates|sciences|analytics|media|studios?|works|global|international)\b",
    re.I,
)
# Club / committee style organisations that appear in leadership sections.
BODY_HINT_RE = re.compile(
    r"\b(club|society|committee|chapter|council|cell|forum|association|union|team|"
    r"ngo|foundation|trust|fest|summit|community|board)\b",
    re.I,
)
ROLE_TITLE_HINT_RE = re.compile(
    r"\b(intern|internship|trainee|apprentice|analyst|engineer|developer|programmer|"
    r"consultant|associate|architect|designer|manager|scientist|researcher|research\s+\w+|"
    r"lead|president|vice[\s-]?president|secretary|coordinator|co[\s-]?ordinator|head|"
    r"treasurer|captain|mentor|ambassador|convenor|convener|chair(person)?|member|"
    r"volunteer|executive|officer|strategist|specialist|freelancer?)\b",
    re.I,
)
WORK_MODE_RE = re.compile(r"^(remote|hybrid|on[\s-]?site|onsite|work\s+from\s+home|wfh)$", re.I)
VOLUNTEER_HINT_RE = re.compile(
    r"\b(volunteer|ncc|nss|sport|cultural|drama|music|dance|social\s+impact|outreach\s+drive|"
    r"teach\s+for|rotaract|leo\s+club)\b",
    re.I,
)
LEADERSHIP_HINT_RE = re.compile(
    r"\b(president|secretary|coordinator|head|captain|treasurer|convenor|convener|"
    r"chair(person)?|club|society|committee|chapter|council|cell|forum)\b",
    re.I,
)
INTERN_HINT_RE = re.compile(r"\b(intern|internship|trainee|apprentice|summer\s+analyst)\b", re.I)

# Skills lines are "Label: a, b, c". These labels are not skills sections.
NON_SKILL_LABEL_RE = re.compile(
    r"^(certifications?|certificates?|courses?|coursework|trainings?|licen[cs]es?)\b", re.I
)

ACTION_VERBS = (
    "built", "designed", "developed", "implemented", "led", "created", "analysed",
    "analyzed", "optimised", "optimized", "automated", "deployed", "improved",
    "reduced", "increased", "managed", "modelled", "modeled", "forecasted",
    "valued", "audited", "researched", "delivered", "launched", "migrated",
    "engineered", "architected", "benchmarked", "orchestrated", "streamlined",
    "coordinated", "mentored", "presented", "negotiated", "integrated",
)
METRIC_RE = re.compile(
    r"(\d+(?:[.,]\d+)?\s*(?:%|percent|x|k\b|lakh|crore|million|mn\b|bn\b|billion|"
    r"users?|teams?|students?|participants?|months?|hours?|ms\b|seconds?)|[$₹]\s?\d|\d+\+)",
    re.I,
)

MAX_TEXT_CHARS = 120_000
MAX_HEADER_LINES = 2
MIN_TITLE_CHARS = 3
MAX_TITLE_WORDS = 20
# How many projects are surfaced as the student's headline work by default.
PRIMARY_PROJECT_COUNT = 3


# ---------------------------------------------------------------------------
# Line model
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class Line:
    """One physical line, split into its visual columns."""

    text: str
    indent: int
    is_bullet: bool
    extra_cells: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)

    @property
    def blob(self) -> str:
        return " ".join([self.text, *self.extra_cells])

    @property
    def duration(self) -> re.Match[str] | None:
        for cell in [*self.extra_cells, self.text]:
            match = DURATION_RE.search(cell)
            if match:
                return match
        return None

    @property
    def single_date(self) -> str | None:
        for cell in self.extra_cells:
            if DURATION_RE.search(cell):
                continue
            match = SINGLE_DATE_RE.fullmatch(cell.strip()) or (
                SINGLE_DATE_RE.search(cell) if len(cell) <= 24 else None
            )
            if match:
                return match.group(1)
        return None

    @property
    def has_date_cell(self) -> bool:
        return any(
            DURATION_RE.search(cell) or SINGLE_DATE_RE.search(cell)
            for cell in self.extra_cells
        ) or bool(DURATION_RE.search(self.text))

    @property
    def notes(self) -> list[str]:
        """Column cells that are neither dates nor scores - location, scope."""
        out: list[str] = []
        for cell in self.extra_cells:
            if DURATION_RE.search(cell) or SINGLE_DATE_RE.search(cell):
                continue
            if CGPA_RE.search(cell) or PERCENT_RE.search(cell) or BARE_SCORE_RE.match(cell):
                continue
            if cell:
                out.append(cell)
        return out


def _strip_urls(value: str) -> tuple[str, list[str]]:
    """Pull every URL out of a string, returning the cleaned text and the URLs."""
    urls = [m.group(0) for m in URL_RE.finditer(value)]
    cleaned = URL_RE.sub(" ", value)
    cleaned = SCHEME_URL_RE.sub(" ", cleaned)
    return " ".join(cleaned.split()), urls


def read_lines(raw_lines: list[str]) -> list[Line]:
    """Turn raw text lines into the column-aware :class:`Line` model."""
    out: list[Line] = []
    for raw in raw_lines:
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        body = raw.strip()
        is_bullet = bool(BULLET_RE.match(body))
        if is_bullet:
            body = BULLET_RE.sub("", body, count=1)

        cells: list[str] = []
        urls: list[str] = []
        for cell in body.split(COLUMN_SEP):
            cleaned, cell_urls = _strip_urls(cell)
            urls.extend(cell_urls)
            cleaned = cleaned.strip()
            if cleaned:
                cells.append(cleaned)
        if not cells:
            # A line that was nothing but links still carries its links.
            if urls and out:
                out[-1].urls.extend(u for u in urls if u not in out[-1].urls)
            continue
        out.append(
            Line(
                text=cells[0],
                indent=indent,
                is_bullet=is_bullet,
                extra_cells=cells[1:],
                urls=_dedupe(urls),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Section splitting
# ---------------------------------------------------------------------------
def _heading_kind(line: Line) -> str | None:
    """Which section this line declares, or ``None`` if it is not a heading."""
    if line.is_bullet or line.extra_cells or line.urls:
        return None
    text = line.text.strip()
    if not text or len(text) > MAX_HEADING_CHARS:
        return None
    if text.endswith((".", ",")) or DURATION_RE.search(text):
        return None

    normalised = re.sub(r"[^A-Za-z&/,\s]", " ", text).strip()
    if not normalised:
        return None
    fragments = [
        part.strip()
        for part in re.split(r"\s*(?:,|&|/|\band\b)\s*", normalised, flags=re.I)
        if part.strip()
    ]
    matched: set[str] = set()
    for fragment in fragments:
        for kind, pattern in SECTION_FRAGMENTS:
            if pattern.match(fragment):
                matched.add(kind)
                break
        else:
            # An unrecognised fragment means this is prose, not a heading.
            return None
    if not matched:
        return None
    for kind in SECTION_PRIORITY:
        if kind in matched:
            return kind
    return None


def split_sections(lines: list[Line]) -> dict[str, list[Line]]:
    """Bucket the resume's lines under the headings it declares."""
    sections: dict[str, list[Line]] = {"header": []}
    current = "header"
    for line in lines:
        kind = _heading_kind(line)
        if kind is not None:
            current = kind
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _dedupe(values: list[str], limit: int | None = None) -> list[str]:
    seen: dict[str, str] = {}
    for value in values:
        cleaned = " ".join(str(value).split())
        if not cleaned:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen[key] = cleaned
    out = list(seen.values())
    return out[:limit] if limit else out


def _clean(value: str) -> str:
    return " ".join(value.split()).strip(" •-–—|,;:.")


def _dehyphenate(previous: str, nxt: str) -> str:
    """``"struc-" + "tures"`` -> ``"structures"``; otherwise join with a space."""
    if previous.endswith("-") and nxt[:1].islower():
        return previous[:-1] + nxt
    return f"{previous} {nxt}"


def _split_list(value: str) -> list[str]:
    """Split a comma/semicolon list without breaking bracketed groups."""
    out: list[str] = []
    buffer: list[str] = []
    depth = 0
    for char in value:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth = max(depth - 1, 0)
        if depth == 0 and (char in ",;|•·" or (char == "/" and depth == 0)):
            out.append("".join(buffer))
            buffer = []
            continue
        buffer.append(char)
    out.append("".join(buffer))
    return [_clean(part) for part in out if _clean(part)]


def _is_fragment(title: str) -> bool:
    """Reject sentence pieces that a layout wrap left behind."""
    if len(title) < MIN_TITLE_CHARS:
        return True
    if title[:1].islower():
        return True
    if title.endswith((",", "-", "–", "—")):
        return True
    if len(title.split()) > MAX_TITLE_WORDS:
        return True
    # "and validating formula lineage through end-to-end testing" - a heading
    # does not open with a conjunction or preposition.
    return bool(re.match(r"^(and|or|but|with|for|to|of|in|on|by|through|using|the)\b", title, re.I))


def _strip_duration(value: str) -> str:
    value = DURATION_RE.sub(" ", value)
    value = SINGLE_DATE_RE.sub(" ", value)
    return _clean(value)


def _normalise_url(value: str) -> str:
    value = value.rstrip("/.,;)")
    if not value.lower().startswith("http"):
        value = "https://" + value
    return value


def _join_bullets(bullets: list[str]) -> str:
    """Join bullets into prose, ending each one cleanly."""
    parts: list[str] = []
    for bullet in bullets:
        cleaned = " ".join(bullet.split()).strip()
        if not cleaned:
            continue
        if not cleaned.endswith((".", "!", "?")):
            cleaned += "."
        parts.append(cleaned)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Entry grouping
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class Entry:
    """A heading (one or two lines) plus the bullets that belong to it."""

    header: list[Line] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)

    @property
    def blob(self) -> str:
        return " ".join([line.blob for line in self.header] + self.bullets)


def _is_wrap(previous: Line, line: Line, full_width: int) -> bool:
    """Is ``line`` the wrapped tail of ``previous`` rather than new content?

    ``full_width`` is the widest line in the section. A line that stopped well
    short of the right margin ended because its content ended, so what follows
    is new content - that is what separates two short certification lines from
    one sentence wrapped across the page.
    """
    if previous.extra_cells or line.extra_cells or line.has_date_cell:
        return False
    if ITEM_LABEL_RE.match(line.text) or HEADER_LABEL_RE.match(line.text):
        return False
    previous_text = previous.text.rstrip()
    if previous_text.endswith(("-", "–", "—", ",")):
        return True
    if line.text[:1].islower():
        return True
    if SENTENCE_END_RE.search(previous_text) or previous_text.endswith(")"):
        return False
    return full_width > 0 and len(previous_text) >= 0.85 * full_width


def _full_width(lines: list[Line]) -> int:
    return max((len(line.blob) + line.indent for line in lines), default=0)


def group_entries(
    lines: list[Line],
    *,
    bullet_starts_entry: bool = False,
    label_starts_entry: bool = False,
    max_header_lines: int = MAX_HEADER_LINES,
) -> list[Entry]:
    """Group one section's lines into entries.

    ``bullet_starts_entry`` is for list sections (achievements), where an
    unheaded bullet is itself an item. In entry sections a bullet is always a
    detail of the heading above it. ``label_starts_entry`` makes a
    ``"1st Place: ..."`` line open a new item instead of becoming a second
    heading line.
    """
    if not lines:
        return []

    # The section's left margin, measured over every line: a section made
    # entirely of bullets still has continuations indented past them.
    base_indent = min(line.indent for line in lines)
    full_width = _full_width(lines)

    entries: list[Entry] = []
    current: Entry | None = None

    for line in lines:
        if line.is_bullet:
            if current is None or (bullet_starts_entry and not current.header):
                current = Entry()
                entries.append(current)
            current.bullets.append(line.text)
            current.urls.extend(line.urls)
            continue

        # Indented past the heading column: a wrapped continuation.
        if current is not None and line.indent > base_indent + 1:
            _absorb_continuation(current, line)
            continue

        if current is not None and not current.bullets and current.header:
            if _is_wrap(current.header[-1], line, full_width):
                _absorb_continuation(current, line)
                continue
            starts_item = label_starts_entry and bool(ITEM_LABEL_RE.match(line.text))
            if (
                not starts_item
                and len(current.header) < max_header_lines
                and not (line.has_date_cell and current.header[0].has_date_cell)
            ):
                current.header.append(line)
                current.urls.extend(line.urls)
                continue

        current = Entry(header=[line], urls=list(line.urls))
        entries.append(current)

    for entry in entries:
        entry.urls = _dedupe(entry.urls)
    return [entry for entry in entries if entry.header or entry.bullets]


def _absorb_continuation(entry: Entry, line: Line) -> None:
    """Fold a wrapped line back into whatever it continues."""
    entry.urls.extend(line.urls)
    if entry.bullets:
        entry.bullets[-1] = _dehyphenate(entry.bullets[-1], line.text)
    elif entry.header:
        last = entry.header[-1]
        last.text = _dehyphenate(last.text, line.text)
        last.extra_cells.extend(line.extra_cells)
    else:  # pragma: no cover - defensive
        entry.header.append(line)


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


def extract_contact(text: str, sections: dict[str, list[Line]]) -> dict[str, Any]:
    header_lines = sections.get("header", [])
    head = "\n".join(line.blob for line in header_lines[:12]) or text[:800]
    emails = EMAIL_RE.findall(text)
    phones = [p for p in PHONE_RE.findall(text[:2000]) if len(re.sub(r"\D", "", p)) >= 10]

    github_candidates = [m.group(0) for m in GITHUB_RE.finditer(text)]
    profile_github = [m for m in github_candidates if GITHUB_PROFILE_RE.match(m)]
    linkedin_candidates = [m.group(0) for m in LINKEDIN_RE.finditer(text)]

    name: str | None = None
    for line in header_lines[:5]:
        candidate = line.text.strip()
        if EMAIL_RE.search(candidate) or URL_RE.search(candidate) or line.extra_cells:
            continue
        words = candidate.split()
        if 1 < len(words) <= 5 and all(
            re.fullmatch(r"[A-Za-z.'-]+", word) for word in words
        ):
            name = " ".join(word.title() if word.isupper() else word for word in words)
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


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------
def _skill_tokens(body: str) -> list[str]:
    tokens: list[str] = []
    for token in _split_list(body):
        token = token.strip(" .-")
        if not token or token.isdigit() or len(token) > 48:
            continue
        # A sentence is not a skill.
        if len(token.split()) > 5:
            continue
        if len(token) > 1 or token.upper() in ("C", "R"):
            tokens.append(token)
    return tokens


def extract_skills(
    sections: dict[str, list[Line]], catalogue: dict[str, str]
) -> tuple[dict[str, Any], list[str]]:
    """Skills from the skills section plus catalogue hits anywhere in the text.

    Returns ``(skills, certification_lines)``: a "Certifications & Courses:"
    line inside a skills block is a certification list, not a skill list.
    """
    declared: list[str] = []
    certification_lines: list[str] = []

    # A skills block wraps like any other: "Certifications & Courses: ..." can
    # run over three lines, and splitting them apart turns one course list into
    # a handful of invented skills.
    for entry in group_entries(
        sections.get("skills", []), bullet_starts_entry=True, label_starts_entry=True
    ):
        body = _entry_text(entry)
        label = ""
        if ":" in body and len(body.split(":", 1)[0]) < 48:
            label, body = body.split(":", 1)
        if NON_SKILL_LABEL_RE.match(label.strip()):
            certification_lines.append(body.strip())
            continue
        declared.extend(_skill_tokens(body))

    full_text = " \n".join(
        line.blob for block in sections.values() for line in block
    ).lower()

    catalogue_hits: list[str] = []
    for needle, canonical in catalogue.items():
        if len(needle) < 2:
            continue
        pattern = r"(?<![a-z0-9+#])" + re.escape(needle) + r"(?![a-z0-9+#])"
        if re.search(pattern, full_text):
            catalogue_hits.append(canonical)

    declared_clean = _dedupe(declared, 60)
    return (
        {
            "declared": declared_clean,
            "catalogue_matches": _dedupe(catalogue_hits, 60),
            "all": _dedupe(declared_clean + catalogue_hits, 80),
        },
        certification_lines,
    )


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------
def _score_from(blob: str, cells: list[str]) -> tuple[float | None, str | None, float | None]:
    for candidate in [*cells, blob]:
        cgpa = CGPA_RE.search(candidate)
        if cgpa:
            scale = float(cgpa.group(2)) if cgpa.group(2) else None
            return float(cgpa.group(1)), "cgpa", scale
        bare = BARE_SCORE_RE.match(candidate.strip())
        if bare:
            return float(bare.group(1)), "cgpa", float(bare.group(2))
        percent = PERCENT_RE.search(candidate)
        if percent:
            return float(percent.group(1)), "percentage", 100.0
    return None, None, None


def extract_education(sections: dict[str, list[Line]], text: str) -> list[dict[str, Any]]:
    lines = sections.get("education", [])
    entries: list[dict[str, Any]] = []
    buffer: list[Line] = []

    def flush() -> None:
        if not buffer:
            return
        blob = " ".join(line.blob for line in buffer)
        cells = [cell for line in buffer for cell in line.extra_cells]
        degree_match = DEGREE_RE.search(blob)
        institution_line = next(
            (line for line in buffer if INSTITUTION_HINT_RE.search(line.text)), buffer[0]
        )
        # The line that is not the institution names the programme in the
        # student's own words ("Minor in Corporate Finance and Investment
        # Banking"), which is more useful than the matched degree token alone.
        program = next(
            (
                _strip_duration(re.split(r"\s*\|\s*", line.text)[0])
                for line in buffer
                if line is not institution_line and DEGREE_RE.search(line.text)
            ),
            None,
        )
        score, score_type, scale = _score_from(blob, cells)
        years = [int(m.group(0)) for m in YEAR_RE.finditer(blob)]
        duration = next((line.duration for line in buffer if line.duration), None)
        is_current = bool(
            duration and re.match(r"present|current|ongoing|now|date", duration.group(2), re.I)
        )
        entry = {
            "raw": _clean(blob)[:400],
            "degree": _clean(degree_match.group(0)) if degree_match else None,
            "program": program,
            "institution": _strip_duration(institution_line.text) or None,
            "score": score,
            "score_type": score_type,
            "score_scale": scale,
            "start_year": min(years) if years else None,
            "end_year": None if is_current else (max(years) if years else None),
            "is_current": is_current,
        }
        if entry["degree"] or entry["institution"] or entry["score"]:
            entries.append(entry)
        buffer.clear()

    width = _full_width(lines)
    for line in lines:
        if buffer and not _is_wrap(buffer[-1], line, width):
            # A new institution, or a third line, starts a new row.
            if INSTITUTION_HINT_RE.search(line.text) or len(buffer) >= 2:
                flush()
        buffer.append(line)
    flush()

    grad = GRAD_YEAR_RE.search(text)
    if grad:
        for entry in entries:
            entry.setdefault("graduation_year", int(grad.group(1)))
    return entries[:8]


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
def _entry_dates(entry: Entry) -> tuple[str | None, str | None, str | None]:
    """``(duration_text, start_raw, end_raw)`` from the entry's heading."""
    for line in entry.header:
        duration = line.duration
        if duration:
            return duration.group(0), duration.group(1), duration.group(2)
    for line in entry.header:
        single = line.single_date
        if single:
            return single, single, None
    duration = DURATION_RE.search(entry.blob)
    if duration:
        return duration.group(0), duration.group(1), duration.group(2)
    return None, None, None


def _inline_tech(entry: Entry) -> list[str]:
    for line in entry.header:
        match = TECH_INLINE_RE.search(line.blob)
        if match:
            return _split_list(match.group(1))
    return []


def _substance(bullets: list[str], tech: list[str], description: str, links: list[str]) -> float:
    """How much real content an entry carries, for ranking - not for scoring."""
    score = 0.0
    score += min(len(bullets), 4) * 1.0
    score += min(len(tech), 6) * 0.25
    score += min(len(description) / 300.0, 2.0)
    score += min(len(METRIC_RE.findall(description)), 4) * 0.5
    if links:
        score += 0.5
    return round(score, 2)


def extract_projects(sections: dict[str, list[Line]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for entry in group_entries(sections.get("projects", [])):
        if not entry.header:
            continue
        primary = entry.header[0]
        duration, start_raw, end_raw = _entry_dates(entry)

        heading = _strip_duration(primary.text)
        segments = [seg for seg in re.split(r"\s*\|\s*", heading) if seg.strip()]
        # "VyapariOne - Inventory Platform Github" ends with a link anchor, but
        # "Collaborative VS Code" ends with part of its own name, so the anchor
        # is only stripped from the end of the title segment.
        title = _clean(LINK_WORD_RE.sub(" ", segments[0])) if segments else ""

        tech: list[str] = []
        for segment in segments[1:]:
            tech.extend(_split_list(segment))
        tech.extend(_inline_tech(entry))

        # A second heading line is the client, organisation or subtitle - it is
        # context for the project, never part of its name.
        subtitle_lines = [
            _strip_duration(line.text)
            for line in entry.header[1:]
            if not HEADER_LABEL_RE.match(line.text)
        ]
        subtitle = next((s for s in subtitle_lines if s), None)

        description = _join_bullets(entry.bullets)
        if not description and subtitle:
            description = subtitle
            subtitle = None

        if not title or _is_fragment(title):
            continue
        # A title on its own is not a project record.
        if not entry.bullets and not tech and not subtitle and not duration:
            continue

        key = title.lower()
        if key in seen:
            continue
        seen.add(key)

        urls = _dedupe(entry.urls, 4)
        github = next((url for url in urls if "github.com" in url.lower()), None)
        results.append(
            {
                "title": title[:180],
                "organization": (subtitle or None),
                "description": (description or title)[:1500],
                "technologies": _dedupe(tech, 15),
                "links": urls,
                "github_url": github,
                "live_url": next((url for url in urls if url != github), None),
                "duration": duration,
                "start_raw": start_raw,
                "end_raw": end_raw,
                "highlights": entry.bullets[:10],
                "substance": _substance(entry.bullets, tech, description, urls),
            }
        )

    ranked = sorted(results, key=lambda item: item["substance"], reverse=True)
    primary_titles = {item["title"] for item in ranked[:PRIMARY_PROJECT_COUNT]}
    for item in results:
        item["is_primary"] = item["title"] in primary_titles
    return results[:12]


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------
def _experience_type(section: str, title: str, organization: str, blob: str) -> str:
    lowered = f"{title} {blob}".lower()
    if section == "positions":
        # Leadership and volunteering are never employment, whatever the
        # wording - they are classified only within those two kinds.
        if VOLUNTEER_HINT_RE.search(lowered):
            return "extracurricular"
        return "position_of_responsibility"
    if INTERN_HINT_RE.search(lowered):
        return "internship"
    if LEADERSHIP_HINT_RE.search(title.lower()):
        # A student body, college or committee is not an employer, so a
        # leadership title there is a position of responsibility even when it
        # sits under a generic "Experience" heading.
        if BODY_HINT_RE.search(organization) or INSTITUTION_HINT_RE.search(organization):
            return "position_of_responsibility"
        if not COMPANY_SUFFIX_RE.search(organization):
            return "position_of_responsibility"
    return "job"


def _role_score(value: str) -> int:
    return len(ROLE_TITLE_HINT_RE.findall(value))


def _org_score(value: str) -> int:
    return (
        len(COMPANY_SUFFIX_RE.findall(value))
        + len(INSTITUTION_HINT_RE.findall(value))
        + len(BODY_HINT_RE.findall(value))
    )


def _pick_org_segment(value: str) -> tuple[str, str]:
    """Split ``"SPJIMR | Under Prof. X"`` into the organisation and the rest."""
    segments = [_clean(part) for part in re.split(r"\s*[|–—]\s*", value) if _clean(part)]
    if len(segments) < 2:
        return _clean(value), ""
    best = max(segments, key=_org_score)
    if _org_score(best) == 0:
        best = segments[0]
    rest = " ".join(seg for seg in segments if seg != best)
    return best, rest


def _split_role_and_org(text: str) -> tuple[str, str | None]:
    """Split a single heading line that carries both a role and an employer.

    ``"Volunteer - Abhyudaya, SPJIMR"`` is a role and an organisation even
    though the organisation name carries no company or committee word.
    """
    for separator in (r"\s+[–—]\s+", r"\s+-\s+", r"\s*\|\s*", r",\s+"):
        parts = [_clean(part) for part in re.split(separator, text, maxsplit=1) if _clean(part)]
        if len(parts) != 2:
            continue
        if _role_score(parts[0]) and (_org_score(parts[1]) or not _role_score(parts[1])):
            return parts[0], parts[1]
    return _clean(text), None


def _pick_title_index(candidates: list[str]) -> int:
    """Which heading line is the role, given the other is the organisation.

    Resumes disagree on the order: some print the employer first, some the
    role. Scoring both lines on role words minus organisation words settles it
    without assuming either layout; ties keep the printed order.
    """
    differentials = [_role_score(c) - _org_score(c) for c in candidates]
    best = max(range(len(candidates)), key=lambda i: differentials[i])
    return best if differentials[best] > differentials[0] else 0


def _experience_from_entry(entry: Entry, section: str) -> dict[str, Any] | None:
    header_lines = [line for line in entry.header if not HEADER_LABEL_RE.match(line.text)]
    label_lines = [line for line in entry.header if HEADER_LABEL_RE.match(line.text)]
    if not header_lines:
        return None

    duration, start_raw, end_raw = _entry_dates(entry)
    candidates = [_strip_duration(line.text) for line in header_lines[:MAX_HEADER_LINES]]
    candidates = [c for c in candidates if c]
    if not candidates:
        return None

    title: str
    organization: str | None
    if len(candidates) >= 2:
        index = _pick_title_index(candidates[:2])
        title = candidates[index]
        organization = candidates[1 - index]
        organization, trailing = _pick_org_segment(organization)
    else:
        title, organization = _split_role_and_org(candidates[0])
        trailing = ""
        if organization:
            organization, extra = _pick_org_segment(organization)
            trailing = extra

    title = _clean(LINK_WORD_RE.sub(" ", title))
    if not title or _is_fragment(title):
        return None

    # A role line can carry its own location column ("Intern | Remote").
    notes = [note for line in header_lines for note in line.notes]
    location = next(
        (
            note
            for note in notes
            if len(note) <= 40
            and not INSTITUTION_HINT_RE.search(note)
            and (WORK_MODE_RE.match(note) or len(note.split()) <= 3)
        ),
        None,
    )
    context = [note for note in notes if note != location]
    if trailing:
        context.append(trailing)

    description_bits = [*entry.bullets]
    for line in label_lines:
        if not TECH_INLINE_RE.match(line.text):
            description_bits.append(line.text)
    description = _join_bullets(description_bits)
    if not description and context:
        description = _join_bullets(context)

    skills_used = _inline_tech(entry)

    if not organization:
        organization = next((c for c in context if _org_score(c)), None) or title
    organization = _clean(organization)[:180] or title[:180]

    return {
        "title": title[:180],
        "organization": organization,
        "experience_type": _experience_type(section, title, organization, entry.blob),
        "description": description[:2000] or None,
        "location": location,
        "duration": duration,
        "start_raw": start_raw,
        "end_raw": end_raw,
        "skills_used": _dedupe(skills_used, 15),
        "highlights": entry.bullets[:10],
        "source_section": section,
    }


def extract_experience(sections: dict[str, list[Line]]) -> list[dict[str, Any]]:
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
def _entry_text(entry: Entry) -> str:
    parts = [_clean(line.text) for line in entry.header if _clean(line.text)]
    parts += [_clean(bullet) for bullet in entry.bullets if _clean(bullet)]
    return " ".join(parts)


def extract_certifications(
    sections: dict[str, list[Line]], extra_lines: list[str]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    raw_items: list[str] = []
    # Two certifications printed on consecutive lines are two records, so a
    # certification entry never takes a second heading line.
    for entry in group_entries(
        sections.get("certifications", []),
        bullet_starts_entry=True,
        label_starts_entry=True,
        max_header_lines=1,
    ):
        raw_items.append(_entry_text(entry))
    raw_items.extend(extra_lines)

    for raw in raw_items:
        # "Udemy - A; CFI - B, C" is a list of certifications, not one.
        for chunk in [part.strip() for part in raw.split(";") if part.strip()]:
            cleaned = _clean(chunk)
            if len(cleaned) < 4:
                continue
            parts = [
                _clean(part)
                for part in re.split(r"\s*[|–—]\s*|\s+-\s+|,\s*by\s+", cleaned)
                if _clean(part)
            ]
            year = YEAR_RE.search(cleaned)
            # "Udemy - The Complete Investment Banking 2026" names the issuer
            # first; the certification is the substantive half.
            named = [p for p in parts if not YEAR_RE.fullmatch(p) and len(p) > 2]
            name = (max(named, key=len) if named else cleaned)[:200]
            issuer = next(
                (part for part in named if part != name and len(part) <= 60),
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
                    "raw": cleaned[:300],
                }
            )
    return out[:15]


def _achievement_category(text: str) -> str:
    lowered = text.lower()
    if re.search(
        r"hackathon|contest|competition|rank|winner|runner|olympiad|case\s+comp|finalist|"
        r"1st|2nd|3rd|first\s+place|second\s+place|third\s+place|pitch",
        lowered,
    ):
        return "competition"
    if re.search(r"scholar|topper|dean|merit|gold\s+medal|academic|rank\s+\d|percentile", lowered):
        return "academic"
    if re.search(r"club|sport|ncc|nss|volunteer|cultural|music|drama|debate", lowered):
        return "extracurricular"
    return "other"


def extract_achievements(sections: dict[str, list[Line]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    for entry in group_entries(
        sections.get("achievements", []), bullet_starts_entry=True, label_starts_entry=True
    ):
        if not entry.header and not entry.bullets:
            continue
        heading = _clean(entry.header[0].text) if entry.header else _clean(entry.bullets[0])
        detail_lines = [_clean(line.text) for line in entry.header[1:]]
        detail_lines += [_clean(bullet) for bullet in entry.bullets]
        scope = next(
            (note for line in entry.header for note in line.notes if len(note) <= 60), None
        )

        # "First Place: A; B; C" is three awards sharing one prefix.
        label_match = ITEM_LABEL_RE.match(heading)
        chunks: list[tuple[str, str]] = []
        if label_match and ";" in heading:
            prefix, body = heading.split(":", 1)
            for piece in body.split(";"):
                piece = _clean(piece)
                if piece:
                    chunks.append((f"{_clean(prefix)}: {piece}", ""))
        else:
            chunks.append((heading, " ".join(detail_lines)))

        for title_text, detail in chunks:
            title_text = _clean(title_text)
            if len(title_text) < 5:
                continue
            key = title_text.lower()[:120]
            if key in seen:
                continue
            seen.add(key)
            full = " ".join(filter(None, [title_text, detail]))
            year = YEAR_RE.search(full)
            # A run-on award line keeps its full text as the description so
            # nothing is lost to the title's length cap.
            if len(title_text) > 200 and not detail:
                detail = title_text
            out.append(
                {
                    "title": title_text[:200],
                    "description": (detail or None),
                    "category": _achievement_category(full),
                    "scope": scope,
                    "year": int(year.group(0)) if year else None,
                }
            )
    return out[:20]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def parse_resume(text: str, catalogue: dict[str, str]) -> dict[str, Any]:
    """Full deterministic parse. ``catalogue`` is lowercase name/alias -> display name."""
    text = text[:MAX_TEXT_CHARS]
    raw_lines = text.split("\n")
    lines = read_lines(raw_lines)
    sections = split_sections(lines)
    sections_found = [
        name for name in sections if name != "header" and sections[name]
    ]

    skills, certification_lines = extract_skills(sections, catalogue)
    projects = extract_projects(sections)
    experience = extract_experience(sections)

    words = re.findall(r"[A-Za-z][A-Za-z'+#.-]*", text)
    bullet_count = sum(1 for line in lines if line.is_bullet)
    lowered = text.lower()

    return {
        "contact": extract_contact(text, sections),
        "skills": skills,
        "education": extract_education(sections, text),
        "projects": projects,
        "experience": experience,
        "certifications": extract_certifications(sections, certification_lines),
        "achievements": extract_achievements(sections),
        "sections_found": sections_found,
        "stats": {
            "word_count": len(words),
            "line_count": len(lines),
            "bullet_count": bullet_count,
            "action_verbs_used": sorted({v for v in ACTION_VERBS if v in lowered}),
            "quantified_statements": len(METRIC_RE.findall(text)),
            "character_count": len(text),
        },
    }
