from __future__ import annotations

import asyncio
import logging
from typing import Any

from langgraph.types import Command

from app.models import JobStatus
from app.observability import flush_traces, traced_node
from app.store import JobStore

logger = logging.getLogger(__name__)


class WorkerPool:
    def __init__(self, graph: Any, store: JobStore, concurrency: int = 2):
        self.graph = graph
        self.store = store
        self.queue: asyncio.Queue[tuple[str, dict[str, Any] | None]] = asyncio.Queue()
        self.concurrency = concurrency
        self.tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        self.tasks = [asyncio.create_task(self._run(i), name=f"agent-worker-{i}") for i in range(self.concurrency)]
        for job_id in await self.store.recoverable_ids():
            await self.store.update(job_id, status=JobStatus.PENDING)
            await self.enqueue(job_id)

    async def stop(self) -> None:
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        flush_traces()

    async def enqueue(self, job_id: str, resume: dict[str, Any] | None = None) -> None:
        await self.queue.put((job_id, resume))

    async def _run(self, worker_number: int) -> None:
        while True:
            job_id, resume = await self.queue.get()
            try:
                await self.process(job_id, resume)
            except Exception:
                logger.exception("Fallo no controlado del worker %s", worker_number)
            finally:
                self.queue.task_done()

    @traced_node("worker.execute", kind="CHAIN")
    async def process(self, job_id: str, resume: dict[str, Any] | None = None) -> None:
        try:
            job = await self.store.get(job_id)
            if job is None:
                return
            await self.store.update(job_id, status=JobStatus.RUNNING, error=None)
            config = {"configurable": {"thread_id": job_id}}
            graph_input: Any = Command(resume=resume) if resume is not None else {
                "query": job.query,
                "critical": job.critical,
                "estimated_cost_usd": job.estimated_cost_usd,
                "research_data": [],
                "analysis_results": {},
                "validation_status": "PENDING",
                "task_completed": False,
            }
            result = await self.graph.ainvoke(graph_input, config=config)
            interrupts = result.get("__interrupt__", [])
            if interrupts:
                value = getattr(interrupts[0], "value", interrupts[0])
                await self.store.update(
                    job_id,
                    status=JobStatus.WAITING_APPROVAL,
                    approval_request=value,
                )
                return
            rejected = result.get("validation_status") == "REJECTED"
            await self.store.update(
                job_id,
                status=JobStatus.REJECTED if rejected else JobStatus.DONE,
                result=result.get("result", {}),
                approval_request=None,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("El job %s falló", job_id)
            try:
                await self.store.update(
                    job_id,
                    status=JobStatus.FAILED,
                    error=f"{type(exc).__name__}: {exc}",
                )
            except Exception:
                logger.exception("No se pudo persistir FAILED para %s", job_id)
