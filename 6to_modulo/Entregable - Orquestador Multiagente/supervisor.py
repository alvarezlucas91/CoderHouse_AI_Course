from __future__ import annotations

from typing import Any


MAX_STEPS = 6


def validate_analysis(state: dict[str, Any]) -> tuple[bool, str]:
    """Valida si la evidencia y el análisis cumplen los criterios mínimos."""
    research_data = state.get("research_data") or []
    analysis_results = state.get("analysis_results") or {}

    if not research_data:
        return False, "No hay evidencia suficiente para continuar."

    if not analysis_results:
        return False, "El analista aún no generó una salida válida."

    if not analysis_results.get("valid", False):
        return False, "El análisis no supera la validación de calidad."

    if len(research_data) < 1:
        return False, "Se requieren al menos algunos documentos relevantes."

    return True, "El resultado cumple la validación del supervisor."


def supervisor_node(state: dict[str, Any]) -> dict[str, Any]:
    """Decide quién debe intervenir ahora o si se debe cerrar el flujo."""
    step_count = state.get("step_count", 0)
    research_data = state.get("research_data") or []
    analysis_results = state.get("analysis_results") or {}

    if step_count >= MAX_STEPS:
        state["next_agent"] = "END"
        state["task_completed"] = True
        state["validation_status"] = "FAILED"
        return state

    if not research_data:
        state["next_agent"] = "RESEARCH"
        state["task_completed"] = False
        state["validation_status"] = "PENDING"
        return state

    if not analysis_results:
        state["next_agent"] = "ANALYZE"
        state["task_completed"] = False
        state["validation_status"] = "PENDING"
        return state

    is_valid, reason = validate_analysis(state)
    if is_valid:
        state["next_agent"] = "END"
        state["task_completed"] = True
        state["validation_status"] = "PASSED"
        state.setdefault("contributions", {}).setdefault("validation", []).append(reason)
        return state

    state["next_agent"] = "VALIDATE"
    state["task_completed"] = False
    state["validation_status"] = "FAILED"
    state.setdefault("contributions", {}).setdefault("validation", []).append(reason)
    return state


def validation_node(state: dict[str, Any]) -> dict[str, Any]:
    """Aplica la validación final y decide si requiere reanálisis o cierre."""
    is_valid, reason = validate_analysis(state)
    if is_valid:
        state["next_agent"] = "END"
        state["task_completed"] = True
        state["validation_status"] = "PASSED"
        state.setdefault("contributions", {}).setdefault("validation", []).append(reason)
        return state

    state["next_agent"] = "ANALYZE"
    state["task_completed"] = False
    state["validation_status"] = "FAILED"
    state.setdefault("contributions", {}).setdefault("validation", []).append(reason)
    return state
