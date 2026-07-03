"""Aggregates all v1 API routers. New domain routers are added here as
each phase implements them (auth, organizations, projects, repositories, ...).
"""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
