from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from schemas import ResearchDocument
from vectorstore_client import ChromaKnowledgeClient


def build_research_agent():
    """Agente de investigación que consulta el vectorstore Chroma y devuelve evidencia útil."""
    client = ChromaKnowledgeClient()

    def research_tool(query: str) -> str:
        docs = client.search(query, k=5)
        return client.summarize(docs)

    return create_react_agent(
        model="openai/gpt-4o-mini",
        tools=[research_tool],
        prompt=(
            "Eres un agente de investigación especializado en recuperar evidencia técnica "
            "de una base de conocimiento local. Tu trabajo es buscar hechos, contexto y "
            "referencias relevantes para responder la consulta del usuario. "
            "Nunca inventes información; usa solo la evidencia recuperada."
        ),
    )


def run_research_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta la investigación y guarda la evidencia en el estado compartido."""
    query = state.get("query") or ""
    if not query:
        return {**state, "research_data": [], "task_completed": False, "next_agent": "END"}

    client = ChromaKnowledgeClient()
    docs = client.search(query, k=5)
    summary = client.summarize(docs)

    validated_docs = [ResearchDocument.model_validate(doc) for doc in docs]
    state["research_data"] = [doc.model_dump() for doc in validated_docs]
    state["contributions"]["research"] = [summary]
    state["next_agent"] = "ANALYZE" if docs else "END"
    state["step_count"] = state.get("step_count", 0) + 1
    return state
