"""Student-scoped Career Connect endpoints."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.modules.auth.dependencies import CurrentUser, DbSession
from app.models import CareerConnectContact, CareerConnectJob, CareerConnectTrackerItem
from app.modules import career_connect_service as discovery
from app.modules.careerverse import career_fit_service, gemini_service

router = APIRouter(prefix="/career-connect", tags=["Career Connect"])

class JobIn(BaseModel):
    external_key: str
    title: str
    company: str | None = None
    location: str | None = None
    experience: str | None = None
    employment_type: str | None = None
    description: str | None = None
    sources: list[dict] = Field(default_factory=list)

class ContactIn(BaseModel):
    profile_url: str
    name: str | None = None
    designation: str | None = None
    company: str | None = None
    department: str | None = None
    location: str | None = None
    source: str = "manual"

class TrackerIn(BaseModel):
    kind: Literal["job", "contact"]
    job_id: int | None = None
    contact_id: int | None = None
    title: str
    organization: str | None = None
    status: Literal["saved", "approached", "referral_requested", "applied", "interview", "selected", "rejected"] = "saved"
    reminder_at: datetime | None = None
    notes: str | None = None

class TrackerUpdate(BaseModel):
    status: Literal["saved", "approached", "referral_requested", "applied", "interview", "selected", "rejected"] | None = None
    reminder_at: datetime | None = None
    notes: str | None = None

class CopilotIn(BaseModel):
    contact_id: int
    action: Literal["connection_request", "informational_interview", "referral_request", "follow_up", "questions"]

def _job(row):
    return {k: getattr(row, k) for k in ("id", "external_key", "title", "company", "location", "experience", "employment_type", "description", "sources", "created_at", "updated_at")}

@router.get("/jobs")
def jobs(user: CurrentUser, role: str = "", company: str = "", location: str = "", employment_type: str = ""):
    return discovery.search_jobs(role, company, location, employment_type)

@router.get("/jobs/saved")
def saved_jobs(user: CurrentUser, db: DbSession):
    return [_job(x) for x in db.scalars(select(CareerConnectJob).where(CareerConnectJob.user_id == user.id).order_by(CareerConnectJob.created_at.desc()))]

@router.post("/jobs/saved")
def save_job(body: JobIn, user: CurrentUser, db: DbSession):
    row = db.scalar(select(CareerConnectJob).where(CareerConnectJob.user_id == user.id, CareerConnectJob.external_key == body.external_key))
    if row is None:
        row = CareerConnectJob(user_id=user.id, **body.model_dump()); db.add(row)
    db.commit(); db.refresh(row); return _job(row)

@router.delete("/jobs/saved/{job_id}", status_code=204)
def delete_job(job_id: int, user: CurrentUser, db: DbSession):
    row = db.scalar(select(CareerConnectJob).where(CareerConnectJob.id == job_id, CareerConnectJob.user_id == user.id))
    if row: db.delete(row); db.commit()

@router.get("/people/search")
def people_search(user: CurrentUser, company: str = "", designation: str = "", department: str = "", location: str = ""):
    return discovery.search_people(company, designation, department, location)

@router.get("/people")
def people(user: CurrentUser, db: DbSession):
    return [{k: getattr(x, k) for k in ("id", "profile_url", "name", "designation", "company", "department", "location", "source")} for x in db.scalars(select(CareerConnectContact).where(CareerConnectContact.user_id == user.id).order_by(CareerConnectContact.created_at.desc()))]

def _save_contact(data: dict, user, db):
    url = discovery.safe_linkedin_profile(data.get("profile_url", ""))
    if not url: return False
    row = db.scalar(select(CareerConnectContact).where(CareerConnectContact.user_id == user.id, CareerConnectContact.profile_url == url))
    if row is None:
        row = CareerConnectContact(user_id=user.id, profile_url=url, name=data.get("name"), designation=data.get("designation"), company=data.get("company"), department=data.get("department"), location=data.get("location"), source=data.get("source", "manual")); db.add(row)
    return True

@router.post("/people")
def save_person(body: ContactIn, user: CurrentUser, db: DbSession):
    if not _save_contact(body.model_dump(), user, db): raise HTTPException(422, "Only direct LinkedIn /in/ profile URLs can be saved.")
    db.commit(); return {"message": "Contact saved"}

@router.post("/people/import")
async def import_people(file: UploadFile, user: CurrentUser, db: DbSession):
    if not file.filename or not file.filename.lower().endswith(".csv"): raise HTTPException(400, "Upload a CSV file.")
    raw = await file.read(2_000_001)
    if len(raw) > 2_000_000: raise HTTPException(413, "CSV must be under 2 MB.")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    saved = 0
    for row in reader:
        data = {"profile_url": row.get("URL", row.get("Profile URL", row.get("LinkedIn URL", ""))), "name": (row.get("First Name", "") + " " + row.get("Last Name", "")).strip() or None, "designation": row.get("Position", row.get("Title")), "company": row.get("Company"), "location": row.get("Location"), "source": "csv"}
        saved += int(_save_contact(data, user, db))
    db.commit(); return {"saved": saved}

@router.delete("/people/{contact_id}", status_code=204)
def delete_person(contact_id: int, user: CurrentUser, db: DbSession):
    row = db.scalar(select(CareerConnectContact).where(CareerConnectContact.id == contact_id, CareerConnectContact.user_id == user.id))
    if row: db.delete(row); db.commit()

@router.post("/copilot")
def copilot(body: CopilotIn, user: CurrentUser, db: DbSession):
    person = db.scalar(select(CareerConnectContact).where(CareerConnectContact.id == body.contact_id, CareerConnectContact.user_id == user.id))
    if not person: raise HTTPException(404, "Contact not found")
    try: profile = career_fit_service.student_features(db, user)
    except Exception: profile = {}
    prompt = f"Draft a concise, truthful {body.action.replace('_',' ')} for a student to personally review and send. Do not claim experience absent from profile. Return JSON with message string and questions array. Student profile: {str(profile)[:5000]}. Public contact details: name={person.name}, role={person.designation}, company={person.company}. Never send it."
    try: result = gemini_service.generate_json(prompt, temperature=0.5, max_tokens=700)
    except gemini_service.GeminiUnavailable as exc: raise HTTPException(503, str(exc)) from exc
    return {"draft": result, "review_required": True}

@router.get("/tracker")
def tracker(user: CurrentUser, db: DbSession):
    rows = db.scalars(select(CareerConnectTrackerItem).where(CareerConnectTrackerItem.user_id == user.id).order_by(CareerConnectTrackerItem.reminder_at.asc().nullslast(), CareerConnectTrackerItem.created_at.desc()))
    return [{k: getattr(x, k) for k in ("id", "kind", "job_id", "contact_id", "title", "organization", "status", "reminder_at", "notes", "created_at")} for x in rows]

@router.post("/tracker")
def add_tracker(body: TrackerIn, user: CurrentUser, db: DbSession):
    if body.job_id and not db.scalar(select(CareerConnectJob.id).where(CareerConnectJob.id == body.job_id, CareerConnectJob.user_id == user.id)): raise HTTPException(404, "Saved job not found")
    if body.contact_id and not db.scalar(select(CareerConnectContact.id).where(CareerConnectContact.id == body.contact_id, CareerConnectContact.user_id == user.id)): raise HTTPException(404, "Contact not found")
    row = CareerConnectTrackerItem(user_id=user.id, **body.model_dump()); db.add(row); db.commit(); db.refresh(row); return {"id": row.id}

@router.patch("/tracker/{item_id}")
def update_tracker(item_id: int, body: TrackerUpdate, user: CurrentUser, db: DbSession):
    row = db.scalar(select(CareerConnectTrackerItem).where(CareerConnectTrackerItem.id == item_id, CareerConnectTrackerItem.user_id == user.id))
    if not row: raise HTTPException(404, "Tracker item not found")
    for key, value in body.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    db.commit(); return {"message": "Updated"}

@router.delete("/tracker/{item_id}", status_code=204)
def delete_tracker(item_id: int, user: CurrentUser, db: DbSession):
    row = db.scalar(select(CareerConnectTrackerItem).where(CareerConnectTrackerItem.id == item_id, CareerConnectTrackerItem.user_id == user.id))
    if row: db.delete(row); db.commit()
