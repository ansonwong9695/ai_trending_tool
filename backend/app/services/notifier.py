import aiosmtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Dict, Any

from app.config import settings
from app.db.database import async_session_maker
from app.db.models import Notification, TrendingItem, UserSettings
from sqlalchemy import select


async def _record_notification(
    notification_type: str,
    recipient: str,
    subject: str,
    content: str,
    status: str,
    error_message: str = None,
):
    async with async_session_maker() as db:
        notif = Notification(
            notification_type=notification_type,
            recipient=recipient,
            subject=subject,
            content=content,
            status=status,
            error_message=error_message,
            sent_at=datetime.utcnow() if status == "sent" else None,
        )
        db.add(notif)
        await db.commit()


async def send_email_notification(subject: str, html_content: str, recipient: str = None):
    """Send an HTML email notification via aiosmtplib."""
    to_addr = recipient or settings.notification_email

    message = MIMEMultipart("alternative")
    message["From"] = settings.smtp_user
    message["To"] = to_addr
    message["Subject"] = subject
    message.attach(MIMEText(html_content, "html"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_pass,
        )
        await _record_notification("email", to_addr, subject, html_content, "sent")
        print(f"Email sent to {to_addr}: {subject}")
    except Exception as e:
        error = str(e)
        await _record_notification("email", to_addr, subject, html_content, "failed", error)
        print(f"Email send failed: {error}")


def _build_items_html(items: List[Dict[str, Any]]) -> str:
    rows = ""
    for item in items:
        title = item.get("title", "")
        url = item.get("url", "#")
        source = item.get("source", "")
        summary = item.get("summary", "")
        rows += f"""
        <div style="border:1px solid #e0d6c5; border-radius:8px; padding:16px; margin-bottom:12px; background:#fff;">
            <h3 style="margin:0 0 6px; font-family:'Roboto Slab',serif; color:#2c2c2c;">
                <a href="{url}" style="color:#C8853F; text-decoration:none;">{title}</a>
            </h3>
            <p style="margin:0 0 6px; color:#666; font-size:13px;">来源: {source}</p>
            {f'<p style="margin:0; color:#555; font-size:14px;">{summary}</p>' if summary else ''}
        </div>
        """
    return rows


async def notify_keyword_matches(keyword: str, items: List[Dict[str, Any]]):
    """Send email notification for new keyword matches."""
    if not items:
        return

    rows = _build_items_html(items)
    html = f"""
    <html><body style="background:#F6F1E8; font-family:Inter,sans-serif; padding:24px;">
        <div style="max-width:600px; margin:0 auto;">
            <h2 style="font-family:'Roboto Slab',serif; color:#C8853F; border-bottom:2px solid #C8853F; padding-bottom:8px;">
                关键词监控: {keyword}
            </h2>
            <p style="color:#555;">发现 {len(items)} 条相关内容</p>
            {rows}
            <p style="color:#999; font-size:12px; margin-top:24px;">AI热点监控 · {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    </body></html>
    """
    await send_email_notification(f"[热点监控] 关键词「{keyword}」有 {len(items)} 条新内容", html)


async def send_daily_summary():
    """Send daily summary of trending items."""
    async with async_session_maker() as db:
        # Check user settings
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == "default")
        )
        user_settings = result.scalar_one_or_none()
        if user_settings and not user_settings.daily_summary:
            return
        if user_settings and not user_settings.enable_email:
            return

        # Get today's top trending items
        from sqlalchemy import func, desc
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(TrendingItem)
            .where(TrendingItem.is_relevant == True)
            .where(TrendingItem.created_at >= today_start)
            .order_by(desc(TrendingItem.score))
            .limit(10)
        )
        items = result.scalars().all()

    if not items:
        print("No items for daily summary.")
        return

    items_data = [
        {
            "title": item.title,
            "url": item.url,
            "source": item.source,
            "summary": item.summary,
        }
        for item in items
    ]

    rows = _build_items_html(items_data)
    html = f"""
    <html><body style="background:#F6F1E8; font-family:Inter,sans-serif; padding:24px;">
        <div style="max-width:600px; margin:0 auto;">
            <h2 style="font-family:'Roboto Slab',serif; color:#C8853F; border-bottom:2px solid #C8853F; padding-bottom:8px;">
                每日热点摘要
            </h2>
            <p style="color:#555;">今日精选 {len(items)} 条热点内容</p>
            {rows}
            <p style="color:#999; font-size:12px; margin-top:24px;">AI热点监控 · {datetime.now().strftime('%Y-%m-%d')}</p>
        </div>
    </body></html>
    """
    await send_email_notification(f"[每日摘要] {datetime.now().strftime('%Y-%m-%d')} 热点精选", html)
