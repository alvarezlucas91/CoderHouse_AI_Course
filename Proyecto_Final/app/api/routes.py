from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request, status

from app.persistence import InvalidJobTransition
from app.schemas import (
    ApprovalDecision,
    JobRecord,
    JobResponse,
    JobStatus,
    ServiceStatus,
    TaskRequest,
)


router = APIRouter(prefix="/v1")


def _public(job: JobRecord) -> JobResponse:
    return JobResponse.model_validate(job.model_dump(exclude={"request", "approval"}))


@router.post("/tasks", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_task(payload: TaskRequest, request: Request) -> JobResponse:
    now = datetime.now(UTC)
    job = JobRecord(
        id=uuid4(),
        thread_id=payload.thread_id or uuid4(),
        status=JobStatus.PENDING,
        request=payload,
        created_at=now,
        updated_at=now,
    )
    await request.app.state.job_store.create(job)
    await request.app.state.worker_pool.enqueue(job.id)
    return _public(job)


@router.get("/tasks/{job_id}", response_model=JobResponse)
async def get_task(job_id: UUID, request: Request) -> JobResponse:
    job = await request.app.state.job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _public(job)


@router.post("/tasks/{job_id}/approval", response_model=JobResponse, status_code=202)
async def approve_task(
    job_id: UUID, payload: ApprovalDecision, request: Request
) -> JobResponse:
    job = await request.app.state.job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if job.status != JobStatus.WAITING_APPROVAL:
        raise HTTPException(status_code=409, detail="Task is not waiting for approval")
    if not payload.approved:
        try:
            job = await request.app.state.job_store.update(
                job_id,
                status=JobStatus.REJECTED,
                approval=payload,
                approval_request=None,
            )
        except InvalidJobTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return _public(job)

    await request.app.state.worker_pool.enqueue(job_id, payload)
    return _public(job)


@router.get("/health", response_model=ServiceStatus)
async def health(request: Request) -> ServiceStatus:
    await request.app.state.redis.ping()
    return ServiceStatus(status="healthy")


@router.get("/ready", response_model=ServiceStatus)
async def ready(request: Request) -> ServiceStatus:
    if not getattr(request.app.state, "worker_pool", None):
        raise HTTPException(status_code=503, detail="Workers are not ready")
    return ServiceStatus(status="ready")
