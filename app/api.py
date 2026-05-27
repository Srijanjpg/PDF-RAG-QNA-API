import re
import uuid
from pathlib import Path

import aiofiles
from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session
from app.models import DocumentStatus
from app.queue import enqueue_document_index
from app.repositories import (
    create_document,
    delete_document,
    get_document,
    search_chunks,
    update_document_status,
)
from app.schemas import AskRequest, AskResponse, Citation, DocumentStatusResponse, DocumentUploadResponse
from app.services.cache import get_cached_answer, make_question_cache_key, set_cached_answer
from app.services.llm import LLMClient

router = APIRouter()


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_job_queue(request: Request) -> ArqRedis:
    return request.app.state.arq_redis


@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    job_queue: ArqRedis = Depends(get_job_queue),
) -> DocumentUploadResponse:
    if file.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    document_id = uuid.uuid4()
    safe_name = _safe_filename(file.filename or "upload.pdf")
    file_path = settings.upload_dir / f"{document_id}_{safe_name}"
    max_bytes = settings.max_upload_mb * 1024 * 1024
    bytes_written = 0

    async with aiofiles.open(file_path, "wb") as out_file:
        while chunk := await file.read(1024 * 1024):
            bytes_written += len(chunk)
            if bytes_written > max_bytes:
                await out_file.close()
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"PDF exceeds {settings.max_upload_mb} MB upload limit",
                )
            await out_file.write(chunk)

    document = await create_document(
        session,
        document_id=document_id,
        filename=safe_name,
        file_path=str(file_path),
    )

    try:
        await enqueue_document_index(job_queue, document.id, document.file_path)
    except Exception as exc:
        await update_document_status(
            session,
            document.id,
            DocumentStatus.FAILED,
            error_message=f"Could not enqueue indexing job: {exc}",
        )
        raise HTTPException(
            status_code=503,
            detail="Document was uploaded, but indexing could not be queued.",
        ) from exc

    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        status=document.status,
    )


@router.get("/documents/{document_id}/status", response_model=DocumentStatusResponse)
async def document_status(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> DocumentStatusResponse:
    document = await get_document(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentStatusResponse(
        document_id=document.id,
        filename=document.filename,
        status=document.status,
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.post("/documents/{document_id}/ask", response_model=AskResponse)
async def ask_document(
    document_id: uuid.UUID,
    payload: AskRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> AskResponse:
    document = await get_document(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != DocumentStatus.READY:
        raise HTTPException(
            status_code=409,
            detail="Document is still processing. Please wait until it is ready.",
        )

    cache_key = make_question_cache_key(document_id, payload.question, settings)
    cached = await get_cached_answer(redis, cache_key)
    if cached is not None:
        cached.cached = True
        return cached

    llm = LLMClient(settings)
    query_embedding = (await llm.embed_texts([payload.question], input_type="query"))[0]
    matches = await search_chunks(session, document_id, query_embedding, settings.retrieval_top_k)
    citations = [
        Citation(
            chunk_id=chunk.id,
            page_number=chunk.page_number,
            score=score,
            text=chunk.text,
        )
        for chunk, score in matches
        if score >= settings.retrieval_min_score
    ]

    if not citations:
        response = AskResponse(
            answer="I could not find this in the uploaded PDF.",
            citations=[],
        )
    else:
        answer = await llm.answer_question(payload.question, citations)
        response = AskResponse(answer=answer, citations=citations)

    await set_cached_answer(redis, cache_key, response, settings.cache_ttl_seconds)
    return response


@router.delete("/documents/{document_id}", status_code=204)
async def remove_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    document = await get_document(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = Path(document.file_path)
    deleted = await delete_document(session, document_id)
    if deleted:
        file_path.unlink(missing_ok=True)


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name if name.lower().endswith(".pdf") else f"{name}.pdf"
