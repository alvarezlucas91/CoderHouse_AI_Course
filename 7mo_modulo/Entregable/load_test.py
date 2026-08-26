"""Crea cinco jobs concurrentes y espera su estado terminal."""
from __future__ import annotations

import asyncio
import time

import httpx

QUERIES = [
    "Explica la arquitectura de Amazon Redshift",
    "Resume las estrategias de distribución de datos",
    "Analiza recomendaciones de rendimiento",
    "Compara almacenamiento columnar y por filas",
    "Identifica buenas prácticas de cargas ETL",
]
TERMINAL = {"DONE", "FAILED", "REJECTED"}


async def submit(client: httpx.AsyncClient, query: str) -> dict:
    response = await client.post("/tasks", json={"query": query})
    response.raise_for_status()
    return response.json()


async def wait_for_job(client: httpx.AsyncClient, job_id: str) -> dict:
    while True:
        response = await client.get(f"/tasks/{job_id}")
        response.raise_for_status()
        job = response.json()
        if job["status"] in TERMINAL:
            return job
        await asyncio.sleep(0.25)


async def main() -> None:
    started = time.perf_counter()
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=60) as client:
        jobs = await asyncio.gather(*(submit(client, query) for query in QUERIES))
        print("IDs recibidos sin esperar ejecución:", [job["id"] for job in jobs])
        completed = await asyncio.gather(*(wait_for_job(client, job["id"]) for job in jobs))
    elapsed = time.perf_counter() - started
    print("Estados:", [job["status"] for job in completed])
    print(f"Tiempo total: {elapsed:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
