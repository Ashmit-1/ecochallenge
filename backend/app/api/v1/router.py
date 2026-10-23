"""Mounts every v1 router. This is the single place the API surface is assembled."""

from fastapi import APIRouter

from app.api.v1.routes import auth, challenges, leaderboard, profile, submissions, system

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(challenges.router)
api_router.include_router(submissions.router)
api_router.include_router(profile.router)
api_router.include_router(leaderboard.router)
