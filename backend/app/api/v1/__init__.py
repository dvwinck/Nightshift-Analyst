"""API v1 package."""

from fastapi import APIRouter

from app.api.v1.routes import auth, cases, characters, game_state

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(characters.router, prefix="/characters", tags=["characters"])
api_router.include_router(game_state.router, prefix="/game-state", tags=["game-state"])
