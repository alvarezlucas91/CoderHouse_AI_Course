from __future__ import annotations

from typing import Any

from langgraph.types import Command, interrupt

from app.observability import traced_node

CRITICAL_TERMS = {
    "borrar", "eliminar", "delete", "transferir", "comprar", "publicar",
    "enviar email", "producción", "production", "deploy", "pagar",
}
HIGH_COST_USD = 0.10


@traced_node("agent.risk_assessment")
async def assess_risk(state: dict[str, Any]) -> dict[str, Any]:
    query = state["query"].lower()
    reasons = [f"término crítico: {term}" for term in CRITICAL_TERMS if term in query]
    if state.get("critical"):
        reasons.append("marcada crítica por el cliente")
    if float(state.get("estimated_cost_usd", 0)) >= HIGH_COST_USD:
        reasons.append(f"costo estimado >= USD {HIGH_COST_USD:.2f}")
    return {"critical": bool(reasons), "risk_reasons": sorted(reasons)}


@traced_node("human.approval", kind="CHAIN")
def human_approval(state: dict[str, Any]) -> dict[str, Any]:
    if not state.get("critical"):
        return {"approved": True, "approval_comment": "No requiere aprobación"}
    decision = interrupt({
        "question": "¿Autoriza ejecutar esta tarea crítica?",
        "query": state["query"],
        "reasons": state.get("risk_reasons", []),
    })
    return {
        "approved": bool(decision.get("approved")),
        "approval_comment": decision.get("comment"),
    }


def route_after_approval(state: dict[str, Any]) -> str:
    return "RESEARCH" if state.get("approved") else "REJECT"


@traced_node("human.rejected", kind="CHAIN")
async def reject_task(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_completed": True,
        "validation_status": "REJECTED",
        "result": {"message": "La ejecución fue rechazada por el aprobador humano."},
    }
