from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # OpenRouter
    openrouter_api_key: str

    # Twitter
    twitter_api_key: Optional[str] = None

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str
    smtp_pass: str
    notification_email: str

    # Web Push
    vapid_public_key: Optional[str] = None
    vapid_private_key: Optional[str] = None
    vapid_subject: Optional[str] = None

    # Application
    app_url: str = "http://localhost:5173"
    backend_port: int = 8000
    frontend_port: int = 5173

    # Scheduler
    monitor_interval_minutes: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
