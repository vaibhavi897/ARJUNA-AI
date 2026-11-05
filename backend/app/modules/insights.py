"""Personalised narrative generation.

Everything here is computed from the student's own stored data. When no LLM
provider key is configured the output is deterministic and labelled
``rule_based`` - the UI reports the mode honestly rather than implying a model
is running.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from app.core.config import settings


def ai_mode() -> str:
    """``llm_assisted`` only if a provider key is actually present."""
    return "llm_assisted" if settings.llm_enabled else "rule_based"


def _time_greeting(now: dt.datetime) -> str:
    hour = now.hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def build_greeting(
    *,
    full_name: str,
    profile_completion: int,
    role_scores: list[dict[str, Any]],
    roadmap_pending: int,
    roadmap_completed: int,
    now: dt.datetime | None = None,
) -> str:
    """One personalised line that always references real numbers."""
    now = now or dt.datetime.now()
    first_name = full_name.split()[0] if full_name else "there"
    opener = f"{_time_greeting(now)}, {first_name}."

    if not role_scores:
        return (
            f"{opener} Your profile is {profile_completion}% complete - finish onboarding "
            "to unlock your role-wise readiness scores."
        )

    best = max(role_scores, key=lambda r: r["score"])
    improved = [r for r in role_scores if (r.get("score_delta") or 0) > 0]

    parts = [opener, f"{best['role_name']} is your strongest fit at {best['score']}/100."]

    if improved:
        top_gain = max(improved, key=lambda r: r["score_delta"])
        parts.append(
            f"{top_gain['role_name']} is up {top_gain['score_delta']} points since your last assessment."
        )
    elif roadmap_completed:
        parts.append(f"You have completed {roadmap_completed} roadmap action(s) so far.")

    if roadmap_pending:
        parts.append(f"{roadmap_pending} recommended action(s) are waiting.")
    elif profile_completion < 100:
        parts.append(f"Your profile is {profile_completion}% complete.")

    return " ".join(parts)


def build_ai_insights(
    *,
    role_scores: list[dict[str, Any]],
    domain_averages: list[dict[str, Any]],
    skills_total: int,
    skills_evidence_backed: int,
    projects_count: int,
    internships_count: int,
    resume_present: bool,
    resume_quality: float | None,
    profile_completion: int,
    roadmap_pending: int,
    top_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Cross-cutting observations about the profile as a whole."""
    insights: list[dict[str, Any]] = []

    # 1. Cross-domain comparison, e.g. technical vs finance strength.
    if len(domain_averages) >= 2:
        ranked = sorted(domain_averages, key=lambda d: d["average_score"], reverse=True)
        best, worst = ranked[0], ranked[-1]
        spread = round(best["average_score"] - worst["average_score"], 1)
        if spread >= 8:
            body = (
                f"Your {best['domain_name']} profile averages {best['average_score']}/100 "
                f"while {worst['domain_name']} averages {worst['average_score']}/100 - a "
                f"{spread}-point spread."
            )
            if top_gaps:
                body += (
                    f" The quickest way to close it is {top_gaps[0]['skill_name']}"
                    f" ({top_gaps[0].get('status', 'gap').replace('_', ' ')})."
                )
            insights.append(
                {
                    "kind": "domain_comparison",
                    "title": f"{best['domain_name']} is ahead of {worst['domain_name']}",
                    "body": body,
                    "severity": "medium",
                }
            )

    # 2. Claim vs evidence balance.
    if skills_total:
        claimed_only = skills_total - skills_evidence_backed
        ratio = skills_evidence_backed / skills_total
        if claimed_only and ratio < 0.5:
            insights.append(
                {
                    "kind": "evidence_gap",
                    "title": f"{claimed_only} of {skills_total} skills are unproven",
                    "body": (
                        "Only "
                        f"{skills_evidence_backed} of your {skills_total} listed skills appear in "
                        "a project or internship. Scoring weights demonstrated skills far more "
                        "heavily than claimed ones, so building with what you already list is "
                        "usually faster than adding new skills."
                    ),
                    "severity": "high",
                }
            )
        elif ratio >= 0.7:
            insights.append(
                {
                    "kind": "evidence_strength",
                    "title": "Your skill claims are well evidenced",
                    "body": (
                        f"{skills_evidence_backed} of {skills_total} skills are backed by real "
                        "work. That is exactly what interviewers probe for."
                    ),
                    "severity": "low",
                }
            )

    # 3. Portfolio shape.
    if projects_count == 0:
        insights.append(
            {
                "kind": "portfolio",
                "title": "No projects on your profile yet",
                "body": (
                    "Projects carry the practical-evidence weight in every role rubric. "
                    "One well-documented project changes several scores at once."
                ),
                "severity": "high",
            }
        )
    elif internships_count == 0 and projects_count >= 3:
        insights.append(
            {
                "kind": "portfolio",
                "title": "Strong project work, no internship yet",
                "body": (
                    f"{projects_count} projects give you material to talk about. Converting that "
                    "into one internship would lift the experience component across every role."
                ),
                "severity": "medium",
            }
        )

    # 4. Resume.
    if not resume_present:
        insights.append(
            {
                "kind": "resume",
                "title": "Resume not analysed yet",
                "body": (
                    "Upload a PDF or DOCX resume to unlock keyword analysis, quality scoring "
                    "and the resume component of every role score."
                ),
                "severity": "high",
            }
        )
    elif resume_quality is not None and resume_quality < 60:
        insights.append(
            {
                "kind": "resume",
                "title": f"Resume quality is {resume_quality}/100",
                "body": (
                    "Most of the lost points come from formatting and impact rather than "
                    "content - quantified bullets and action verbs move this quickly."
                ),
                "severity": "medium",
            }
        )

    # 5. Momentum / next action.
    if role_scores:
        improving = [r for r in role_scores if (r.get("score_delta") or 0) > 0]
        declining = [r for r in role_scores if (r.get("score_delta") or 0) < 0]
        if improving:
            top = max(improving, key=lambda r: r["score_delta"])
            insights.append(
                {
                    "kind": "momentum",
                    "title": f"{top['role_name']} improved by {top['score_delta']} points",
                    "body": "Your last profile update moved this score. Keep the same pattern going.",
                    "severity": "low",
                }
            )
        elif declining:
            top = min(declining, key=lambda r: r["score_delta"])
            insights.append(
                {
                    "kind": "momentum",
                    "title": f"{top['role_name']} dropped by {abs(top['score_delta'])} points",
                    "body": (
                        "A score can fall when entries are removed or when a new target role "
                        "has a stricter rubric. Open the role breakdown to see which component changed."
                    ),
                    "severity": "medium",
                }
            )

    if profile_completion < 80:
        insights.append(
            {
                "kind": "completeness",
                "title": f"Profile is {profile_completion}% complete",
                "body": (
                    "Incomplete sections leave rubric components at zero or neutral. "
                    "Completing them is the cheapest score improvement available."
                ),
                "severity": "medium",
            }
        )

    if roadmap_pending:
        insights.append(
            {
                "kind": "roadmap",
                "title": f"{roadmap_pending} roadmap action(s) pending",
                "body": "Each action lists the role it helps and the points at stake.",
                "severity": "low",
            }
        )

    return insights[:7]
