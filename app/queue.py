import uuid
from urllib.parse import urlparse

from arq.connections import ArqRedis, RedisSettings


def redis_settings_from_url(redis_url: str) -> RedisSettings:
    parsed = urlparse(redis_url)
    if parsed.scheme not in {"redis", "rediss"}:
        raise ValueError("REDIS_URL must use redis:// or rediss://")

    database = 0
    if parsed.path and parsed.path != "/":
        database = int(parsed.path.lstrip("/"))

    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=database,
        username=parsed.username,
        password=parsed.password,
        ssl=parsed.scheme == "rediss",
    )


async def enqueue_document_index(
    redis: ArqRedis,
    document_id: uuid.UUID,
    file_path: str,
) -> str:
    job = await redis.enqueue_job("index_document", str(document_id), file_path)
    if job is None:
        raise RuntimeError("index_document job was not enqueued")
    return job.job_id
