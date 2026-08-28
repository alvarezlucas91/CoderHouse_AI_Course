import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

import httpx


SCENARIOS = [
    "Explica la función del leader node y cita la evidencia.",
    "Diagnostica una consulta con queue time alto y execution time normal.",
    "¿Qué significa DS_BCAST_INNER y cómo debería investigarlo?",
    "Una carga COPY falló por datos inválidos: indica el procedimiento de diagnóstico.",
    "¿Cómo decido entre optimizar una consulta y aumentar la capacidad?",
]
TERMINAL = {"DONE", "FAILED", "REJECTED"}


async def submit(client: httpx.AsyncClient, query: str) -> str:
    response = await client.post("/v1/tasks", json={"query": query})
    response.raise_for_status()
    return response.json()["id"]


async def wait_for_result(client: httpx.AsyncClient, job_id: str, timeout: float) -> dict:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        response = await client.get(f"/v1/tasks/{job_id}")
        response.raise_for_status()
        job = response.json()
        if job["status"] in TERMINAL or job["status"] == "WAITING_APPROVAL":
            return job
        await asyncio.sleep(1)
    raise TimeoutError(f"Task {job_id} did not finish in {timeout} seconds")


async def run(base_url: str, timeout: float, concurrency: int, output: Path) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        started = monotonic()
        semaphore = asyncio.Semaphore(concurrency)

        async def execute(query: str) -> dict:
            async with semaphore:
                job_id = await submit(client, query)
                return await wait_for_result(client, job_id, timeout)

        jobs = await asyncio.gather(*(execute(query) for query in SCENARIOS))
    report = {
        "executed_at": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "scenario_count": len(SCENARIOS),
        "concurrency": concurrency,
        "elapsed_seconds": round(monotonic() - started, 2),
        "tasks": [
            {
                "scenario": scenario,
                "id": job["id"],
                "status": job["status"],
                "has_result": bool(job["result"]),
                "error": job.get("error"),
            }
            for scenario, job in zip(SCENARIOS, jobs, strict=True)
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if any(job["status"] == "FAILED" for job in jobs):
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run five end-to-end scenarios")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        choices=range(1, 6),
        metavar="1..5",
        help="Concurrent scenarios; keep 1 for provider free-tier quotas.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evidence/load-test-report.json"),
        help="Path for the reproducible JSON evidence report.",
    )
    arguments = parser.parse_args()
    asyncio.run(run(arguments.base_url, arguments.timeout, arguments.concurrency, arguments.output))
