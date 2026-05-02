import hashlib
import json
import uuid

from redis.asyncio import Redis

from app.config import Settings
from app.schemas import AskResponse


def make_question_cache_key(document_id: uuid.UUID, question: str, settings: Settings) -> str:
    normalized = " ".join(question.lower().split())
    digest = hashlib.sha256(
        "|".join(
            [
                str(document_id),
                normalized,
                settings.llm_base_url,
                settings.embedding_model,
                settings.generation_model,
                str(settings.retrieval_top_k),
                str(settings.retrieval_min_score),
            ]
        ).encode()
    ).hexdigest()
    return f"qa:{digest}"


async def get_cached_answer(redis: Redis, key: str) -> AskResponse | None:
    payload = await redis.get(key)
    if payload is None:
        return None
    return AskResponse.model_validate_json(payload)


async def set_cached_answer(
    redis: Redis,
    key: str,
    response: AskResponse,
    ttl_seconds: int,
) -> None:
    await redis.setex(key, ttl_seconds, json.dumps(response.model_dump(mode="json")))
