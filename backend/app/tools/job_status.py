from __future__ import annotations

import asyncio
import sys

from redis.asyncio import Redis

from backend.app.services.job_status import (
    JobStatusStore,
)


async def main(job_id: str) -> None:
    redis = Redis.from_url(
        "redis://127.0.0.1:6379",
        decode_responses=True,
    )

    try:
        store = JobStatusStore(redis)

        state = await store.get(
            job_id
        )

        if state is None:
            print("Job not found.")
            return

        print(f"Job ID: {state.job_id}")
        print(f"Status: {state.status}")
        print(f"Stage: {state.stage}")
        print(f"Progress: {state.progress}%")
        print(f"Message: {state.message}")
        print(f"Updated: {state.updated_at}")

    finally:
        await redis.aclose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: "
            "python -m backend.app.tools.job_status "
            "<job_id>"
        )

    asyncio.run(
        main(sys.argv[1])
    )