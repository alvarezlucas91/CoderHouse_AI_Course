from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    DONE = "DONE"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class TaskCreate(BaseModel):
    query: str = Field(min_length=3, max_length=4000)
    critical: bool = False
    estimated_cost_usd: float = Field(default=0, ge=0)


class ApprovalRequest(BaseModel):
    approved: bool
    comment: str | None = Field(default=None, max_length=1000)


class Job(BaseModel):
    id: str
    status: JobStatus
    query: str
    critical: bool = False
    estimated_cost_usd: float = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    approval_request: dict[str, Any] | None = None
    approval: dict[str, Any] | None = None
    created_at: str
    updated_at: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
