"""Generate DOCX resumes for demo students.

The seeded resumes are produced from each demo student's own seeded data and
then pushed through the real extraction/parsing pipeline, so resume insights in
the demo are genuine parser output rather than canned text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_docx_resume(student: dict[str, Any], destination: Path) -> Path:
    """Write a plausible one-page resume for a demo student."""
    import docx
    from docx.shared import Pt

    document = docx.Document()
    style = document.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    profile = student["profile"]

    heading = document.add_paragraph()
    run = heading.add_run(student["full_name"])
    run.bold = True
    run.font.size = Pt(18)

    contact_bits = [
        student["email"],
        profile.get("phone"),
        profile.get("location"),
        profile.get("linkedin_url"),
        profile.get("github_url"),
    ]
    document.add_paragraph(" | ".join(bit for bit in contact_bits if bit))

    if profile.get("bio"):
        document.add_paragraph("SUMMARY")
        document.add_paragraph(profile["bio"])

    # --- Education ---
    document.add_paragraph("EDUCATION")
    for entry in student.get("academics", []):
        score = entry.get("score")
        score_text = ""
        if score is not None:
            score_text = (
                f"CGPA: {score}/10"
                if entry.get("score_type") == "cgpa"
                else f"Percentage: {score}%"
            )
        line = f"{entry['institution']} - {entry.get('degree_or_program') or ''}"
        document.add_paragraph(line.strip(" -"))
        tail = [
            entry.get("board_or_university"),
            f"{entry.get('start_year') or ''} - {entry.get('end_year') or ''}".strip(" -"),
            score_text,
        ]
        document.add_paragraph(" | ".join(bit for bit in tail if bit))
        if entry.get("relevant_coursework"):
            document.add_paragraph(
                "Relevant coursework: " + ", ".join(entry["relevant_coursework"])
            )

    # --- Skills ---
    document.add_paragraph("SKILLS")
    document.add_paragraph(", ".join(name for name, _ in student.get("skills", [])))

    # --- Projects ---
    if student.get("projects"):
        document.add_paragraph("PROJECTS")
        for project in student["projects"]:
            title = document.add_paragraph()
            title_run = title.add_run(project["title"])
            title_run.bold = True
            if project.get("technologies"):
                document.add_paragraph(
                    "Technologies used: " + ", ".join(project["technologies"])
                )
            for sentence in _bullets(project.get("description", "")):
                document.add_paragraph(sentence, style="List Bullet")
            if project.get("contribution"):
                document.add_paragraph(project["contribution"], style="List Bullet")

    # --- Experience ---
    experiences = [
        exp
        for exp in student.get("experiences", [])
        if exp["experience_type"] in ("internship", "job")
    ]
    if experiences:
        document.add_paragraph("EXPERIENCE")
        for exp in experiences:
            header = document.add_paragraph()
            header_run = header.add_run(f"{exp['title']} | {exp['organization']}")
            header_run.bold = True
            if exp.get("duration_months"):
                document.add_paragraph(f"Duration: {exp['duration_months']} months")
            for sentence in _bullets(exp.get("description", "")):
                document.add_paragraph(sentence, style="List Bullet")

    positions = [
        exp
        for exp in student.get("experiences", [])
        if exp["experience_type"] == "position_of_responsibility"
    ]
    if positions:
        document.add_paragraph("POSITIONS OF RESPONSIBILITY")
        for exp in positions:
            document.add_paragraph(
                f"{exp['title']}, {exp['organization']} - {exp.get('description') or ''}",
                style="List Bullet",
            )

    # --- Certifications ---
    if student.get("certifications"):
        document.add_paragraph("CERTIFICATIONS")
        for cert in student["certifications"]:
            bits = [cert["name"], cert.get("issuer"), str(cert.get("year") or "")]
            document.add_paragraph(
                " - ".join(bit for bit in bits if bit), style="List Bullet"
            )

    # --- Achievements ---
    if student.get("achievements"):
        document.add_paragraph("ACHIEVEMENTS")
        for item in student["achievements"]:
            document.add_paragraph(item["title"], style="List Bullet")

    destination.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(destination))
    return destination


def _bullets(text: str, limit: int = 3) -> list[str]:
    """Split a paragraph into resume-style bullets."""
    parts = [part.strip() for part in text.split(". ") if part.strip()]
    return [part if part.endswith(".") else part + "." for part in parts[:limit]]
