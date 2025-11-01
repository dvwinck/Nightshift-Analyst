"""Character management routes."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.users import current_active_user
from app.database import get_session
from app.models.user import User
from app.models.character import Character, CharacterCreate, CharacterRead, CharacterUpdate

router = APIRouter()


@router.post("/", response_model=CharacterRead, status_code=status.HTTP_201_CREATED)
async def create_character(
    character_data: CharacterCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Create a new character."""
    character = Character(**character_data.model_dump())
    session.add(character)
    await session.commit()
    await session.refresh(character)
    return character


@router.get("/case/{case_id}", response_model=List[CharacterRead])
async def list_case_characters(
    case_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """List all characters for a specific case."""
    from sqlalchemy import select
    
    result = await session.execute(
        select(Character).where(Character.case_id == case_id)
    )
    characters = result.scalars().all()
    return characters


@router.get("/{character_id}", response_model=CharacterRead)
async def get_character(
    character_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Get a specific character."""
    from sqlalchemy import select
    
    result = await session.execute(
        select(Character).where(Character.id == character_id)
    )
    character = result.scalar_one_or_none()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    return character


@router.patch("/{character_id}", response_model=CharacterRead)
async def update_character(
    character_id: UUID,
    character_update: CharacterUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Update a character."""
    from sqlalchemy import select
    
    result = await session.execute(
        select(Character).where(Character.id == character_id)
    )
    character = result.scalar_one_or_none()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    update_data = character_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(character, key, value)
    
    await session.commit()
    await session.refresh(character)
    return character


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
    character_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Delete a character."""
    from sqlalchemy import select
    
    result = await session.execute(
        select(Character).where(Character.id == character_id)
    )
    character = result.scalar_one_or_none()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    await session.delete(character)
    await session.commit()
