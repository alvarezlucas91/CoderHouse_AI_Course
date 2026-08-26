from __future__ import annotations

import os
from contextlib import asynccontextmanager
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from redis.asyncio import Redis

from app.graph import build_graph
from app.models import ApprovalRequest, Job, JobStatus, TaskCreate, utc_now
from app.observability import configure_observability
from app.store import JobStore
from app.worker import WorkerPool

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_observability()
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis = Redis.from_url(redis_url, decode_responses=True)
    await redis.ping()
    # RedisSaver necesita respuestas binarias y Redis con JSON + Search.
    async with AsyncRedisSaver.from_conn_string(redis_url) as checkpointer:
        await checkpointer.asetup()
        store = JobStore(redis, int(os.getenv("JOB_TTL_SECONDS", "604800")))
        pool = WorkerPool(build_graph(checkpointer), store, int(os.getenv("WORKER_CONCURRENCY", "2")))
        app.state.redis = redis
        app.state.store = store
        app.state.pool = pool
        await pool.start()
        yield
        await pool.stop()
    await redis.aclose()


app = FastAPI(
    title="API multi-agente con HITL",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["system"])
async def health(request: Request) -> dict[str, str]:
    await request.app.state.redis.ping()
    return {"status": "ok"}


@app.post("/tasks", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
async def create_task(payload: TaskCreate, request: Request) -> Job:
    now = utc_now()
    job = Job(
        id=str(uuid4()),
        status=JobStatus.PENDING,
        query=payload.query,
        critical=payload.critical,
        estimated_cost_usd=payload.estimated_cost_usd,
        created_at=now,
        updated_at=now,
    )
    await request.app.state.store.create(job)
    await request.app.state.pool.enqueue(job.id)
    return job


@app.get("/tasks/{job_id}", response_model=Job)
async def get_task(job_id: str, request: Request) -> Job:
    job = await request.app.state.store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return job


@app.post("/tasks/{job_id}/approve", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
async def approve_task(job_id: str, decision: ApprovalRequest, request: Request) -> Job:
    store: JobStore = request.app.state.store
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    if job.status != JobStatus.WAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail=f"El job no espera aprobación (estado actual: {job.status})",
        )
    approval = {"approved": decision.approved, "comment": decision.comment, "at": utc_now()}
    try:
        job = await store.update(
            job_id,
            expected_status=JobStatus.WAITING_APPROVAL,
            status=JobStatus.PENDING,
            approval=approval,
        )
    except ValueError as exc:
        # Dos aprobadores concurrentes: solo la primera transición puede ganar.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await request.app.state.pool.enqueue(job_id, approval)
    return job
