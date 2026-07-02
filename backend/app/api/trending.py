from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional, Annotated

from app.db.database import get_db
from app.db.models import TrendingItem, Keyword
from app.api.schemas import TrendingItemResponse, MonitorResponse
from app.jobs.monitor import run_keyword_monitor, run_trending_collector

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=List[TrendingItemResponse])
async def list_trending(
    db: DbDep,
    keyword: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    stmt = select(TrendingItem).where(TrendingItem.is_relevant == True)

    if keyword:
        stmt = stmt.where(TrendingItem.keyword == keyword)
    if source:
        stmt = stmt.where(TrendingItem.source == source)

    stmt = stmt.order_by(desc(TrendingItem.created_at)).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{item_id}", response_model=TrendingItemResponse)
async def get_trending_item(item_id: int, db: DbDep):
    item = await db.get(TrendingItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("/monitor/trigger", response_model=MonitorResponse)
async def trigger_monitor(background_tasks: BackgroundTasks, db: DbDep):
    """Manually trigger keyword monitoring for all active keywords"""
    result = await db.execute(select(Keyword).where(Keyword.is_active == True))
    keywords = result.scalars().all()

    if not keywords:
        return MonitorResponse(success=True, message="No active keywords to monitor", items_found=0)

    background_tasks.add_task(run_keyword_monitor)
    return MonitorResponse(
        success=True,
        message=f"Monitor triggered for {len(keywords)} keywords",
        items_found=0,
    )


@router.post("/collect/trigger", response_model=MonitorResponse)
async def trigger_collect(background_tasks: BackgroundTasks):
    """Manually trigger trending topics collection"""
    background_tasks.add_task(run_trending_collector)
    return MonitorResponse(success=True, message="Trending collection triggered", items_found=0)
