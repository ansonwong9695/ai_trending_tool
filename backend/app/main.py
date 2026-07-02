from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.db.database import init_db
from app.jobs.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="AI Trending Monitor",
    description="AI-powered trending topics and keyword monitoring tool",
    version="0.1.0",
    lifespan=lifespan
)

allowed_origins = list({
    settings.app_url.rstrip("/"),
    "http://localhost:5173",
    "http://127.0.0.1:5173",
})

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import keywords, trending, notifications, settings as settings_router

app.include_router(keywords.router, prefix="/api/v1/keywords", tags=["keywords"])
app.include_router(trending.router, prefix="/api/v1/trending", tags=["trending"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["settings"])


@app.get("/")
async def root():
    return {"message": "AI Trending Monitor API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
