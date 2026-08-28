# Evidencia de observabilidad

Las evidencias reales guardadas en esta carpeta son:

1. `01-overview-traces.PNG`: vista general del proyecto y sus trazas.
2. `02-supervisor-agents.PNG`: árbol de Supervisor y agentes especialistas.
3. `03-rag-hybrid.PNG`: spans de recuperación Pinecone y BM25 bajo RAG híbrido.
4. `04-human-approval.PNG`: reanudación HITL con `HUMAN_APPROVAL` y `FINISH`.
5. `05-api-swagger.PNG`: documentación general de la API.
6. `05-api-swagger-01.PNG` a `05-api-swagger-05.PNG`: endpoints y contratos
   Pydantic desplegados en Swagger.
7. `load-test-report.json`: resultado reproducible de los cinco escenarios.
8. `observability-report.md`: IDs, estados y resumen cuantitativo de Phoenix.

El lote se ejecutó con concurrencia 1 para respetar la cuota de Groq. Esto no cambia
la naturaleza asíncrona de la API ni del sistema; el runner permite seleccionar
entre 1 y 5 escenarios concurrentes con `--concurrency`.

No se deben fabricar capturas. Phoenix está disponible en
<http://127.0.0.1:6006> mientras Docker Compose esté activo.
