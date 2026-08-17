from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AgentRoute = Literal["SUPERVISOR", "RESEARCH", "ANALYZE", "VALIDATE", "END"]


class ResearchDocument(BaseModel):
    """Representa un documento recuperado del vector store."""

    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    distance: float | None = None


class AnalysisResultModel(BaseModel):
    """Resultado generado por el agente analítico."""

    sentiment: Literal["positivo", "neutral", "negativo"]
    summary: str = Field(min_length=1)
    valid: bool
    document_count: int = Field(ge=0)
    sources: list[str] = Field(default_factory=list)


class MultiAgentStateModel(BaseModel):
    """Valida y documenta el payload del estado compartido del grafo."""

    model_config = ConfigDict(extra="allow")

    messages: list[Any] = Field(default_factory=list)
    query: str = ""
    research_data: list[ResearchDocument] = Field(default_factory=list)
    analysis_results: dict[str, Any] | AnalysisResultModel = Field(default_factory=dict)
    next_agent: AgentRoute = "SUPERVISOR"
    task_completed: bool = False
    step_count: int = 0
    contributions: dict[str, list[str]] = Field(
        default_factory=lambda: {"research": [], "analysis": [], "validation": []}
    )
    validation_status: Literal["PENDING", "PASSED", "FAILED"] = "PENDING"

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "MultiAgentStateModel":
        """Crea un modelo validado a partir de un payload en dict."""
        return cls.model_validate(state)


def validate_state_payload(state: dict[str, Any]) -> MultiAgentStateModel:
    """Valida un payload antes de que el grafo lo procese."""
    return MultiAgentStateModel.from_state(state)
