import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document, DocumentStatus


async def create_document(
    session: AsyncSession,
    document_id: uuid.UUID,
    filename: str,
    file_path: str,
) -> Document:
    document = Document(id=document_id, filename=filename, file_path=file_path)
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


async def get_document(session: AsyncSession, document_id: uuid.UUID) -> Document | None:
    return await session.get(Document, document_id)


async def update_document_status(
    session: AsyncSession,
    document_id: uuid.UUID,
    status: DocumentStatus,
    error_message: str | None = None,
) -> None:
    document = await session.get(Document, document_id)
    if document is None:
        return
    document.status = status
    document.error_message = error_message
    await session.commit()


async def replace_chunks(session: AsyncSession, document_id: uuid.UUID, chunks: list[Chunk]) -> None:
    await session.execute(delete(Chunk).where(Chunk.document_id == document_id))
    session.add_all(chunks)
    await session.commit()


async def delete_document(session: AsyncSession, document_id: uuid.UUID) -> bool:
    document = await session.get(Document, document_id)
    if document is None:
        return False
    await session.delete(document)
    await session.commit()
    return True


async def search_chunks(
    session: AsyncSession,
    document_id: uuid.UUID,
    query_embedding: list[float],
    top_k: int,
) -> list[tuple[Chunk, float]]:
    distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")
    statement = (
        select(Chunk, distance)
        .where(Chunk.document_id == document_id)
        .order_by(distance)
        .limit(top_k)
    )
    rows = (await session.execute(statement)).all()
    return [(chunk, max(0.0, 1.0 - float(dist))) for chunk, dist in rows]
