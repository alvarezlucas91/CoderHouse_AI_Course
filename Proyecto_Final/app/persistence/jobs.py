from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.schemas import ApprovalDecision, JobRecord, JobStatus, TaskResult


class AsyncRedis(Protocol):
    async def set(self, name: str, value: str, *, ex: int | None = None) -> Any: ...
    async def get(self, name: str) -> str | bytes | None: ...
    def scan_iter(self, *, match: str) -> AsyncIterator[str | bytes]: ...


ALLOWED_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.FAILED},
    JobStatus.RUNNING: {
        JobStatus.WAITING_APPROVAL,
        JobStatus.DONE,
        JobStatus.FAILED,
        JobStatus.REJECTED,
        JobStatus.PENDING,
    },
    JobStatus.WAITING_APPROVAL: {JobStatus.RUNNING, JobStatus.REJECTED, JobStatus.FAILED},
    JobStatus.DONE: set(),
    JobStatus.FAILED: {JobStatus.PENDING},
    JobStatus.REJECTED: set(),
}


class InvalidJobTransition(ValueError):
    pass


class JobStore:
    def __init__(self, redis: AsyncRedis, *, ttl_seconds: int = 604800) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def key(job_id: UUID | str) -> str:
        return f"jobs:{job_id}"

    async def create(self, job: JobRecord) -> None:
        await self._redis.set(self.key(job.id), job.model_dump_json(), ex=self._ttl_seconds)

    async def get(self, job_id: UUID | str) -> JobRecord | None:
        raw = await self._redis.get(self.key(job_id))
        if raw is None:
            return None
        return JobRecord.model_validate_json(raw)

    async def update(
        self,
        job_id: UUID | str,
        *,
        status: JobStatus | None = None,
        result: TaskResult | None = None,
        error: str | None = None,
        approval_request: dict[str, str] | None = None,
        approval: ApprovalDecision | None = None,
        allow_same_status: bool = False,
    ) -> JobRecord:
        # Workers serialize updates for a job. API approval first verifies the
        # current state; Redis remains the durable source of truth.
        job = await self.get(job_id)
        if job is None:
            raise KeyError(str(job_id))
        if status is not None and status != job.status:
            if status not in ALLOWED_TRANSITIONS[job.status]:
                raise InvalidJobTransition(f"{job.status} -> {status} is not allowed")
        elif status is not None and not allow_same_status:
            raise InvalidJobTransition(f"Job is already {status}")

        updated = job.model_copy(
            update={
                "status": status or job.status,
                "result": result if result is not None else job.result,
                "error": error,
                "approval_request": approval_request,
                "approval": approval if approval is not None else job.approval,
                "updated_at": datetime.now(UTC),
            }
        )
        await self.create(updated)
        return updated

    async def recoverable(self) -> list[JobRecord]:
        jobs: list[JobRecord] = []
        async for key in self._redis.scan_iter(match="jobs:*"):
            normalized = key.decode() if isinstance(key, bytes) else key
            job = await self.get(normalized.removeprefix("jobs:"))
            if job and job.status in {JobStatus.PENDING, JobStatus.RUNNING}:
                jobs.append(job)
        return jobs
