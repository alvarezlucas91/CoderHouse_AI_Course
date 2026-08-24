"""Ejercicio 1 - Observabilidad de un orquestador multiagente con Phoenix.

Reutiliza el cliente Chroma del entregable del módulo 6 y ejecuta el flujo:

    supervisor (AGENT)
      ├─ research_agent (AGENT) -> rag_search (TOOL) -> Chroma (RETRIEVER)
      ├─ analyst_agent (AGENT)  -> synthesize (TOOL) -> OpenAI SDK (LLM)
      └─ validation_agent (AGENT)

Phoenix debe estar levantado antes de ejecutar la batería. Ejemplos:

    python Ejercicio_1.py --smoke-test
    python Ejercicio_1.py --run-suite
    python Ejercicio_1.py --query "Compara Redshift con un data warehouse tradicional"

Variables de entorno:
    PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces
    PHOENIX_PROJECT_NAME=modulo-7-multiagente
    GROQ_API_KEY=...                 # se usa mediante su API compatible con OpenAI
    LLM_MODEL=llama-3.3-70b-versatile

El endpoint HTTP/protobuf (6006/v1/traces) evita depender del puerto gRPC. No se
guardan prompts, claves ni respuestas fuera de la traza local de Phoenix.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1] if HERE.name == "Demo_Phoenix" else HERE.parent
MODULE6 = PROJECT_ROOT / "6to_modulo" / "Entregable - Orquestador Multiagente"
DEFAULT_VECTORSTORE = PROJECT_ROOT / "3er_modulo" / "Entregable" / "vectorstore"
REPORT_PATH = HERE / "hallazgos_phoenix.md"

try:
    from dotenv import load_dotenv

    load_dotenv(HERE / ".env")
except ImportError:
    pass  # --smoke-test informará la dependencia si el flujo la necesita.

# Reutilización explícita del sistema del módulo anterior.
if str(MODULE6) not in sys.path:
    sys.path.insert(0, str(MODULE6))


SUITE_QUERIES = [
    "Explica la arquitectura de Amazon Redshift, identifica sus componentes y relaciona cada afirmación con una fuente.",
    "Compara procesamiento, almacenamiento y escalabilidad de Redshift usando únicamente la documentación recuperada.",
    "Propón una estrategia de rendimiento para Redshift y separa hechos documentados de recomendaciones inferidas.",
    "Analiza ventajas, limitaciones y casos de uso de la arquitectura descrita; cita la evidencia de cada conclusión.",
    "Construye un resumen técnico de la información disponible, detecta contradicciones y declara cualquier dato faltante.",
]


@dataclass
class RunMetrics:
    query: str
    trace_id: str
    total_ms: float = 0.0
    retrieval_ms: float = 0.0
    llm_network_ms: float = 0.0
    processing_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float | None = None
    grounded: bool = False
    status: str = "OK"
    error: str = ""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def configure_tracing():
    """Registra OTLP/OpenInference e instrumenta el SDK OpenAI.

    La búsqueda Chroma se instrumenta manualmente porque OpenInference no
    distribuye actualmente un instrumentor oficial específico para chromadb.
    El span usa las convenciones RETRIEVER y contiene documentos y distancias.
    """
    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        raise RuntimeError(
            "Faltan dependencias de observabilidad. Ejecuta: "
            "pip install -r 7mo_modulo/Demo_Phoenix/requirements.txt"
        ) from exc

    endpoint = os.getenv(
        "PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"
    )
    project = os.getenv("PHOENIX_PROJECT_NAME", "modulo-7-multiagente")
    resource = Resource.create({"service.name": project, "openinference.project.name": project})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    OpenAIInstrumentor().instrument(tracer_provider=provider)
    return provider, provider.get_tracer("modulo7.multiagente")


def _span(tracer, name: str, kind: str, **attributes: Any) -> Iterator[Any]:
    """Crea un span con atributos OpenInference sin acoplarse a sus enums."""
    attrs = {"openinference.span.kind": kind, **attributes}
    return tracer.start_as_current_span(name, attributes=attrs, record_exception=True)


def _trace_id(span: Any) -> str:
    return f"{span.get_span_context().trace_id:032x}"


def _load_client(vectorstore: Path):
    from vectorstore_client import ChromaKnowledgeClient

    return ChromaKnowledgeClient(str(vectorstore))


def retrieve_documents(tracer, query: str, vectorstore: Path, k: int = 5):
    """Herramienta RAG; deja que los fallos suban para marcarlos como ERROR."""
    from opentelemetry.trace import Status, StatusCode

    with _span(
        tracer,
        "tool.rag_search",
        "TOOL",
        **{"tool.name": "rag_search", "input.value": query, "input.mime_type": "text/plain"},
    ) as tool_span:
        start = time.perf_counter()
        try:
            client = _load_client(vectorstore)
            with _span(
                tracer,
                "chroma.collection.query",
                "RETRIEVER",
                **{
                    "db.system": "chroma",
                    "db.namespace": "technical_documents",
                    "retrieval.top_k": k,
                    "input.value": query,
                    "input.mime_type": "text/plain",
                    "app.latency.category": "local_processing",
                },
            ) as span:
                raw = client.collection.query(
                    query_texts=[query],
                    n_results=k,
                    include=["documents", "metadatas", "distances"],
                )
                docs = [
                    {"content": doc, "metadata": meta or {}, "distance": distance}
                    for doc, meta, distance in zip(
                        raw.get("documents", [[]])[0],
                        raw.get("metadatas", [[]])[0],
                        raw.get("distances", [[]])[0],
                    )
                ]
                span.set_attribute("retrieval.documents", _json(docs))
                span.set_attribute("retrieval.document_count", len(docs))
            elapsed = (time.perf_counter() - start) * 1000
            tool_span.set_attribute("output.value", _json(docs))
            tool_span.set_attribute("app.duration_ms", elapsed)
            return docs, elapsed
        except Exception as exc:
            tool_span.set_status(Status(StatusCode.ERROR, str(exc)))
            tool_span.set_attribute("error.type", type(exc).__name__)
            raise


def _documents_as_context(documents: list[dict[str, Any]]) -> str:
    blocks = []
    for index, doc in enumerate(documents, 1):
        source = doc.get("metadata", {}).get("source", f"documento_{index}")
        content = (doc.get("content") or "").strip()[:1800]
        blocks.append(f"[{index}] Fuente: {source}\n{content}")
    return "\n\n".join(blocks)


def synthesize_answer(tracer, query: str, documents: list[dict[str, Any]]):
    """Llama al LLM mediante OpenAI SDK; su instrumentor crea el span LLM hijo."""
    from openai import OpenAI

    api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Define GROQ_API_KEY u OPENAI_API_KEY para ejecutar el analista.")

    using_groq = bool(os.getenv("GROQ_API_KEY"))
    base_url = "https://api.groq.com/openai/v1" if using_groq else None
    model = os.getenv(
        "LLM_MODEL", "llama-3.3-70b-versatile" if using_groq else "gpt-4o-mini"
    )
    client = OpenAI(api_key=api_key, base_url=base_url)

    build_start = time.perf_counter()
    context = _documents_as_context(documents)
    system = (
        "Eres el agente analista de un sistema RAG. Responde solo con evidencia del "
        "CONTEXTO. Cita [n] después de cada afirmación. Si no hay sustento, dilo. "
        "Devuelve JSON estricto con: answer (string), citations (array de enteros), "
        "grounded (boolean) y missing_information (array de strings)."
    )
    prompt = f"CONSULTA:\n{query}\n\nCONTEXTO:\n{context}"
    processing_ms = (time.perf_counter() - build_start) * 1000

    with _span(
        tracer,
        "tool.synthesize_grounded_answer",
        "TOOL",
        **{"tool.name": "synthesize_grounded_answer", "input.value": prompt},
    ) as span:
        network_start = time.perf_counter()
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        network_ms = (time.perf_counter() - network_start) * 1000
        content = response.choices[0].message.content or "{}"
        parse_start = time.perf_counter()
        result = json.loads(content)
        citations = result.get("citations") or []
        valid_citations = all(isinstance(i, int) and 1 <= i <= len(documents) for i in citations)
        grounded = bool(result.get("grounded") and citations and valid_citations)
        processing_ms += (time.perf_counter() - parse_start) * 1000
        usage = response.usage
        tokens = {
            "prompt": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion": int(getattr(usage, "completion_tokens", 0) or 0),
            "total": int(getattr(usage, "total_tokens", 0) or 0),
        }
        span.set_attribute("output.value", content)
        span.set_attribute("app.network_latency_ms", network_ms)
        span.set_attribute("app.processing_latency_ms", processing_ms)
        span.set_attribute("app.grounded", grounded)
        span.set_attribute("llm.token_count.total", tokens["total"])
        return result, tokens, network_ms, processing_ms, grounded


def estimate_cost(tokens: dict[str, int]) -> float | None:
    """Costo opcional según tarifas configuradas, sin fijar precios que cambian."""
    input_per_million = os.getenv("LLM_INPUT_USD_PER_MILLION")
    output_per_million = os.getenv("LLM_OUTPUT_USD_PER_MILLION")
    if input_per_million is None or output_per_million is None:
        return None
    return (
        tokens["prompt"] * float(input_per_million)
        + tokens["completion"] * float(output_per_million)
    ) / 1_000_000


def run_workflow(tracer, query: str, vectorstore: Path = DEFAULT_VECTORSTORE) -> tuple[dict[str, Any], RunMetrics]:
    """Orquestador jerárquico inspirado en el grafo del módulo 6."""
    from opentelemetry.trace import Status, StatusCode

    started = time.perf_counter()
    metrics = RunMetrics(query=query, trace_id="")
    result: dict[str, Any] = {}
    with _span(
        tracer,
        "supervisor.multiagent_rag",
        "AGENT",
        **{"input.value": query, "input.mime_type": "text/plain", "session.id": "modulo-7-suite"},
    ) as root:
        metrics.trace_id = _trace_id(root)
        try:
            with _span(tracer, "agent.research", "AGENT", **{"agent.name": "research_agent"}):
                documents, metrics.retrieval_ms = retrieve_documents(tracer, query, vectorstore)
            if not documents:
                raise LookupError("La búsqueda no recuperó documentos; no se puede fundamentar la respuesta.")

            with _span(tracer, "agent.analyst", "AGENT", **{"agent.name": "analyst_agent"}):
                result, tokens, metrics.llm_network_ms, metrics.processing_ms, metrics.grounded = synthesize_answer(
                    tracer, query, documents
                )
            metrics.prompt_tokens = tokens["prompt"]
            metrics.completion_tokens = tokens["completion"]
            metrics.total_tokens = tokens["total"]
            metrics.estimated_cost_usd = estimate_cost(tokens)

            with _span(tracer, "agent.validation", "AGENT", **{"agent.name": "validation_agent"}) as validation:
                citations = result.get("citations") or []
                validation.set_attribute("evaluation.name", "groundedness")
                validation.set_attribute("evaluation.score", 1.0 if metrics.grounded else 0.0)
                validation.set_attribute("evaluation.label", "grounded" if metrics.grounded else "not_grounded")
                validation.set_attribute("validation.citation_count", len(citations))
            root.set_attribute("output.value", _json(result))
            root.set_attribute("app.grounded", metrics.grounded)
        except Exception as exc:
            metrics.status = "ERROR"
            metrics.error = f"{type(exc).__name__}: {exc}"
            root.set_status(Status(StatusCode.ERROR, str(exc)))
            root.set_attribute("error.type", type(exc).__name__)
            root.set_attribute("error.message", str(exc))
        finally:
            metrics.total_ms = (time.perf_counter() - started) * 1000
            root.set_attribute("app.total_latency_ms", metrics.total_ms)
    return result, metrics


def write_report(rows: list[RunMetrics], path: Path = REPORT_PATH) -> None:
    successful = [row for row in rows if row.status == "OK"]
    slowest = max(successful, key=lambda row: max(row.retrieval_ms, row.llm_network_ms), default=None)
    longest = max(successful, key=lambda row: row.total_tokens, default=None)
    table = [
        "| Traza | Estado | Total ms | Chroma ms | Red/API LLM ms | Proceso ms | Tokens | Grounded |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        table.append(
            f"| `{row.trace_id}` | {row.status} | {row.total_ms:.1f} | {row.retrieval_ms:.1f} | "
            f"{row.llm_network_ms:.1f} | {row.processing_ms:.1f} | {row.total_tokens} | {row.grounded} |"
        )
    findings = "Aún no hubo ejecuciones exitosas."
    if slowest and longest:
        dominant = "generación del LLM/red" if slowest.llm_network_ms >= slowest.retrieval_ms else "recuperación Chroma"
        cost = "no calculado (faltan tarifas)" if longest.estimated_cost_usd is None else f"USD {longest.estimated_cost_usd:.6f}"
        findings = (
            f"El span dominante fue **{dominant}** en la traza `{slowest.trace_id}`. "
            f"La llamada LLM tardó {slowest.llm_network_ms:.1f} ms (red + inferencia remota), "
            f"Chroma {slowest.retrieval_ms:.1f} ms (proceso local) y el procesamiento local "
            f"medido {slowest.processing_ms:.1f} ms. El razonamiento más largo fue "
            f"`{longest.trace_id}` con {longest.total_tokens} tokens; costo: {cost}."
        )
    content = f"""# Hallazgos de observabilidad — Phoenix

> Generado automáticamente. Abrir `http://localhost:6006` y filtrar el proyecto
> `modulo-7-multiagente`. Para una URL compartible, publicar este archivo en Drive,
> Notion o un repositorio y pegar aquí el enlace: **PENDIENTE**.

## Resultados

{chr(10).join(table)}

## Análisis

{findings}

- **Latencia:** `app.network_latency_ms` incluye transporte e inferencia de la API;
  `app.processing_latency_ms` cubre construcción/parseo local; Chroma se marca como
  `local_processing`. El span OpenAI permite inspeccionar además la llamada del SDK.
- **Groundedness:** se exige al menos una cita válida `[n]` dentro del rango de
  documentos recuperados. `grounded=false` indica respuesta sin evidencia suficiente
  o citas inválidas y se ve también en el span de validación.
- **Fallo intencional:** la fila `ERROR` usa una ruta Chroma inexistente/no válida. El
  span `tool.rag_search` y su ancestro quedan en estado ERROR, en vez de convertir el
  error en evidencia.
- **Eficiencia:** reducir `top_k`, recortar fragmentos repetidos y limitar el contexto
  enviado al analista baja tokens y latencia sin ocultar la recuperación.
"""
    path.write_text(content, encoding="utf-8")


def run_suite(tracer) -> list[RunMetrics]:
    rows = []
    for number, query in enumerate(SUITE_QUERIES, 1):
        result, metrics = run_workflow(tracer, query)
        rows.append(metrics)
        print(f"[{number}/5] {metrics.status} trace={metrics.trace_id} tokens={metrics.total_tokens}")
        if result:
            print(result.get("answer", "")[:240])

    # Fallo observable y reproducible: un archivo se usa como directorio de persistencia.
    _, failed = run_workflow(tracer, "Consulta de control que debe fallar", Path(__file__))
    rows.append(failed)
    print(f"[fallo] {failed.status} trace={failed.trace_id}: {failed.error}")
    write_report(rows)
    return rows


def smoke_test() -> None:
    """Comprueba datos y dependencias sin enviar trazas ni consumir tokens."""
    required = [
        ("chromadb", "chromadb"),
        ("openai", "openai"),
        ("OpenInference OpenAI", "openinference.instrumentation.openai"),
        ("OTLP HTTP", "opentelemetry.exporter.otlp.proto.http.trace_exporter"),
    ]
    missing = []
    for label, module in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(label)
    if not DEFAULT_VECTORSTORE.exists():
        missing.append(f"vectorstore: {DEFAULT_VECTORSTORE}")
    if missing:
        raise RuntimeError("Faltan: " + ", ".join(missing))
    client = _load_client(DEFAULT_VECTORSTORE)
    print(f"OK: colección={client.collection.name}, documentos={client.collection.count()}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Observabilidad de un orquestador multiagente con Phoenix y OpenInference."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-suite", action="store_true", help="5 consultas + 1 fallo intencional")
    group.add_argument("--query", help="ejecuta una consulta")
    group.add_argument("--smoke-test", action="store_true", help="valida dependencias y Chroma sin API")
    args = parser.parse_args()
    if args.smoke_test:
        smoke_test()
        return 0

    provider, tracer = configure_tracing()
    try:
        if args.run_suite:
            run_suite(tracer)
            print(f"Reporte: {REPORT_PATH}")
        else:
            result, metrics = run_workflow(tracer, args.query)
            print(_json(result if result else asdict(metrics)))
            write_report([metrics])
            if metrics.status == "ERROR":
                return 1
    finally:
        provider.force_flush()
        provider.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
