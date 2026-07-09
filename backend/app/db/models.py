from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON
from sqlalchemy.sql import func
from app.db.database import Base


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(200), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    sources = Column(JSON, nullable=True)  # ["hackernews", "bing", "google_news", "weibo"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TrendingItem(Base):
    __tablename__ = "trending_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=True)
    summary = Column(Text, nullable=True)
    source = Column(String(50), nullable=False)  # hackernews, bing, google_news, weibo, github
    score = Column(Float, default=0.0)
    tags = Column(JSON, nullable=True)
    keyword = Column(String(200), nullable=True, index=True)
    raw_data = Column(JSON, nullable=True)
    is_relevant = Column(Boolean, default=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def primary_url(self):
        if self.url:
            return self.url
        if isinstance(self.raw_data, dict):
            value = self.raw_data.get("primary_url")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @property
    def raw_urls(self):
        urls = []

        if self.url:
            urls.append(self.url)

        if isinstance(self.raw_data, dict):
            raw_urls = self.raw_data.get("raw_urls")
            if isinstance(raw_urls, list):
                for value in raw_urls:
                    if isinstance(value, str) and value.strip():
                        urls.append(value.strip())

        deduped = []
        seen = set()
        for url in urls:
            if url in seen:
                continue
            seen.add(url)
            deduped.append(url)
        return deduped or None


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    notification_type = Column(String(50), nullable=False)  # email, web_push, in_app
    recipient = Column(String(200), nullable=False)
    subject = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, sent, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), default="default", unique=True)
    notification_email = Column(String(200), nullable=True)
    enable_email = Column(Boolean, default=True)
    enable_web_push = Column(Boolean, default=False)
    enable_in_app = Column(Boolean, default=True)
    daily_summary = Column(Boolean, default=True)
    summary_time = Column(String(10), default="09:00")
    settings = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
