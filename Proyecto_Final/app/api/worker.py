import asyncio
import logging
from typing import Any
from uuid import UUID

from langgraph.types import Command

from app.persistence import JobStore
from app.observability import traced
from app.schemas import (
    ApprovalDecision,
    DiagnosticReport,
    Evidence,
    JobStatus,
    RecommendationPlan,
    TaskResult,
)


logger = logging.getLogger(__name__)


class WorkerPool:
    def __init__(self, graph: Any, store: JobStore, *, concurrency: int = 2) -> None:
        self._graph = graph
        self._store = store
        self._concurrency = concurrency
        self._queue: asyncio.Queue[tuple[UUID, ApprovalDecision | None]] = asyncio.Queue()
        self._tasks: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        self._tasks = [
            asyncio.create_task(self._run(number), name=f"intelligence-worker-{number}")
            for number in range(self._concurrency)
        ]
        for job in await self._store.recoverable():
            if job.status == JobStatus.RUNNING:
                await self._store.update(job.id, status=JobStatus.PENDING)
            await self.enqueue(job.id)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def enqueue(self, job_id: UUID, approval: ApprovalDecision | None = None) -> None:
        await self._queue.put((job_id, approval))

    async def _run(self, number: int) -> None:
        while True:
            job_id, approval = await self._queue.get()
            try:
                await self.process(job_id, approval)
            except Exception:
                logger.exception("Unhandled worker %s failure for job %s", number, job_id)
            finally:
                self._queue.task_done()

    @traced("worker.execute", kind="CHAIN")
    async def process(self, job_id: UUID, approval: ApprovalDecision | None = None) -> None:
        try:
            job = await self._store.get(job_id)
            if job is None:
                return
            await self._store.update(job_id, status=JobStatus.RUNNING)
            config = {"configurable": {"thread_id": str(job.thread_id)}}
            graph_input: Any
            if approval is not None:
                graph_input = Command(resume=approval.model_dump(mode="json"))
            else:
                graph_input = {
                    "query": job.request.query,
                    "context": job.request.context,
                    "evidence": [],
                    "diagnosis": None,
                    "recommendation_plan": None,
                    "validation": None,
                    "iteration": 0,
                    "max_iterations": 8,
                    "audit_log": [],
                    "rejected": False,
                }
            state = await self._graph.ainvoke(graph_input, config=config)
            interrupts = state.get("__interrupt__", [])
            if interrupts:
                value = getattr(interrupts[0], "value", interrupts[0])
                await self._store.update(
                    job_id,
                    status=JobStatus.WAITING_APPROVAL,
                    approval_request={
                        "type": str(value.get("type", "approval")),
                        "reason": str(value.get("reason", "Human review required")),
                    },
                )
                return

            rejected = bool(state.get("rejected"))
            result = _task_result(state)
            await self._store.update(
                job_id,
                status=JobStatus.REJECTED if rejected else JobStatus.DONE,
                result=result,
                approval=approval,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Job %s failed", job_id)
            try:
                await self._store.update(
                    job_id,
                    status=JobStatus.FAILED,
                    error=f"{type(exc).__name__}: {exc}",
                )
            except Exception:
                logger.exception("Could not persist FAILED for job %s", job_id)


def _task_result(state: dict[str, Any]) -> TaskResult:
    diagnosis = (
        DiagnosticReport.model_validate(state["diagnosis"]) if state.get("diagnosis") else None
    )
    plan = (
        RecommendationPlan.model_validate(state["recommendation_plan"])
        if state.get("recommendation_plan")
        else None
    )
    return TaskResult(
        answer=state.get("final_answer") or "No se produjo una respuesta final.",
        diagnosis=diagnosis,
        recommendations=plan.recommendations if plan else [],
        evidence=[Evidence.model_validate(item) for item in state.get("evidence", [])],
        limitations=(
            state.get("supervisor_decision", {}).get("missing_information", [])
            if isinstance(state.get("supervisor_decision"), dict)
            else []
        ),
    )
