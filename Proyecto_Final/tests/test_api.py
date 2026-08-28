import asyncio
from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient

from app.api.main import create_app
from app.persistence import JobStore
from tests.test_job_store import FakeRedis


class FakeWorkerPool:
    def __init__(self) -> None:
        self.enqueued = []

    async def enqueue(self, job_id, approval=None) -> None:
        self.enqueued.append((job_id, approval))


def test_create_and_get_task() -> None:
    redis = FakeRedis()
    worker = FakeWorkerPool()

    @asynccontextmanager
    async def lifespan(app):
        app.state.redis = redis
        app.state.job_store = JobStore(redis)
        app.state.worker_pool = worker
        yield

    async def scenario() -> None:
        app = create_app(lifespan=lifespan)
        transport = ASGITransport(app=app)
        async with app.router.lifespan_context(app):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                created = await client.post(
                    "/v1/tasks", json={"query": "Diagnose query queue contention"}
                )
                assert created.status_code == 202
                payload = created.json()
                fetched = await client.get(f"/v1/tasks/{payload['id']}")
                assert fetched.status_code == 200
                assert fetched.json()["status"] == "PENDING"
                assert len(worker.enqueued) == 1
                health = await client.get("/v1/health")
                ready = await client.get("/v1/ready")
                assert health.json() == {"status": "healthy"}
                assert ready.json() == {"status": "ready"}

    asyncio.run(scenario())
