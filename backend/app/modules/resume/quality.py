"""Resume quality scoring.

Deterministic and fully explainable: every point is attached to a named check
so the dashboard can state why a resume scored what it did.
"""

from __future__ import annotations

from typing import Any

EXPECTED_SECTIONS = ("education", "skills", "projects", "experience")
NICE_TO_HAVE_SECTIONS = ("certifications", "achievements", "summary")

IDEAL_WORD_RANGE = (300, 900)


def build_quality_report(parsed: dict[str, Any]) -> dict[str, Any]:
    stats = parsed.get("stats", {})
    contact = parsed.get("contact", {})
    sections_found = set(parsed.get("sections_found", []))

    checks: list[dict[str, Any]] = []

    def check(key: str, label: str, earned: float, possible: float, detail: str) -> None:
        checks.append(
            {
                "key": key,
                "label": label,
                "earned": round(earned, 1),
                "possible": possible,
                "passed": earned >= possible * 0.75,
                "detail": detail,
            }
        )

    # --- 1. Core sections (32) ---
    present_core = [s for s in EXPECTED_SECTIONS if s in sections_found]
    check(
        "core_sections",
        "Core sections present",
        32 * len(present_core) / len(EXPECTED_SECTIONS),
        32,
        f"Found {len(present_core)} of {len(EXPECTED_SECTIONS)}: "
        + (", ".join(present_core) or "none"),
    )

    # --- 2. Supporting sections (8) ---
    present_nice = [s for s in NICE_TO_HAVE_SECTIONS if s in sections_found]
    check(
        "supporting_sections",
        "Supporting sections",
        8 * min(len(present_nice) / 2, 1.0),
        8,
        f"Found: {', '.join(present_nice) or 'none'}",
    )

    # --- 3. Contact completeness (12) ---
    contact_points = 0.0
    contact_bits: list[str] = []
    if contact.get("email"):
        contact_points += 5
        contact_bits.append("email")
    if contact.get("phone"):
        contact_points += 3
        contact_bits.append("phone")
    if contact.get("linkedin_url"):
        contact_points += 2
        contact_bits.append("LinkedIn")
    if contact.get("github_url") or contact.get("other_urls"):
        contact_points += 2
        contact_bits.append("portfolio/GitHub")
    check(
        "contact",
        "Contact details",
        contact_points,
        12,
        f"Detected: {', '.join(contact_bits) or 'none'}",
    )

    # --- 4. Length (10) ---
    word_count = int(stats.get("word_count", 0))
    low, high = IDEAL_WORD_RANGE
    if word_count == 0:
        length_points = 0.0
        length_detail = "No readable text."
    elif word_count < low:
        length_points = 10 * (word_count / low)
        length_detail = f"{word_count} words - thin for a placement resume (aim for {low}+)."
    elif word_count <= high:
        length_points = 10.0
        length_detail = f"{word_count} words - well within the ideal range."
    else:
        length_points = max(5.0, 10 - (word_count - high) / 200)
        length_detail = f"{word_count} words - consider trimming to under {high}."
    check("length", "Resume length", length_points, 10, length_detail)

    # --- 5. Bullet formatting (8) ---
    bullets = int(stats.get("bullet_count", 0))
    check(
        "bullets",
        "Bullet-point formatting",
        8 * min(bullets / 10, 1.0),
        8,
        f"{bullets} bullet lines detected.",
    )

    # --- 6. Action verbs (12) ---
    verbs = stats.get("action_verbs_used", []) or []
    check(
        "action_verbs",
        "Strong action verbs",
        12 * min(len(verbs) / 6, 1.0),
        12,
        f"{len(verbs)} distinct action verbs" + (f" ({', '.join(verbs[:6])})" if verbs else ""),
    )

    # --- 7. Quantified impact (10) ---
    metrics = int(stats.get("quantified_statements", 0))
    check(
        "quantified_impact",
        "Quantified impact",
        10 * min(metrics / 4, 1.0),
        10,
        f"{metrics} statements include a number or percentage.",
    )

    # --- 8. Evidence depth (8) ---
    project_count = len(parsed.get("projects", []) or [])
    experience_count = len(parsed.get("experience", []) or [])
    depth = min((project_count + experience_count) / 4, 1.0)
    check(
        "evidence_depth",
        "Projects and experience detail",
        8 * depth,
        8,
        f"{project_count} projects and {experience_count} experience entries parsed.",
    )

    earned = sum(item["earned"] for item in checks)
    possible = sum(item["possible"] for item in checks)
    score = round(100 * earned / possible, 1) if possible else 0.0

    strengths = [item["label"] for item in checks if item["passed"]]
    improvements = [
        _improvement_copy(item) for item in checks if not item["passed"]
    ]

    return {
        "score": score,
        "checks": checks,
        "strengths": strengths,
        "improvements": improvements,
        "sections_found": sorted(sections_found),
        "sections_missing": [
            s
            for s in EXPECTED_SECTIONS + NICE_TO_HAVE_SECTIONS
            if s not in sections_found
        ],
        "word_count": word_count,
    }


def _improvement_copy(item: dict[str, Any]) -> str:
    key = item["key"]
    copy = {
        "core_sections": "Add the missing core sections (Education, Skills, Projects, Experience) with clear headings.",
        "supporting_sections": "Add a Certifications or Achievements section to show depth beyond coursework.",
        "contact": "Include email, phone, LinkedIn and a GitHub or portfolio link in the header.",
        "length": "Expand each project and internship with 2-3 outcome-focused bullets.",
        "bullets": "Convert long paragraphs into concise bullet points - recruiters scan, they do not read.",
        "action_verbs": "Start bullets with action verbs such as built, designed, analysed, automated or led.",
        "quantified_impact": "Quantify outcomes: users served, accuracy gained, hours saved, percentage improved.",
        "evidence_depth": "Describe at least 2 projects and 1 internship in detail.",
    }
    return copy.get(key, item["label"])


def missing_role_keywords(
    resume_text: str | None, keywords: list[str]
) -> list[dict[str, Any]]:
    """Which of a role's expected keywords never appear in the resume."""
    if not keywords:
        return []
    lowered = (resume_text or "").lower()
    out: list[dict[str, Any]] = []
    for keyword in keywords:
        present = keyword.lower() in lowered if lowered else False
        out.append({"keyword": keyword, "present": present})
    return out
