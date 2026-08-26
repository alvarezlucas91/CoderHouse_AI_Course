from __future__ import annotations

import fakeredis.aioredis

from app.models import Job, JobStatus, utc_now
from app.store import JobStore


async def test_job_roundtrip_and_failure_state():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    store = JobStore(redis)
    now = utc_now()
    job = Job(id="job-1", status=JobStatus.PENDING, query="consulta", created_at=now, updated_at=now)
    await store.create(job)
    loaded = await store.get("job-1")
    assert loaded and loaded.status == JobStatus.PENDING
    failed = await store.update("job-1", status=JobStatus.FAILED, error="boom")
    assert failed.status == JobStatus.FAILED
    assert (await store.get("job-1")).error == "boom"
    await redis.aclose()
