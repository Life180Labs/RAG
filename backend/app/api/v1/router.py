"""Aggregates all v1 API routers. New domain routers are added here as
each phase implements them (auth, organizations, projects, repositories, ...).
"""

from fastapi import APIRouter

from app.api.v1 import auth, health, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(users.router)
