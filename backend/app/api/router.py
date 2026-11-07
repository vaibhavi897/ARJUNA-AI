"""API router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, career_connect, careerverse, catalog, dashboard, interviews, learning, onboarding, profile, resume, settings
from app.api.routes import resume_builder, translate

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(onboarding.router)
api_router.include_router(profile.router)
api_router.include_router(resume.router)
api_router.include_router(settings.router)
api_router.include_router(dashboard.router)
api_router.include_router(interviews.router)
api_router.include_router(careerverse.router)
api_router.include_router(career_connect.router)
api_router.include_router(learning.router)
api_router.include_router(resume_builder.router)
api_router.include_router(translate.router)
