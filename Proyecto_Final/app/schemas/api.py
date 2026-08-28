from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from .agents import DiagnosticReport, Recommendation
from .rag import Evidence


class JobStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    DONE = "DONE"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class TaskRequest(BaseModel):
    query: str = Field(min_length=3, max_length=4000)
    thread_id: UUID | None = None
    context: dict[str, str | int | float | bool] = Field(default_factory=dict)


class ApprovalDecision(BaseModel):
    approved: bool
    comment: str | None = Field(default=None, max_length=1000)


class ServiceStatus(BaseModel):
    status: str = Field(pattern="^(healthy|ready)$")


class TaskResult(BaseModel):
    answer: str = Field(min_length=1, max_length=10000)
    diagnosis: DiagnosticReport | None = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class JobResponse(BaseModel):
    id: UUID
    thread_id: UUID
    status: JobStatus
    result: TaskResult | None = None
    error: str | None = None
    approval_request: dict[str, str] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class JobRecord(JobResponse):
    request: TaskRequest
    approval: ApprovalDecision | None = None
