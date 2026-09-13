from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import ProfileOut, ProfileUpdate
from app.security.dependencies import get_current_user

router = APIRouter()


@router.get("", response_model=ProfileOut)
async def read_profile(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ProfileOut:
    profile = await ProfileRepository(db).get_by_user_id(current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return ProfileOut.model_validate(profile)


@router.put("", response_model=ProfileOut)
async def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    repo = ProfileRepository(db)
    profile = await repo.get_by_user_id(current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    # exclude_unset: fields the client didn't send stay untouched; an explicit null clears that field.
    profile = await repo.update(profile, **payload.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(profile)
    return ProfileOut.model_validate(profile)
