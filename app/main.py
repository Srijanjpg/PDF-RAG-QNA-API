from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis

from app.api import router
from app.config import get_settings
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    await init_db()
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield
    finally:
        await app.state.redis.aclose()


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")
