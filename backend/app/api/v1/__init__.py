"""API v1 package."""

from fastapi import APIRouter

from app.api.v1.routes import auth, shifts

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(shifts.router, prefix="/shifts", tags=["shifts"])
