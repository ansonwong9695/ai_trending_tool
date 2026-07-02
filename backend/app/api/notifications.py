from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional, Annotated

from app.db.database import get_db
from app.db.models import Notification
from app.api.schemas import NotificationResponse, MonitorResponse

router = APIRouter()

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(
    db: DbDep,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    stmt = select(Notification)
    if status:
        stmt = stmt.where(Notification.status == status)
    stmt = stmt.order_by(desc(Notification.created_at)).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(notification_id: int, db: DbDep):
    notification = await db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.post("/test-email", response_model=MonitorResponse)
async def test_email(background_tasks: BackgroundTasks):
    """Send a test email notification."""
    from app.services.notifier import send_email_notification
    background_tasks.add_task(
        send_email_notification,
        "测试邮件 - AI热点监控",
        "<h2>邮件通知测试成功！</h2><p>您的 AI 热点监控邮件通知已配置完成。</p>",
    )
    return MonitorResponse(success=True, message="Test email queued", items_found=0)


@router.post("/daily-summary", response_model=MonitorResponse)
async def trigger_daily_summary(background_tasks: BackgroundTasks):
    """Manually trigger daily summary email."""
    from app.services.notifier import send_daily_summary
    background_tasks.add_task(send_daily_summary)
    return MonitorResponse(success=True, message="Daily summary queued", items_found=0)
