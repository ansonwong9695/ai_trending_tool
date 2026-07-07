from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Annotated

from app.db.database import get_db
from app.db.models import Keyword
from app.api.schemas import KeywordCreate, KeywordUpdate, KeywordResponse
from app.jobs.monitor import run_keyword_monitor

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=List[KeywordResponse])
async def list_keywords(db: DbDep):
    result = await db.execute(select(Keyword).order_by(Keyword.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=KeywordResponse, status_code=201)
async def create_keyword(data: KeywordCreate, background_tasks: BackgroundTasks, db: DbDep):
    existing = await db.execute(select(Keyword).where(Keyword.keyword == data.keyword))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Keyword already exists")

    keyword = Keyword(keyword=data.keyword, sources=data.sources)
    db.add(keyword)
    await db.commit()
    await db.refresh(keyword)

    if keyword.is_active:
        background_tasks.add_task(run_keyword_monitor)

    return keyword


@router.get("/{keyword_id}", response_model=KeywordResponse)
async def get_keyword(keyword_id: int, db: DbDep):
    keyword = await db.get(Keyword, keyword_id)
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return keyword


@router.patch("/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(keyword_id: int, data: KeywordUpdate, db: DbDep):
    keyword = await db.get(Keyword, keyword_id)
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    if data.is_active is not None:
        keyword.is_active = data.is_active
    if data.sources is not None:
        keyword.sources = data.sources

    await db.commit()
    await db.refresh(keyword)
    return keyword


@router.delete("/{keyword_id}", status_code=204)
async def delete_keyword(keyword_id: int, db: DbDep):
    keyword = await db.get(Keyword, keyword_id)
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    await db.delete(keyword)
    await db.commit()
