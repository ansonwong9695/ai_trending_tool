from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.jobs.monitor import run_keyword_monitor, run_trending_collector
from app.services.notifier import send_daily_summary

_scheduler = AsyncIOScheduler()


def start_scheduler():
    interval = settings.monitor_interval_minutes
    _scheduler.add_job(
        run_keyword_monitor,
        "interval",
        minutes=interval,
        id="keyword_monitor",
        replace_existing=True,
    )
    _scheduler.add_job(
        run_trending_collector,
        "interval",
        minutes=interval,
        id="trending_collector",
        replace_existing=True,
    )
    _scheduler.add_job(
        send_daily_summary,
        "cron",
        hour=9,
        minute=0,
        id="daily_summary",
        replace_existing=True,
    )
    _scheduler.start()


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
