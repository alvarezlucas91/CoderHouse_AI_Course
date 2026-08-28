import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.persistence import InvalidJobTransition, JobStore
from app.schemas import JobRecord, JobStatus, TaskRequest


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def set(self, name: str, value: str, *, ex: int | None = None) -> None:
        self.data[name] = value

    async def get(self, name: str) -> str | None:
        return self.data.get(name)

    async def scan_iter(self, *, match: str) -> AsyncIterator[str]:
        for key in self.data:
            if key.startswith("jobs:"):
                yield key


def job(status: JobStatus = JobStatus.PENDING) -> JobRecord:
    now = datetime.now(UTC)
    return JobRecord(
        id=uuid4(),
        thread_id=uuid4(),
        status=status,
        request=TaskRequest(query="Diagnose Redshift queue contention"),
        created_at=now,
        updated_at=now,
    )


def test_store_persists_and_recovers_running_jobs() -> None:
    async def scenario() -> None:
        store = JobStore(FakeRedis())
        record = job()
        await store.create(record)
        await store.update(record.id, status=JobStatus.RUNNING)

        restored = await store.get(record.id)
        recoverable = await store.recoverable()

        assert restored is not None and restored.status == JobStatus.RUNNING
        assert [item.id for item in recoverable] == [record.id]

    asyncio.run(scenario())


def test_store_rejects_invalid_terminal_transition() -> None:
    async def scenario() -> None:
        store = JobStore(FakeRedis())
        record = job(JobStatus.DONE)
        await store.create(record)
        with pytest.raises(InvalidJobTransition):
            await store.update(record.id, status=JobStatus.RUNNING)

    asyncio.run(scenario())

