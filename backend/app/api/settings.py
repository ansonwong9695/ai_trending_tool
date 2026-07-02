from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated

from app.db.database import get_db
from app.db.models import UserSettings
from app.api.schemas import UserSettingsUpdate, UserSettingsResponse

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_or_create_settings(db: AsyncSession) -> UserSettings:
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == "default"))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserSettings(user_id="default")
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.get("/", response_model=UserSettingsResponse)
async def get_settings(db: DbDep):
    return await get_or_create_settings(db)


@router.patch("/", response_model=UserSettingsResponse)
async def update_settings(data: UserSettingsUpdate, db: DbDep):
    settings = await get_or_create_settings(db)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)
    return settings
