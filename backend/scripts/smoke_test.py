"""End-to-end check of the full student journey against a running backend.

    python -m scripts.smoke_test            # against http://127.0.0.1:8000
    python -m scripts.smoke_test --base-url http://127.0.0.1:8000

It registers a throwaway student, walks all seven onboarding steps, uploads a
generated DOCX resume, imports the parsed data, completes onboarding, reads the
dashboard, completes a roadmap task, edits the profile to prove rescoring, and
checks that one student cannot read another student's data.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import sys
import uuid

import httpx

PASS = "PASS"
FAIL = "FAIL"
failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    print(f"  [{status}] {label}" + (f" - {detail}" if detail else ""))
    if not condition:
        failures.append(label)


def build_resume_bytes(name: str) -> bytes:
    import docx

    document = docx.Document()
    document.add_paragraph(name)
    document.add_paragraph(f"smoke.{uuid.uuid4().hex[:6]}@smoke.arjuna.ai | +91 99999 88888")
    document.add_paragraph("EDUCATION")
    document.add_paragraph("Smoke Test Institute of Technology - B.Tech Computer Science")
    document.add_paragraph("Smoke University | 2022 - 2026 | CGPA: 8.20/10")
    document.add_paragraph("Relevant coursework: Data Structures, Algorithms, DBMS")
    document.add_paragraph("SKILLS")
    document.add_paragraph("Python, SQL, Docker, Pandas, Machine Learning, Excel")
    document.add_paragraph("PROJECTS")
    document.add_paragraph("Inventory Forecasting Service")
    document.add_paragraph("Technologies used: Python, Pandas, SQL")
    document.add_paragraph(
        "Built a demand forecasting service that reduced stockouts by 18% across 40 SKUs.",
        style="List Bullet",
    )
    document.add_paragraph("EXPERIENCE")
    document.add_paragraph("Data Analyst Intern | Northgate Analytics Pvt Ltd")
    document.add_paragraph("Jan 2025 - Jun 2025")
    document.add_paragraph(
        "Automated a weekly reporting pipeline and cut manual effort by 12 hours per week.",
        style="List Bullet",
    )
    document.add_paragraph("CERTIFICATIONS")
    document.add_paragraph("Google Data Analytics Professional Certificate - Google - 2025")
    document.add_paragraph("ACHIEVEMENTS")
    document.add_paragraph("Winner, Internal Analytics Hackathon 2025")

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def run(base_url: str) -> int:
    suffix = uuid.uuid4().hex[:8]
    email = f"smoke.{suffix}@smoke.arjuna.ai"
    username = f"smoke.{suffix}"
    password = "SmokeTest123"
    full_name = "Smoke Test Student"

    client = httpx.Client(base_url=base_url, timeout=60.0)

    print("\n1. Health")
    health = client.get("/health").json()
    check("API healthy", health.get("status") == "ok", f"db={health['database']['connected']}")
    check(
        "AI mode reported honestly",
        health.get("ai_analysis") in {"rule_based", "llm_assisted"},
        health.get("ai_analysis", "?"),
    )

    print("\n2. Validation rejects bad input")
    weak = client.post(
        "/api/auth/register",
        json={
            "full_name": full_name,
            "email": email,
            "username": username,
            "password": "short",
            "confirm_password": "short",
        },
    )
    check("Short password rejected", weak.status_code == 422, str(weak.status_code))
    mismatch = client.post(
        "/api/auth/register",
        json={
            "full_name": full_name,
            "email": email,
            "username": username,
            "password": password,
            "confirm_password": "Different123",
        },
    )
    check("Password mismatch rejected", mismatch.status_code == 422, str(mismatch.status_code))

    print("\n3. Registration")
    registered = client.post(
        "/api/auth/register",
        json={
            "full_name": full_name,
            "email": email,
            "username": username,
            "password": password,
            "confirm_password": password,
        },
    )
    check("Registered", registered.status_code == 201, str(registered.status_code))
    if registered.status_code != 201:
        print(registered.text[:500])
        return 1
    payload = registered.json()
    token = payload["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    check("Sent to onboarding", payload["next_route"].startswith("/onboarding"), payload["next_route"])

    duplicate = client.post(
        "/api/auth/register",
        json={
            "full_name": full_name,
            "email": email,
            "username": f"{username}x",
            "password": password,
            "confirm_password": password,
        },
    )
    check("Duplicate email blocked", duplicate.status_code == 409, str(duplicate.status_code))

    print("\n4. Protected routes require a token")
    anonymous = httpx.Client(base_url=base_url, timeout=30.0)
    check(
        "Dashboard rejects anonymous callers",
        anonymous.get("/api/dashboard").status_code == 401,
    )
    check("Profile rejects anonymous callers", anonymous.get("/api/profile").status_code == 401)
    check(
        "Bad token rejected",
        anonymous.get(
            "/api/profile", headers={"Authorization": "Bearer not-a-real-token"}
        ).status_code
        == 401,
    )

    print("\n5. Dashboard blocked before onboarding")
    early = client.get("/api/dashboard")
    check("Dashboard gated on onboarding", early.status_code == 409, str(early.status_code))

    print("\n6. Onboarding steps")
    step1 = client.post(
        "/api/onboarding/personal",
        json={
            "full_name": full_name,
            "email": email,
            "phone": "+91 90000 11111",
            "location": "Pune",
            "college": "Smoke Test Institute of Technology",
            "degree": "B.Tech",
            "branch": "Computer Science",
            "graduation_year": 2026,
            "current_academic_year": "Final Year",
            "cgpa": 8.2,
            "cgpa_scale": 10.0,
            "headline": "Analytics-leaning CS undergrad",
            "bio": "Final year student focused on data analytics and backend work.",
        },
    )
    check("Step 1 personal saved", step1.status_code == 200, str(step1.status_code))

    step2 = client.post(
        "/api/onboarding/academics",
        json={
            "entries": [
                {
                    "level": "undergraduate",
                    "institution": "Smoke Test Institute of Technology",
                    "board_or_university": "Smoke University",
                    "degree_or_program": "B.Tech Computer Science",
                    "score": 8.2,
                    "score_type": "cgpa",
                    "start_year": 2022,
                    "end_year": 2026,
                    "is_current": True,
                    "achievements": "Department rank 9",
                    "relevant_coursework": ["Data Structures", "DBMS", "Statistics"],
                }
            ]
        },
    )
    check("Step 2 academics saved", step2.status_code == 200, str(step2.status_code))

    step3 = client.post(
        "/api/onboarding/skills",
        json={
            "skills": [
                {"name": "Python", "proficiency": "advanced"},
                {"name": "SQL", "proficiency": "advanced"},
                {"name": "Pandas", "proficiency": "intermediate"},
                {"name": "Excel", "proficiency": "intermediate"},
                {"name": "Data Visualization", "proficiency": "intermediate"},
                {"name": "Statistics", "proficiency": "intermediate"},
                {"name": "Kotlin Multiplatform Wizardry", "proficiency": "advanced"},
            ]
        },
    )
    check("Step 3 skills saved", step3.status_code == 200, str(step3.status_code))
    check(
        "Custom skill accepted",
        any(
            skill["name"] == "Kotlin Multiplatform Wizardry"
            for skill in client.get("/api/profile").json()["skills"]
        ),
    )

    step4 = client.post(
        "/api/onboarding/projects",
        json={
            "projects": [
                {
                    "title": "Inventory Forecasting Service",
                    "description": "Demand forecasting service that reduced stockouts by 18% across 40 SKUs using a seasonal model and a nightly batch job.",
                    "contribution": "Sole developer; built the model and the batch pipeline.",
                    "category": "Data Analytics",
                    "duration_months": 3,
                    "technologies": ["Python", "Pandas", "SQL"],
                    "github_url": "https://github.com/example/forecasting",
                },
                {
                    "title": "Campus Energy Dashboard",
                    "description": "Dashboard over three years of meter readings highlighting block-level consumption peaks.",
                    "contribution": "Owned data cleaning and the dashboard.",
                    "category": "Business Intelligence",
                    "duration_months": 2,
                    "technologies": ["Excel", "Data Visualization", "SQL"],
                },
            ]
        },
    )
    check("Step 4 projects saved", step4.status_code == 200, str(step4.status_code))

    step5 = client.post(
        "/api/onboarding/experience",
        json={
            "experiences": [
                {
                    "experience_type": "internship",
                    "organization": "Northgate Analytics",
                    "title": "Data Analyst Intern",
                    "description": "Automated weekly reporting and saved 12 hours of manual work per week.",
                    "duration_months": 5,
                    "skills_used": ["SQL", "Python", "Excel"],
                }
            ],
            "certifications": [
                {
                    "name": "Google Data Analytics Professional Certificate",
                    "issuer": "Google",
                    "related_skills": ["SQL", "Data Visualization"],
                }
            ],
            "achievements": [
                {
                    "title": "Winner, Internal Analytics Hackathon",
                    "category": "competition",
                    "scope": "college",
                }
            ],
        },
    )
    check("Step 5 experience saved", step5.status_code == 200, str(step5.status_code))

    print("\n7. Resume upload, parse and selective import")
    bad_type = client.post(
        "/api/resume/upload",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )
    check("Non-PDF/DOCX rejected", bad_type.status_code == 415, str(bad_type.status_code))

    fake_pdf = client.post(
        "/api/resume/upload",
        files={"file": ("fake.pdf", b"this is not really a pdf", "application/pdf")},
    )
    check("Renamed file rejected by magic check", fake_pdf.status_code == 400, str(fake_pdf.status_code))

    upload = client.post(
        "/api/resume/upload",
        files={
            "file": (
                "smoke_resume.docx",
                build_resume_bytes(full_name),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    check("Resume uploaded", upload.status_code == 200, str(upload.status_code))
    review = upload.json()["review"]
    check("Resume parsed", review["parse_status"] == "parsed", review["parse_status"])
    quality = review.get("quality") or {}
    check("Quality score produced", isinstance(quality.get("score"), (int, float)), str(quality.get("score")))
    suggestions = review.get("suggestions") or {}
    check("Skills extracted", len(suggestions.get("skills", [])) > 0, str(len(suggestions.get("skills", []))))
    check(
        "Existing skills flagged as already present",
        any(item["already_in_profile"] for item in suggestions.get("skills", [])),
    )
    check("Experience extracted", len(suggestions.get("experience", [])) > 0)

    before_skills = len(client.get("/api/profile").json()["skills"])
    new_skills = [
        item["name"] for item in suggestions.get("skills", []) if not item["already_in_profile"]
    ][:3]
    imported = client.post(
        "/api/resume/import",
        json={
            "import_contact": True,
            "skills": new_skills,
            "projects": [],
            "experience": [],
            "certifications": [],
            "achievements": [],
        },
    )
    check("Selective import succeeded", imported.status_code == 200, str(imported.status_code))
    after_profile = client.get("/api/profile").json()
    check(
        "Only selected skills imported",
        len(after_profile["skills"]) == before_skills + len(new_skills),
        f"{before_skills} -> {len(after_profile['skills'])} (+{len(new_skills)} selected)",
    )
    check(
        "Manually entered proficiency preserved",
        next(s["proficiency"] for s in after_profile["skills"] if s["name"] == "Python") == "advanced",
    )

    print("\n8. Career preferences")
    roles = client.get("/api/catalog/roles").json()
    check("Role catalogue available", len(roles) >= 10, f"{len(roles)} roles")
    by_slug = {role["slug"]: role["id"] for role in roles}
    chosen = [
        by_slug["data-analyst"],
        by_slug["business-analyst"],
        by_slug["software-development-engineer"],
    ]
    step7 = client.post(
        "/api/onboarding/preferences",
        json={
            "github_url": "github.com/example",
            "linkedin_url": "linkedin.com/in/example",
            "portfolio_url": None,
            "other_links": [],
            "role_ids": chosen,
            "primary_role_id": chosen[0],
        },
    )
    check("Step 7 preferences saved", step7.status_code == 200, str(step7.status_code))

    bad_role = client.put(
        "/api/profile/preferences",
        json={"role_ids": [999999], "primary_role_id": 999999, "other_links": []},
    )
    check("Unknown role id rejected", bad_role.status_code == 400, str(bad_role.status_code))

    print("\n9. Complete onboarding and score")
    complete = client.post("/api/onboarding/complete")
    check("Onboarding completed", complete.status_code == 200, str(complete.status_code))
    scored = complete.json()["data"]["scored"]
    check("All active roles scored", len(scored) == len(roles), f"{len(scored)} assessments")
    check("Scores within 0-100", all(0 <= item["score"] <= 100 for item in scored))
    check("Scores differ by role", len({item["score"] for item in scored}) > 3)

    print("\n10. Determinism (no random scoring)")
    first = {item["role"]: item["score"] for item in scored}
    again = client.post("/api/dashboard/recalculate").json()["data"]["scored"]
    second = {item["role"]: item["score"] for item in again}
    check("Identical profile gives identical scores", first == second)

    print("\n11. Dashboard")
    dashboard = client.get("/api/dashboard")
    check("Dashboard loads", dashboard.status_code == 200, str(dashboard.status_code))
    data = dashboard.json()
    check("Greeting is personalised", full_name.split()[0] in data["welcome"]["greeting"])
    check("Name is not hardcoded", data["welcome"]["full_name"] == full_name)
    check("Readiness present", data["readiness"]["has_assessments"] is True)
    check(
        "Target roles reflected",
        {role["role_id"] for role in data["readiness"]["preferred_roles"]} == set(chosen),
    )
    check("Strengths generated", len(data["strengths"]) > 0, f"{len(data['strengths'])}")
    check("Improvements generated", len(data["improvements"]) > 0, f"{len(data['improvements'])}")
    check("Skill analysis present", data["skills"]["total_skills"] > 0)
    check(
        "Evidence separated from claims",
        data["skills"]["evidence_backed"] > 0 and data["skills"]["claimed_only"] > 0,
        f"{data['skills']['evidence_backed']} proven / {data['skills']['claimed_only']} claimed",
    )
    check("Roadmap generated", data["roadmap"]["total_tasks"] > 0, f"{data['roadmap']['total_tasks']} tasks")
    check("Resume insights present", data["resume_insights"]["has_resume"] is True)
    check("Portfolio counts correct", data["portfolio"]["projects"] == 2, str(data["portfolio"]["projects"]))
    check("Career fit present", len(data["career_fit"]) > 0)
    check("AI insights present", len(data["ai_insights"]) > 0)
    check("Activity feed present", len(data["recent_activity"]) > 0)
    check("Last assessment timestamp set", bool(data["welcome"]["last_assessment_at"]))
    check(
        "AI mode declared",
        data["ai_mode"] in {"rule_based", "llm_assisted"},
        data["ai_mode"],
    )

    print("\n12. Explainability")
    primary_slug = next(
        role["role_slug"] for role in data["readiness"]["preferred_roles"] if role["is_primary"]
    )
    detail = client.get(f"/api/dashboard/roles/{primary_slug}")
    check("Role breakdown loads", detail.status_code == 200, str(detail.status_code))
    breakdown = detail.json()
    check("Seven components explained", len(breakdown["breakdowns"]) == 7, str(len(breakdown["breakdowns"])))
    check(
        "Every component has an explanation",
        all(len(item["explanation"]) > 20 for item in breakdown["breakdowns"]),
    )
    total_points = sum(item["points_earned"] for item in breakdown["breakdowns"])
    possible = sum(item["points_possible"] for item in breakdown["breakdowns"])
    recomputed = round(100 * total_points / possible, 1)
    check(
        "Component points reconcile with the role score",
        abs(recomputed - breakdown["score"]) <= 0.2,
        f"{recomputed} vs {breakdown['score']}",
    )
    check("Skill comparison present", len(breakdown["skill_comparison"]) > 0)
    check("Rubric weights exposed", len(breakdown["weights"]) == 7)

    print("\n13. Roadmap task completion")
    task_id = data["roadmap"]["tasks"][0]["id"]
    done = client.patch(f"/api/roadmap/tasks/{task_id}", json={"status": "completed"})
    check("Task marked complete", done.status_code == 200, str(done.status_code))
    roadmap = client.get("/api/roadmap").json()
    check("Completion persisted", roadmap["completed_tasks"] == 1, str(roadmap["completed_tasks"]))

    print("\n14. Data sync: an edit changes the scores")
    analytics_before = next(
        role["score"] for role in data["readiness"]["roles"] if role["role_slug"] == "data-analyst"
    )
    added = client.put(
        "/api/profile/projects",
        json={
            "projects": [
                {
                    "id": project["id"],
                    "title": project["title"],
                    "description": project["description"],
                    "contribution": project["contribution"],
                    "category": project["category"],
                    "duration_months": project["duration_months"],
                    "technologies": project["technologies"],
                }
                for project in client.get("/api/profile").json()["projects"]
            ]
            + [
                {
                    "title": "Retail Cohort Retention Study",
                    "description": "SQL and Python study of retention across acquisition cohorts, surfacing a 19-point gap between onboarding variants.",
                    "contribution": "Individual project; wrote all queries and the final memo.",
                    "category": "Data Analytics",
                    "duration_months": 2,
                    "technologies": ["SQL", "Python", "Statistics", "Data Visualization"],
                }
            ]
        },
    )
    check("Project added via settings endpoint", added.status_code == 200, str(added.status_code))
    check("Scores recalculated on edit", len(added.json()["recalculated_roles"]) > 0)

    refreshed = client.get("/api/dashboard").json()
    analytics_after = next(
        role["score"] for role in refreshed["readiness"]["roles"] if role["role_slug"] == "data-analyst"
    )
    check(
        "Dashboard reflects the new project",
        refreshed["portfolio"]["projects"] == 3,
        str(refreshed["portfolio"]["projects"]),
    )
    check(
        "Data Analyst score moved after adding a relevant project",
        analytics_after != analytics_before,
        f"{analytics_before} -> {analytics_after}",
    )
    check(
        "History retains the previous snapshot",
        refreshed["progress"]["assessment_count"] > len(roles),
        f"{refreshed['progress']['assessment_count']} snapshots",
    )

    print("\n15. Authorisation: one student cannot read another's data")
    other = httpx.Client(base_url=base_url, timeout=30.0)
    other_suffix = uuid.uuid4().hex[:8]
    other_reg = other.post(
        "/api/auth/register",
        json={
            "full_name": "Second Student",
            "email": f"second.{other_suffix}@smoke.arjuna.ai",
            "username": f"second.{other_suffix}",
            "password": password,
            "confirm_password": password,
        },
    )
    check("Second account created", other_reg.status_code == 201, str(other_reg.status_code))
    other.headers["Authorization"] = f"Bearer {other_reg.json()['access_token']}"
    other_profile = other.get("/api/profile").json()
    check("Second student gets their own empty profile", len(other_profile["skills"]) == 0)
    check("Second student has no projects", len(other_profile["projects"]) == 0)
    check(
        "Second student cannot see the first student's assessment",
        other.get(f"/api/dashboard/roles/{primary_slug}").status_code in (404, 409),
    )
    check(
        "Second student cannot complete the first student's roadmap task",
        other.patch(f"/api/roadmap/tasks/{task_id}", json={"status": "completed"}).status_code == 404,
    )

    print("\n16. Login and resume behaviour")
    login = httpx.Client(base_url=base_url, timeout=30.0).post(
        "/api/auth/login", json={"identifier": email, "password": password}
    )
    check("Login with email works", login.status_code == 200, str(login.status_code))
    check(
        "Completed student goes to the dashboard",
        login.json()["next_route"] == "/app/dashboard",
        login.json()["next_route"],
    )
    login_username = httpx.Client(base_url=base_url, timeout=30.0).post(
        "/api/auth/login", json={"identifier": username, "password": password}
    )
    check("Login with username works", login_username.status_code == 200)
    bad_login = httpx.Client(base_url=base_url, timeout=30.0).post(
        "/api/auth/login", json={"identifier": email, "password": "WrongPassword1"}
    )
    check("Wrong password rejected", bad_login.status_code == 401, str(bad_login.status_code))

    other_incomplete = httpx.Client(base_url=base_url, timeout=30.0).post(
        "/api/auth/login",
        json={"identifier": f"second.{other_suffix}@smoke.arjuna.ai", "password": password},
    )
    check(
        "Incomplete student resumes onboarding",
        other_incomplete.json()["next_route"].startswith("/onboarding"),
        other_incomplete.json()["next_route"],
    )

    print("\n17. Seeded demo account")
    demo = httpx.Client(base_url=base_url, timeout=30.0)
    demo_login = demo.post(
        "/api/auth/login",
        json={"identifier": "aarav.menon@demo.arjuna.ai", "password": "ArjunaDemo@2026"},
    )
    if demo_login.status_code == 200:
        demo.headers["Authorization"] = f"Bearer {demo_login.json()['access_token']}"
        demo_dash = demo.get("/api/dashboard").json()
        check("Demo student signs in", True)
        check(
            "Demo dashboard is personalised to the demo student",
            demo_dash["welcome"]["full_name"] == "Aarav Menon",
            demo_dash["welcome"]["full_name"],
        )
        check(
            "Demo student has their own scores",
            demo_dash["readiness"]["overall_score"] != data["readiness"]["overall_score"],
        )
    else:
        check("Demo student signs in", False, "run the seeder first")

    print("\n18. Password change")
    changed = client.post(
        "/api/auth/change-password",
        json={
            "current_password": password,
            "new_password": "NewSmoke456",
            "confirm_new_password": "NewSmoke456",
        },
    )
    check("Password changed", changed.status_code == 200, str(changed.status_code))
    recheck = httpx.Client(base_url=base_url, timeout=30.0).post(
        "/api/auth/login", json={"identifier": email, "password": "NewSmoke456"}
    )
    check("New password works", recheck.status_code == 200)
    old = httpx.Client(base_url=base_url, timeout=30.0).post(
        "/api/auth/login", json={"identifier": email, "password": password}
    )
    check("Old password no longer works", old.status_code == 401)

    client.close()
    print("\n" + "=" * 70)
    if failures:
        print(f"{len(failures)} CHECK(S) FAILED:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("ALL CHECKS PASSED")
    print(f"Test student: {email} / NewSmoke456")
    print("=" * 70)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the Arjuna AI API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    print(f"Arjuna AI smoke test - {args.base_url} - {dt.datetime.now():%Y-%m-%d %H:%M}")
    try:
        return run(args.base_url)
    except httpx.ConnectError:
        print("\nCould not connect. Start the backend first:")
        print("  uvicorn app.main:app --reload --port 8000")
        return 2


if __name__ == "__main__":
    sys.exit(main())
