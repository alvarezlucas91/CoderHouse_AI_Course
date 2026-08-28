import json
from dataclasses import dataclass
from typing import Any

from langgraph.types import interrupt

from app.agents import StructuredModel
from app.rag import HybridRAGService
from app.schemas import (
    AgentRoute,
    DiagnosticReport,
    RecommendationPlan,
    RetrievalQuery,
    SupervisorDecision,
    ValidationResult,
)

from .state import IntelligenceState


@dataclass(frozen=True)
class NodeDependencies:
    model: StructuredModel
    rag: HybridRAGService


def _audit(state: IntelligenceState, agent: str, event: str) -> list[dict[str, Any]]:
    return [*state.get("audit_log", []), {"agent": agent, "event": event}]


def _snapshot(state: IntelligenceState) -> str:
    evidence = [
        {
            "evidence_id": item.get("evidence_id"),
            "title": item.get("title"),
            "section": item.get("section"),
            "source": item.get("source"),
            "content": str(item.get("content", ""))[:1200],
        }
        for item in state.get("evidence", [])
    ]
    return json.dumps(
        {
            "query": state.get("query"),
            "evidence": evidence,
            "diagnosis": state.get("diagnosis"),
            "recommendation_plan": state.get("recommendation_plan"),
            "validation": state.get("validation"),
            "iteration": state.get("iteration", 0),
        },
        ensure_ascii=False,
        default=str,
    )


def _guarded_route(state: IntelligenceState, proposal: AgentRoute) -> AgentRoute:
    if not state.get("evidence"):
        return AgentRoute.RESEARCH
    if not state.get("diagnosis"):
        return AgentRoute.DIAGNOSE
    if not state.get("recommendation_plan"):
        return AgentRoute.OPTIMIZE
    validation_raw = state.get("validation")
    if not validation_raw:
        return AgentRoute.VALIDATE

    validation = ValidationResult.model_validate(validation_raw)
    if not validation.passed:
        allowed = {AgentRoute.RESEARCH, AgentRoute.DIAGNOSE, AgentRoute.OPTIMIZE}
        return proposal if proposal in allowed else validation.next_agent

    plan = RecommendationPlan.model_validate(state["recommendation_plan"])
    if any(item.requires_approval for item in plan.recommendations) and not state.get("approval"):
        return AgentRoute.HUMAN_APPROVAL
    return AgentRoute.FINISH


async def supervisor_node(
    state: IntelligenceState, dependencies: NodeDependencies
) -> dict[str, Any]:
    iteration = state.get("iteration", 0) + 1
    max_iterations = state.get("max_iterations", 8)
    if iteration > max_iterations:
        decision = SupervisorDecision(
            next_agent=AgentRoute.FINISH,
            reason="Maximum graph iterations reached; returning a bounded partial result.",
            missing_information=["The workflow did not converge before its safety limit."],
            iteration=max_iterations,
        )
        return {
            "supervisor_decision": decision.model_dump(mode="json"),
            "iteration": iteration,
            "final_answer": "No fue posible completar un diagnóstico validado dentro del límite de iteraciones.",
            "audit_log": _audit(state, "supervisor", "iteration_limit_reached"),
        }

    proposal = await dependencies.model.generate(
        SupervisorDecision,
        system_prompt=(
            "Sos el Supervisor de un sistema de diagnóstico de Amazon Redshift. "
            "Elegí exactamente un próximo especialista. No declares FINISH si faltan "
            "evidencia, diagnóstico, recomendaciones o validación."
        ),
        payload=_snapshot(state),
    )
    route = _guarded_route(state, proposal.next_agent)
    decision = proposal.model_copy(update={"next_agent": route, "iteration": iteration})
    return {
        "supervisor_decision": decision.model_dump(mode="json"),
        "iteration": iteration,
        "audit_log": _audit(state, "supervisor", f"route:{route.value}"),
    }


async def research_node(
    state: IntelligenceState, dependencies: NodeDependencies
) -> dict[str, Any]:
    decision = SupervisorDecision.model_validate(state["supervisor_decision"])
    expanded = " ".join([state["query"], *decision.missing_information]).strip()
    result = await dependencies.rag.search(RetrievalQuery(text=expanded, top_k=5))
    return {
        "evidence": [item.model_dump(mode="json") for item in result.evidence],
        "validation": None,
        "audit_log": _audit(state, "research", f"evidence:{len(result.evidence)}"),
    }


async def diagnosis_node(
    state: IntelligenceState, dependencies: NodeDependencies
) -> dict[str, Any]:
    report = await dependencies.model.generate(
        DiagnosticReport,
        system_prompt=(
            "Sos un especialista en diagnóstico de Amazon Redshift. Separá hechos de "
            "hipótesis y citá al menos un evidence_id exacto de la evidencia suministrada "
            "en cada hipótesis. Si faltan métricas, pedilas sin inventar IDs."
        ),
        payload=_snapshot(state),
    )
    return {
        "diagnosis": report.model_dump(mode="json"),
        "recommendation_plan": None,
        "validation": None,
        "audit_log": _audit(state, "diagnosis", "report_created"),
    }


async def optimization_node(
    state: IntelligenceState, dependencies: NodeDependencies
) -> dict[str, Any]:
    plan = await dependencies.model.generate(
        RecommendationPlan,
        system_prompt=(
            "Sos un arquitecto de Amazon Redshift. Proponé acciones priorizadas, reversibles "
            "cuando sea posible y respaldadas por al menos un evidence_id exacto de la "
            "evidencia suministrada. Marcá aprobación para todo "
            "cambio de producción, terminación de sesión o acción high/critical."
        ),
        payload=_snapshot(state),
    )
    return {
        "recommendation_plan": plan.model_dump(mode="json"),
        "validation": None,
        "audit_log": _audit(state, "optimization", "plan_created"),
    }


async def validation_node(
    state: IntelligenceState, dependencies: NodeDependencies
) -> dict[str, Any]:
    known_ids = {item["evidence_id"] for item in state.get("evidence", [])}
    diagnosis = DiagnosticReport.model_validate(state.get("diagnosis"))
    plan = RecommendationPlan.model_validate(state.get("recommendation_plan"))
    cited_ids = {
        evidence_id
        for hypothesis in diagnosis.hypotheses
        for evidence_id in hypothesis.evidence_ids
    } | {
        evidence_id
        for recommendation in plan.recommendations
        for evidence_id in recommendation.evidence_ids
    }
    unknown_ids = sorted(cited_ids - known_ids)
    if unknown_ids:
        validation = ValidationResult(
            passed=False,
            reason="El diagnóstico o el plan contienen citas inexistentes.",
            unsupported_claims=unknown_ids,
            next_agent=AgentRoute.DIAGNOSE,
        )
    else:
        validation = await dependencies.model.generate(
            ValidationResult,
            system_prompt=(
                "Sos el validador crítico. Verificá cobertura, coherencia y soporte documental. "
                "Si aprobás, elegí FINISH o HUMAN_APPROVAL. Si rechazás, devolvé RESEARCH, "
                "DIAGNOSE u OPTIMIZE."
            ),
            payload=_snapshot(state),
        )
    return {
        "validation": validation.model_dump(mode="json"),
        "audit_log": _audit(state, "validation", f"passed:{validation.passed}"),
    }


async def approval_node(state: IntelligenceState) -> dict[str, Any]:
    plan = RecommendationPlan.model_validate(state["recommendation_plan"])
    critical = [item.model_dump(mode="json") for item in plan.recommendations if item.requires_approval]
    request = {
        "type": "recommendation_approval",
        "reason": "El plan contiene acciones que requieren revisión humana.",
        "recommendations": critical,
    }
    response = interrupt(request)
    approved = bool(response.get("approved")) if isinstance(response, dict) else bool(response)
    comment = response.get("comment") if isinstance(response, dict) else None
    return {
        "approval_request": request,
        "approval": {"approved": approved, "comment": comment},
        "rejected": not approved,
        "audit_log": _audit(state, "human", "approved" if approved else "rejected"),
    }


async def finish_node(state: IntelligenceState) -> dict[str, Any]:
    if state.get("rejected"):
        answer = "El plan fue rechazado por la revisión humana y no se autoriza su ejecución."
    elif state.get("final_answer"):
        answer = state["final_answer"]
    else:
        diagnosis = DiagnosticReport.model_validate(state["diagnosis"])
        plan = RecommendationPlan.model_validate(state["recommendation_plan"])
        actions = "\n".join(
            f"{item.priority}. {item.action} (riesgo: {item.risk})"
            for item in sorted(plan.recommendations, key=lambda item: item.priority)
        )
        answer = f"{diagnosis.summary}\n\nPlan recomendado:\n{actions}"
    return {
        "final_answer": answer,
        "audit_log": _audit(state, "system", "finished"),
    }
