import uuid

from arq.worker import func

from app.config import get_settings
from app.database import AsyncSessionLocal, init_db
from app.models import DocumentStatus
from app.queue import redis_settings_from_url
from app.repositories import update_document_status
from app.tasks import process_document

MAX_INDEX_TRIES = 3


async def startup(ctx: dict) -> None:
    await init_db()


async def index_document(ctx: dict, document_id: str, file_path: str) -> None:
    parsed_document_id = uuid.UUID(document_id)
    try:
        await process_document(parsed_document_id, file_path)
    except Exception as exc:
        if ctx.get("job_try", 1) >= MAX_INDEX_TRIES:
            async with AsyncSessionLocal() as session:
                await update_document_status(
                    session,
                    parsed_document_id,
                    DocumentStatus.FAILED,
                    error_message=str(exc),
                )
        raise


class WorkerSettings:
    functions = [func(index_document, max_tries=MAX_INDEX_TRIES, timeout=1800)]
    redis_settings = redis_settings_from_url(get_settings().redis_url)
    on_startup = startup
