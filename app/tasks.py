import asyncio
import uuid
from pathlib import Path

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models import Chunk, DocumentStatus
from app.repositories import replace_chunks, update_document_status
from app.services.chunking import chunk_pages
from app.services.llm import LLMClient
from app.services.pdf import extract_pdf_pages


async def process_document(document_id: uuid.UUID, file_path: str) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        pages = await asyncio.to_thread(extract_pdf_pages, Path(file_path))
        text_chunks = chunk_pages(
            pages,
            chunk_tokens=settings.chunk_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
            model_name=settings.embedding_model,
        )
        if not text_chunks:
            raise ValueError("No extractable text found in PDF")

        llm = LLMClient(settings)
        embeddings: list[list[float]] = []
        batch_size = 64
        for start in range(0, len(text_chunks), batch_size):
            batch = text_chunks[start : start + batch_size]
            embeddings.extend(
                await llm.embed_texts(
                    [chunk.text for chunk in batch],
                    input_type="passage",
                )
            )

        rows = [
            Chunk(
                document_id=document_id,
                chunk_index=text_chunk.chunk_index,
                page_number=text_chunk.page_number,
                text=text_chunk.text,
                embedding=embedding,
            )
            for text_chunk, embedding in zip(text_chunks, embeddings, strict=True)
        ]
        await replace_chunks(session, document_id, rows)
        await update_document_status(session, document_id, DocumentStatus.READY)
