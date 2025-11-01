"""Case management routes."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.users import current_active_user
from app.database import get_session
from app.models.user import User
from app.models.case import Case, CaseCreate, CaseRead, CaseUpdate

router = APIRouter()


@router.post("/", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Create a new case."""
    case = Case(**case_data.model_dump())
    session.add(case)
    await session.commit()
    await session.refresh(case)
    return case


@router.get("/", response_model=List[CaseRead])
async def list_cases(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """List all cases for the current user."""
    from sqlalchemy import select
    
    result = await session.execute(
        select(Case).where(Case.user_id == user.id)
    )
    cases = result.scalars().all()
    return cases


@router.get("/{case_id}", response_model=CaseRead)
async def get_case(
    case_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Get a specific case."""
    from sqlalchemy import select
    
    result = await session.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user.id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    return case


@router.patch("/{case_id}", response_model=CaseRead)
async def update_case(
    case_id: UUID,
    case_update: CaseUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Update a case."""
    from sqlalchemy import select
    
    result = await session.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user.id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    update_data = case_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(case, key, value)
    
    await session.commit()
    await session.refresh(case)
    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Delete a case."""
    from sqlalchemy import select
    
    result = await session.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user.id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    await session.delete(case)
    await session.commit()
