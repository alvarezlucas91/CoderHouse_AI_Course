from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import MessagesState

from schemas import MultiAgentStateModel

AgentRoute = Literal["SUPERVISOR", "RESEARCH", "ANALYZE", "VALIDATE", "END"]


class MultiAgentState(MessagesState):
    """Estado compartido del orquestador multi-agente.

    Se extiende desde MessagesState para mantener el historial de mensajes de
    LangGraph y, además, controla la coordinación y validación del flujo.
    """

    query: str
    research_data: list[dict[str, Any]]
    analysis_results: dict[str, Any]
    next_agent: AgentRoute
    task_completed: bool
    step_count: int
    contributions: dict[str, list[str]]
    validation_status: Literal["PENDING", "PASSED", "FAILED"]

    @classmethod
    def validate_payload(cls, state: dict[str, Any]) -> "MultiAgentState":
        """Valida un payload entrante con Pydantic y lo convierte a un estado compatible."""
        validated = MultiAgentStateModel.model_validate(state)
        normalized = dict(validated)
        normalized["research_data"] = [doc.model_dump() for doc in validated.research_data]
        return cls(**normalized)
