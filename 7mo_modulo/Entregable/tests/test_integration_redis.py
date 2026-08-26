from __future__ import annotations

import os
import time

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REDIS_INTEGRATION") != "1",
    reason="requiere Redis 8 local; usar RUN_REDIS_INTEGRATION=1",
)


def _wait(client: TestClient, job_id: str, expected: set[str]) -> dict:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        job = client.get(f"/tasks/{job_id}").json()
        if job["status"] in expected:
            return job
        time.sleep(0.05)
    raise AssertionError(f"timeout esperando {expected}; último estado={job}")


def test_api_queue_checkpoint_and_hitl(monkeypatch: pytest.MonkeyPatch):
    os.environ["PHOENIX_ENABLED"] = "false"
    from app import graph as graph_module
    from app.main import app

    monkeypatch.setattr(graph_module, "_retrieve", lambda query: [{
        "content": f"evidencia para {query}",
        "metadata": {"source": "integration-test"},
        "distance": 0.01,
    }])
    with TestClient(app) as client:
        response = client.post("/tasks", json={"query": "Analiza esta evidencia"})
        assert response.status_code == 202
        assert response.json()["status"] == "PENDING"
        done = _wait(client, response.json()["id"], {"DONE", "FAILED"})
        assert done["status"] == "DONE"

        response = client.post("/tasks", json={
            "query": "Publicar cambios en producción", "critical": True
        })
        waiting = _wait(client, response.json()["id"], {"WAITING_APPROVAL", "FAILED"})
        assert waiting["status"] == "WAITING_APPROVAL"
        assert waiting["approval_request"]["question"]
        approved = client.post(
            f"/tasks/{waiting['id']}/approve",
            json={"approved": True, "comment": "validado"},
        )
        assert approved.status_code == 202
        final = _wait(client, waiting["id"], {"DONE", "FAILED"})
        assert final["status"] == "DONE"
