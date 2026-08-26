from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from app.models import Job, JobStatus, utc_now


class JobStore:
    """Estado operativo de jobs. Los checkpoints del grafo usan otro namespace."""

    def __init__(self, redis: Redis, ttl_seconds: int = 604800):
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def key(job_id: str) -> str:
        return f"jobs:{job_id}"

    async def create(self, job: Job) -> None:
        await self.redis.set(self.key(job.id), job.model_dump_json(), ex=self.ttl_seconds)

    async def get(self, job_id: str) -> Job | None:
        raw = await self.redis.get(self.key(job_id))
        return Job.model_validate_json(raw) if raw else None

    async def update(
        self, job_id: str, *, expected_status: JobStatus | None = None, **changes: Any
    ) -> Job:
        # Un worker procesa cada job; WATCH evita perder una aprobación concurrente.
        key = self.key(job_id)
        async with self.redis.pipeline(transaction=True) as pipe:
            while True:
                try:
                    await pipe.watch(key)
                    raw = await pipe.get(key)
                    if not raw:
                        raise KeyError(job_id)
                    payload = json.loads(raw)
                    if expected_status is not None and payload.get("status") != expected_status:
                        raise ValueError(
                            f"estado esperado {expected_status}; actual {payload.get('status')}"
                        )
                    payload.update(changes)
                    payload["updated_at"] = utc_now()
                    job = Job.model_validate(payload)
                    pipe.multi()
                    pipe.set(key, job.model_dump_json(), ex=self.ttl_seconds)
                    await pipe.execute()
                    return job
                except Exception as exc:
                    from redis.exceptions import WatchError

                    if isinstance(exc, WatchError):
                        continue
                    raise

    async def recoverable_ids(self) -> list[str]:
        ids: list[str] = []
        async for key in self.redis.scan_iter(match="jobs:*"):
            raw = await self.redis.get(key)
            if not raw:
                continue
            job = Job.model_validate_json(raw)
            if job.status in {JobStatus.PENDING, JobStatus.RUNNING}:
                ids.append(job.id)
        return ids
