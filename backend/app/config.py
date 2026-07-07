from typing import Optional
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenRouter
    openrouter_api_key: str

    # Weibo
    weibo_cookie: Optional[str] = None
    weibo_cookie_sub: Optional[str] = None
    weibo_cookie_subp: Optional[str] = None
    weibo_cookie_scf: Optional[str] = None
    weibo_cookie_alf: Optional[str] = None
    weibo_cookie_ssologinstate: Optional[str] = None
    weibo_cookie_t_wm: Optional[str] = None
    weibo_cookie_mlogin: Optional[str] = None
    weibo_cookie_weibocn_from: Optional[str] = None
    weibo_cookie_m_weibocn_params: Optional[str] = None
    weibo_cookie_mweibo_short_token: Optional[str] = None
    weibo_cookie_xsrf_token: Optional[str] = None

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

    @computed_field
    @property
    def weibo_cookie_header(self) -> Optional[str]:
        if self.weibo_cookie:
            return self.weibo_cookie.strip()

        pairs = [
            ("SUB", self.weibo_cookie_sub),
            ("SUBP", self.weibo_cookie_subp),
            ("SCF", self.weibo_cookie_scf),
            ("ALF", self.weibo_cookie_alf),
            ("SSOLoginState", self.weibo_cookie_ssologinstate),
            ("_T_WM", self.weibo_cookie_t_wm),
            ("MLOGIN", self.weibo_cookie_mlogin),
            ("WEIBOCN_FROM", self.weibo_cookie_weibocn_from),
            ("M_WEIBOCN_PARAMS", self.weibo_cookie_m_weibocn_params),
            ("mweibo_short_token", self.weibo_cookie_mweibo_short_token),
            ("XSRF-TOKEN", self.weibo_cookie_xsrf_token),
        ]

        cookie_parts = [f"{key}={value.strip()}" for key, value in pairs if value and value.strip()]
        if not cookie_parts:
            return None
        return "; ".join(cookie_parts)

settings = Settings()
