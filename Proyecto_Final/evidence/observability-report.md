# Evidencia de observabilidad

Fecha de ejecución: 2026-08-28  
Proyecto Phoenix: `redshift-intelligence`  
Dashboard local: <http://localhost:6006>

## Resultado de las cinco pruebas

| Escenario | Job ID | Estado inicial | Estado final |
|---|---|---|---|
| Función del leader node | `8e9d57b9-72f0-4043-9e1f-3f839627b1ae` | DONE | DONE |
| Queue time alto | `6a9cd564-f2e9-45b0-82c3-6f22f898ab29` | WAITING_APPROVAL | DONE |
| DS_BCAST_INNER | `46866f7a-1211-49a3-aabf-2929a758fdab` | DONE | DONE |
| Error de datos en COPY | `a05f84b5-fc2e-4fcf-b2fe-f2515d492420` | DONE | DONE |
| Optimización frente a escalado | `bb6ea85d-5b3d-470f-92ec-c74b9695ec0d` | WAITING_APPROVAL | DONE |

Los dos casos en `WAITING_APPROVAL` se reanudaron mediante
`POST /v1/tasks/{job_id}/approval`, usando el mismo `thread_id` persistido por el
checkpointer de LangGraph en Redis. Ambos finalizaron con resultado y sin reiniciar
el servidor.

El reporte reproducible de la ejecución se encuentra en
[`load-test-report.json`](load-test-report.json). El lote tardó 773,61 segundos y
se ejecutó con concurrencia 1 para respetar el límite de tokens por minuto de la
cuenta Groq utilizada durante la prueba.

## Verificación de Phoenix

La API local de Phoenix devolvió:

- 725 spans.
- 23 trazas.
- 23 spans raíz `worker.execute` / `LangGraph` acumulados durante las pruebas.
- 18 ejecuciones de `rag.hybrid_search`.
- 18 ejecuciones de `retriever.pinecone`.
- 18 ejecuciones de `retriever.bm25`.
- 68 ejecuciones del Supervisor.
- Spans de diagnóstico, optimización, validación y aprobación humana.

La cantidad acumulada incluye las ejecuciones de estabilización previas al lote
definitivo. Los cinco Job IDs de la tabla permiten localizar las trazas finales en
el dashboard.

## Capturas requeridas para la entrega

Desde <http://localhost:6006>, seleccionar el proyecto
`redshift-intelligence`, filtrar por el horario del lote final y guardar las
capturas indicadas en [`README.md`](README.md). Las capturas son la única evidencia
visual que debe realizarse manualmente desde el navegador.
