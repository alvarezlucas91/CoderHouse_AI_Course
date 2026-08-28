import asyncio
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graph import GraphDependencies, build_graph
from app.rag import HybridRAGService
from app.schemas import (
    AgentRoute,
    DiagnosticHypothesis,
    DiagnosticReport,
    Evidence,
    Recommendation,
    RecommendationPlan,
    RetrievalQuery,
    SupervisorDecision,
    ValidationResult,
)


class StaticRetriever:
    async def search(self, query: RetrievalQuery) -> list[Evidence]:
        return [
            Evidence(
                evidence_id="evidence-123",
                content="High queue time indicates workload contention.",
                source="monitoring.md",
                title="Monitoring",
                category="monitoring",
                fused_score=0,
            )
        ]


class FakeStructuredModel:
    def __init__(self, *, high_risk: bool = False) -> None:
        self.high_risk = high_risk

    async def generate(
        self,
        schema: type[Any],
        *,
        system_prompt: str,
        payload: str,
    ) -> Any:
        if schema is SupervisorDecision:
            return SupervisorDecision(
                next_agent=AgentRoute.FINISH,
                reason="All available information has been inspected.",
                iteration=0,
            )
        if schema is DiagnosticReport:
            return DiagnosticReport(
                summary="The workload is spending excessive time in its queue.",
                hypotheses=[
                    DiagnosticHypothesis(
                        hypothesis="WLM contention is delaying execution.",
                        confidence=0.8,
                        evidence_ids=["evidence-123"],
                    )
                ],
            )
        if schema is RecommendationPlan:
            return RecommendationPlan(
                overall_rationale="Measure queue saturation before changing capacity.",
                recommendations=[
                    Recommendation(
                        action=(
                            "Change the production WLM configuration."
                            if self.high_risk
                            else "Review WLM queue assignments and priorities."
                        ),
                        rationale="Queue time dominates the observed latency.",
                        priority=1,
                        risk="high" if self.high_risk else "low",
                        evidence_ids=["evidence-123"],
                        reversible=True,
                        requires_approval=self.high_risk,
                    )
                ],
            )
        if schema is ValidationResult:
            return ValidationResult(
                passed=True,
                reason="Every diagnosis and recommendation has supporting evidence.",
                next_agent=AgentRoute.FINISH,
            )
        raise AssertionError(f"Unexpected schema: {schema}")


def test_graph_executes_guarded_multi_agent_flow() -> None:
    retriever = StaticRetriever()
    rag = HybridRAGService(retriever, retriever, top_k_final=5)
    graph = build_graph(GraphDependencies(model=FakeStructuredModel(), rag=rag))

    result = asyncio.run(
        graph.ainvoke(
            {
                "query": "Why are Redshift queries waiting?",
                "context": {},
                "evidence": [],
                "diagnosis": None,
                "recommendation_plan": None,
                "validation": None,
                "iteration": 0,
                "max_iterations": 8,
                "audit_log": [],
                "rejected": False,
            }
        )
    )

    assert result["validation"]["passed"] is True
    assert "Plan recomendado" in result["final_answer"]
    assert [entry["agent"] for entry in result["audit_log"]] == [
        "supervisor",
        "research",
        "supervisor",
        "diagnosis",
        "supervisor",
        "optimization",
        "supervisor",
        "validation",
        "supervisor",
        "system",
    ]


def test_high_risk_plan_interrupts_and_resumes_same_thread() -> None:
    retriever = StaticRetriever()
    rag = HybridRAGService(retriever, retriever, top_k_final=5)
    graph = build_graph(
        GraphDependencies(model=FakeStructuredModel(high_risk=True), rag=rag),
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "approval-thread"}}
    initial = {
        "query": "Change production WLM to reduce queue time",
        "context": {},
        "evidence": [],
        "diagnosis": None,
        "recommendation_plan": None,
        "validation": None,
        "iteration": 0,
        "max_iterations": 8,
        "audit_log": [],
        "rejected": False,
    }

    paused = asyncio.run(graph.ainvoke(initial, config=config))

    assert paused["__interrupt__"]
    resumed = asyncio.run(
        graph.ainvoke(Command(resume={"approved": True, "comment": "Reviewed"}), config=config)
    )
    assert resumed["approval"] == {"approved": True, "comment": "Reviewed"}
    assert resumed["rejected"] is False
    assert "Plan recomendado" in resumed["final_answer"]
