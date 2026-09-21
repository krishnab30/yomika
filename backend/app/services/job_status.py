from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from redis.asyncio import Redis


STATUS_TTL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class JobState:
    job_id: str
    status: str
    stage: str
    progress: int
    message: str
    updated_at: str


class JobStatusStore:
    def __init__(
        self,
        redis: Redis,
    ) -> None:
        self.redis = redis

    @staticmethod
    def _key(job_id: str) -> str:
        return f"audiobook:job:{job_id}"

    async def update(
        self,
        job_id: str,
        *,
        status: str,
        stage: str,
        progress: int,
        message: str = "",
    ) -> None:
        now = datetime.now(UTC).isoformat()

        key = self._key(job_id)

        await self.redis.hset(
            key,
            mapping={
                "job_id": job_id,
                "status": status,
                "stage": stage,
                "progress": str(progress),
                "message": message,
                "updated_at": now,
            },
        )

        await self.redis.expire(
            key,
            STATUS_TTL_SECONDS,
        )

    async def get(
        self,
        job_id: str,
    ) -> JobState | None:
        data = await self.redis.hgetall(
            self._key(job_id)
        )

        if not data:
            return None

        return JobState(
            job_id=data["job_id"],
            status=data["status"],
            stage=data["stage"],
            progress=int(data["progress"]),
            message=data["message"],
            updated_at=data["updated_at"],
        )