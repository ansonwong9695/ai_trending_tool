from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class KeywordCreate(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    sources: Optional[List[str]] = None


class KeywordUpdate(BaseModel):
    is_active: Optional[bool] = None
    sources: Optional[List[str]] = None


class KeywordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    keyword: str
    is_active: bool
    sources: Optional[List[str]]
    created_at: datetime
    updated_at: Optional[datetime]


class TrendingItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: Optional[str]
    summary: Optional[str]
    source: str
    score: float
    tags: Optional[List[str]]
    keyword: Optional[str]
    is_relevant: bool
    confidence: Optional[float]
    created_at: datetime


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    notification_type: str
    recipient: str
    subject: Optional[str]
    content: str
    status: str
    error_message: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]


class UserSettingsUpdate(BaseModel):
    notification_email: Optional[str] = None
    enable_email: Optional[bool] = None
    enable_web_push: Optional[bool] = None
    enable_in_app: Optional[bool] = None
    daily_summary: Optional[bool] = None
    summary_time: Optional[str] = None


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    notification_email: Optional[str]
    enable_email: bool
    enable_web_push: bool
    enable_in_app: bool
    daily_summary: bool
    summary_time: str
    created_at: datetime
    updated_at: Optional[datetime]


class MonitorResponse(BaseModel):
    success: bool
    message: str
    items_found: int
