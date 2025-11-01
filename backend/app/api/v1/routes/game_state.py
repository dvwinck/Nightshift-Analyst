"""Game state management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.users import current_active_user
from app.database import get_session
from app.models.user import User
from app.models.game_state import GameState, GameStateCreate, GameStateRead, GameStateUpdate

router = APIRouter()


@router.post("/", response_model=GameStateRead, status_code=status.HTTP_201_CREATED)
async def create_game_state(
    game_state_data: GameStateCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Create a new game state for the current user."""
    game_state = GameState(**game_state_data.model_dump())
    session.add(game_state)
    await session.commit()
    await session.refresh(game_state)
    return game_state


@router.get("/me", response_model=GameStateRead)
async def get_my_game_state(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Get the game state for the current user."""
    from sqlalchemy import select
    
    result = await session.execute(
        select(GameState).where(GameState.user_id == user.id)
    )
    game_state = result.scalar_one_or_none()
    
    if not game_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game state not found"
        )
    
    return game_state


@router.patch("/me", response_model=GameStateRead)
async def update_my_game_state(
    game_state_update: GameStateUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Update the game state for the current user."""
    from sqlalchemy import select
    
    result = await session.execute(
        select(GameState).where(GameState.user_id == user.id)
    )
    game_state = result.scalar_one_or_none()
    
    if not game_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game state not found"
        )
    
    update_data = game_state_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(game_state, key, value)
    
    await session.commit()
    await session.refresh(game_state)
    return game_state


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_game_state(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Delete the game state for the current user."""
    from sqlalchemy import select
    
    result = await session.execute(
        select(GameState).where(GameState.user_id == user.id)
    )
    game_state = result.scalar_one_or_none()
    
    if not game_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game state not found"
        )
    
    await session.delete(game_state)
    await session.commit()
