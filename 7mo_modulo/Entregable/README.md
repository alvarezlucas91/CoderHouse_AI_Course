# Pre-entrega 7 — API multi-agente asíncrona

API FastAPI que expone el orquestador del Módulo 6 con cola no bloqueante,
estado y checkpoints en Redis, trazas OpenTelemetry/OpenInference en Phoenix y
aprobación humana obligatoria para acciones críticas.

## Arquitectura

`POST /tasks` solo valida, persiste `PENDING`, encola y responde `202`. Dos workers
asíncronos (configurables) ejecutan el grafo fuera del endpoint. Chroma, cuya API es
síncrona, se llama con `asyncio.to_thread`, por lo que no bloquea el event loop.

El estado visible del job se guarda en claves `jobs:{uuid}`. El
`AsyncRedisSaver` de LangGraph guarda por separado cada checkpoint usando el mismo
`job_id` como `thread_id`. Si un nodo falla, el worker captura la excepción y deja
el job en `FAILED` con el tipo y mensaje del error.

Flujo del grafo:

```text
START → evaluación de riesgo → aprobación HITL ─┬→ investigación → análisis → validación → END
                                                └→ rechazo → END
```

Una tarea es crítica si el cliente envía `critical=true`, si supera el umbral de
costo (`USD 0.10`) o si contiene términos de efectos secundarios como `borrar`,
`transferir`, `publicar` o `deploy`. En ese caso `interrupt()` persiste el punto
exacto y el job queda en `WAITING_APPROVAL`. El endpoint de aprobación reanuda el
mismo thread con `Command(resume=...)`.

## Inicio rápido con Docker (recomendado)

Requiere Docker Compose. Desde esta carpeta:

```powershell
docker compose up --build
```

Servicios:

- API y Swagger: <http://localhost:8000/docs>
- Phoenix: <http://localhost:6006>
- Redis: `localhost:6379`

Se usa Redis 8 porque el checkpointer requiere RedisJSON y RediSearch. El volumen
del vectorstore del Módulo 3 se monta como semilla de solo lectura y se copia una
vez al volumen Docker escribible `chroma-data`. La colección
`technical_documents` debe existir previamente. La API se ejecuta con un solo
proceso Uvicorn porque la cola de esta pre-entrega vive en memoria; la concurrencia
ocurre dentro del proceso. Para varias réplicas, reemplazar la cola por ARQ/Celery.

## Inicio local

Python 3.12+ y un Redis 8 (o Redis Stack) en ejecución:

```powershell
cd 7mo_modulo/Entregable
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --workers 1
```

Phoenix puede iniciarse con el servicio de Compose (`docker compose up redis
phoenix`) o con una instalación local. Si el colector no está disponible, la API
sigue procesando jobs y registra el problema; para una ejecución deliberadamente
sin exportación usa `PHOENIX_ENABLED=false`.

## Uso de la API

Crear una tarea normal; la respuesta llega antes de ejecutar el grafo:

```powershell
$job = Invoke-RestMethod -Method Post http://localhost:8000/tasks `
  -ContentType 'application/json' `
  -Body '{"query":"Explica la arquitectura de Amazon Redshift"}'
$job
Invoke-RestMethod "http://localhost:8000/tasks/$($job.id)"
```

Probar HITL:

```powershell
$critical = Invoke-RestMethod -Method Post http://localhost:8000/tasks `
  -ContentType 'application/json' `
  -Body '{"query":"Publicar este análisis en producción","critical":true}'

# Esperar hasta observar WAITING_APPROVAL y revisar approval_request.
Invoke-RestMethod "http://localhost:8000/tasks/$($critical.id)"

Invoke-RestMethod -Method Post "http://localhost:8000/tasks/$($critical.id)/approve" `
  -ContentType 'application/json' `
  -Body '{"approved":true,"comment":"Revisado por operaciones"}'
```

Enviar `approved:false` finaliza en `REJECTED`; no ejecuta investigación ni
análisis. Aprobar un job que no esté pausado devuelve `409 Conflict`.

Estados posibles: `PENDING`, `RUNNING`, `WAITING_APPROVAL`, `DONE`, `FAILED` y
`REJECTED`. `GET /tasks/{id}` permite polling y `GET /health` comprueba Redis.

## Cinco peticiones concurrentes y evidencia

Con API, Redis y Phoenix activos:

```powershell
python load_test.py
```

El script usa `asyncio.gather` para crear cinco jobs simultáneamente, imprime los
IDs devueltos inmediatamente y espera sus estados terminales. Abrir Phoenix,
seleccionar `modulo-7-api-agente` y verificar los spans `worker.execute`,
`agent.risk_assessment`, `agent.research`, `agent.analyst` y `agent.validation`.

Guardar capturas reales en `screenshots/` siguiendo
[`screenshots/README.md`](screenshots/README.md). Para demostrar HITL, crear una
tarea crítica, capturar `WAITING_APPROVAL`, aprobarla y mostrar la traza reanudada.

## Pruebas

```powershell
pytest -q
```

Las pruebas unitarias no requieren servicios externos: validan clasificación de
riesgo, bypass de tareas no críticas, ruta de rechazo y persistencia/transición a
`FAILED` mediante Redis simulado. La prueba manual/Compose cubre la integración
real del checkpointer, Chroma y Phoenix.

## Variables

Consultar [`.env.example`](.env.example). No se versionan secretos. Para Phoenix
Cloud se configuran `PHOENIX_COLLECTOR_ENDPOINT` y `PHOENIX_API_KEY`. Los jobs
expiran tras siete días por defecto; los checkpoints de LangGraph permanecen para
auditoría. En producción conviene aplicar una política de retención equivalente.

## Referencias técnicas

- [LangGraph: interrupts y reanudación](https://langchain-ai.github.io/langgraph/concepts/breakpoints/)
- [langgraph-checkpoint-redis](https://github.com/redis-developer/langgraph-redis)
- [Phoenix OTEL para Python](https://arize.com/docs/phoenix/sdk-api-reference/python/arize-phoenix-otel)
