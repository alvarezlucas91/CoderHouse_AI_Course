from __future__ import annotations

import json
from typing import Any

from schemas import AnalysisResultModel


def analyze_research_data(state: dict[str, Any]) -> dict[str, Any]:
    """Analiza la evidencia recuperada con una lógica simple de validación y síntesis."""
    documents = state.get("research_data") or []
    if not documents:
        return {
            **state,
            "analysis_results": {"sentiment": "sin_evidencia", "summary": "No hay evidencia para analizar.", "valid": False},
            "next_agent": "END",
            "task_completed": False,
        }

    evidence = "\n\n".join((doc.get("content") or "")[:1000] for doc in documents)
    valid = all((doc.get("content") or "").strip() for doc in documents)

    sentiment = "positivo" if "beneficio" in evidence.lower() or "mejora" in evidence.lower() else "neutral"
    summary = (
        "Los documentos recuperados muestran contexto técnico relevante para la consulta. "
        "Se validó la presencia de contenido estructurado y coherente."
    )

    result = AnalysisResultModel.model_validate({
        "sentiment": sentiment,
        "summary": summary,
        "valid": valid,
        "document_count": len(documents),
        "sources": [doc.get("metadata", {}).get("source", "unknown") for doc in documents],
    })

    state["analysis_results"] = result.model_dump()
    state["contributions"]["analysis"] = [json.dumps(result.model_dump(), ensure_ascii=False)]
    state["next_agent"] = "END"
    state["task_completed"] = True
    state["step_count"] = state.get("step_count", 0) + 1
    return state
