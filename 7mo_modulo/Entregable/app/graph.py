from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.hitl import assess_risk, human_approval, reject_task, route_after_approval
from app.observability import traced_node


class AgentState(TypedDict, total=False):
    query: str
    critical: bool
    estimated_cost_usd: float
    risk_reasons: list[str]
    approved: bool
    approval_comment: str | None
    research_data: list[dict[str, Any]]
    analysis_results: dict[str, Any]
    validation_status: str
    task_completed: bool
    result: dict[str, Any]


def _vectorstore_path() -> Path:
    configured = os.getenv("CHROMA_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "3er_modulo" / "Entregable" / "vectorstore"


def _retrieve(query: str) -> list[dict[str, Any]]:
    from chromadb import PersistentClient

    # El volumen Docker es de solo lectura. `get_or_create_collection` intenta
    # escribir en SQLite aun cuando la colección ya existe.
    collection = PersistentClient(path=str(_vectorstore_path())).get_collection(
        "technical_documents"
    )
    result = collection.query(
        query_texts=[query], n_results=5, include=["documents", "metadatas", "distances"]
    )
    return [
        {"content": text, "metadata": metadata or {}, "distance": distance}
        for text, metadata, distance in zip(
            result.get("documents", [[]])[0],
            result.get("metadatas", [[]])[0],
            result.get("distances", [[]])[0],
        )
    ]


@traced_node("agent.research")
async def research_agent(state: AgentState) -> dict[str, Any]:
    # Chroma es sync: se mueve fuera del event loop.
    documents = await asyncio.to_thread(_retrieve, state["query"])
    return {"research_data": documents}


@traced_node("agent.analyst")
async def analyst_agent(state: AgentState) -> dict[str, Any]:
    documents = state.get("research_data", [])
    sources = [doc.get("metadata", {}).get("source", "unknown") for doc in documents]
    snippets = [(doc.get("content") or "").strip()[:400] for doc in documents]
    return {"analysis_results": {
        "summary": " ".join(snippets) if snippets else "No se recuperó evidencia.",
        "document_count": len(documents),
        "sources": sources,
        "valid": bool(documents and all(snippets)),
    }}


@traced_node("agent.validation")
async def validation_agent(state: AgentState) -> dict[str, Any]:
    analysis = state.get("analysis_results", {})
    valid = bool(analysis.get("valid"))
    return {
        "validation_status": "PASSED" if valid else "FAILED",
        "task_completed": True,
        "result": analysis,
    }


def build_graph(checkpointer: Any):
    """Versión persistente del grafo supervisor/investigador/analista/validador del M6."""
    graph = StateGraph(AgentState)
    graph.add_node("RISK", assess_risk)
    graph.add_node("APPROVAL", human_approval)
    graph.add_node("RESEARCH", research_agent)
    graph.add_node("ANALYZE", analyst_agent)
    graph.add_node("VALIDATE", validation_agent)
    graph.add_node("REJECT", reject_task)
    graph.add_edge(START, "RISK")
    graph.add_edge("RISK", "APPROVAL")
    graph.add_conditional_edges(
        "APPROVAL", route_after_approval, {"RESEARCH": "RESEARCH", "REJECT": "REJECT"}
    )
    graph.add_edge("RESEARCH", "ANALYZE")
    graph.add_edge("ANALYZE", "VALIDATE")
    graph.add_edge("VALIDATE", END)
    graph.add_edge("REJECT", END)
    return graph.compile(checkpointer=checkpointer)
