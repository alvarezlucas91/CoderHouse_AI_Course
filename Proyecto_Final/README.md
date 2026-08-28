# Redshift Intelligence

Copiloto multiagente para diagnóstico y optimización de Amazon Redshift. Combina
RAG híbrido, coordinación mediante Supervisor, aprobación humana para acciones
críticas, API asíncrona, persistencia y trazabilidad.

## Estado de implementación

- [x] Configuración validada con Pydantic Settings.
- [x] Contratos Pydantic para API, evidencia, diagnóstico y recomendaciones.
- [x] Corpus autocontenido de doce documentos.
- [x] Recuperación BM25 asíncrona sin bloquear el event loop.
- [x] Recuperación densa con el SDK nativo `PineconeAsyncio`.
- [x] Fusión RRF concurrente y deduplicación de evidencia.
- [x] Grafo LangGraph con Supervisor y agentes especializados.
- [x] Checkpointer Redis e interrupciones HITL.
- [x] FastAPI, workers y persistencia de jobs.
- [ ] Phoenix, Docker Compose y cinco pruebas end-to-end.

## Arquitectura objetivo

```mermaid
flowchart TD
    U[Usuario] --> API[FastAPI]
    API --> S[Supervisor]
    S --> R[Research Agent]
    R --> PR[Pinecone]
    R --> BM[BM25]
    S --> D[Diagnostic Agent]
    S --> O[Optimization Agent]
    S --> V[Validation Agent]
    V -->|Falta evidencia| R
    V -->|Diagnóstico débil| D
    V -->|Acción crítica| H[Human approval]
    V -->|Validado| F[Respuesta con citas]
    H -->|Aprobado| F
    H -->|Rechazado| X[Respuesta sin ejecución]
```

## Desarrollo

Requiere Python 3.12 o superior:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
pytest -q
```

No copies claves desde los módulos anteriores. Configura secretos nuevos en
`Proyecto_Final/.env`, que no debe versionarse.

## Inicio con un solo comando

1. Copiar `.env.example` a `.env` y completar `PINECONE_API_KEY` y
   `GROQ_API_KEY`. El namespace debe coincidir con el corpus indexado.
2. Ejecutar:

```powershell
docker compose up --build
```

Servicios disponibles:

- Swagger/OpenAPI: <http://localhost:8000/docs>
- Phoenix: <http://localhost:6006>
- Redis: `localhost:6379`

La API usa un proceso Uvicorn porque la cola de trabajos vive dentro del proceso.
Redis conserva jobs y checkpoints. Para escalar horizontalmente se debe reemplazar
la cola local por ARQ, Celery u otro broker distribuido.

## Decisiones iniciales

- El dominio depende de protocolos, no de FastAPI, LangGraph o Pinecone.
- Pinecone usa su cliente asyncio nativo y context managers para cerrar sesiones.
- BM25, que es CPU-bound, se ejecuta mediante `asyncio.to_thread`.
- Las recomendaciones de riesgo alto o crítico requieren aprobación por contrato.
- Una validación fallida no puede dirigir el flujo a finalización.

## API

- `POST /v1/tasks`: valida, persiste y encola una tarea; responde `202`.
- `GET /v1/tasks/{job_id}`: consulta el estado y el resultado tipado.
- `POST /v1/tasks/{job_id}/approval`: aprueba o rechaza una pausa HITL.
- `GET /v1/health`: comprueba Redis.
- `GET /v1/ready`: comprueba que los workers estén inicializados.

Crear y consultar una tarea:

```powershell
$job = Invoke-RestMethod -Method Post http://localhost:8000/v1/tasks `
  -ContentType 'application/json' `
  -Body '{"query":"Diagnostica una consulta con queue time elevado"}'

Invoke-RestMethod "http://localhost:8000/v1/tasks/$($job.id)"
```

Reanudar una tarea en `WAITING_APPROVAL`:

```powershell
Invoke-RestMethod -Method Post `
  "http://localhost:8000/v1/tasks/$($job.id)/approval" `
  -ContentType 'application/json' `
  -Body '{"approved":true,"comment":"Revisado por operaciones"}'
```

## Pruebas y evidencia

Pruebas locales:

```powershell
pytest -q
```

Cinco ejecuciones concurrentes contra el sistema completo:

```powershell
python load_test.py
```

En Phoenix seleccionar el proyecto `redshift-intelligence` y comprobar los spans
`worker.execute`, `agent.supervisor`, `agent.research`, `retriever.pinecone`,
`retriever.bm25`, `agent.diagnosis`, `agent.optimization` y `agent.validation`.
Las capturas requeridas se describen en [`evidence/README.md`](evidence/README.md).

## Persistencia y recuperación

Cada job usa su `thread_id` como identificador del checkpoint de LangGraph. Al
reiniciar, los jobs `PENDING` y `RUNNING` se vuelven a encolar. Los jobs
`WAITING_APPROVAL` permanecen pausados hasta recibir una decisión. Los registros
de jobs expiran después de siete días por defecto; los checkpoints requieren una
política de retención operativa explícita.

## Seguridad

- No se versionan secretos ni respuestas completas en variables de entorno.
- La API nunca devuelve el registro interno que contiene la solicitud persistida.
- Las recomendaciones `high` o `critical` requieren aprobación por contrato.
- La aprobación reanuda el mismo thread; el rechazo deja el job en `REJECTED`.
- En una exposición fuera de localhost deben agregarse autenticación, autorización,
  TLS, rate limiting y políticas de red.
