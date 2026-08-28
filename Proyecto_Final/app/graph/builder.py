from dataclasses import dataclass
from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents import StructuredModel
from app.rag import HybridRAGService
from app.schemas import AgentRoute, SupervisorDecision
from app.observability import traced

from .nodes import (
    NodeDependencies,
    approval_node,
    diagnosis_node,
    finish_node,
    optimization_node,
    research_node,
    supervisor_node,
    validation_node,
)
from .state import IntelligenceState


@dataclass(frozen=True)
class GraphDependencies:
    model: StructuredModel
    rag: HybridRAGService


def _route_after_supervisor(state: IntelligenceState) -> str:
    decision = SupervisorDecision.model_validate(state["supervisor_decision"])
    return decision.next_agent.value


def _route_after_approval(state: IntelligenceState) -> str:
    return "REJECTED" if state.get("rejected") else "APPROVED"


def build_graph(dependencies: GraphDependencies, checkpointer: Any = None):
    node_dependencies = NodeDependencies(model=dependencies.model, rag=dependencies.rag)
    graph = StateGraph(IntelligenceState)
    graph.add_node("SUPERVISOR", traced("agent.supervisor", kind="AGENT")(partial(supervisor_node, dependencies=node_dependencies)))
    graph.add_node("RESEARCH", traced("agent.research", kind="AGENT")(partial(research_node, dependencies=node_dependencies)))
    graph.add_node("DIAGNOSE", traced("agent.diagnosis", kind="AGENT")(partial(diagnosis_node, dependencies=node_dependencies)))
    graph.add_node("OPTIMIZE", traced("agent.optimization", kind="AGENT")(partial(optimization_node, dependencies=node_dependencies)))
    graph.add_node("VALIDATE", traced("agent.validation", kind="AGENT")(partial(validation_node, dependencies=node_dependencies)))
    graph.add_node("HUMAN_APPROVAL", traced("human.approval", kind="AGENT")(approval_node))
    graph.add_node("FINISH", traced("agent.finish", kind="AGENT")(finish_node))

    graph.add_edge(START, "SUPERVISOR")
    graph.add_conditional_edges(
        "SUPERVISOR",
        _route_after_supervisor,
        {
            AgentRoute.RESEARCH.value: "RESEARCH",
            AgentRoute.DIAGNOSE.value: "DIAGNOSE",
            AgentRoute.OPTIMIZE.value: "OPTIMIZE",
            AgentRoute.VALIDATE.value: "VALIDATE",
            AgentRoute.HUMAN_APPROVAL.value: "HUMAN_APPROVAL",
            AgentRoute.FINISH.value: "FINISH",
        },
    )
    for specialist in ("RESEARCH", "DIAGNOSE", "OPTIMIZE", "VALIDATE"):
        graph.add_edge(specialist, "SUPERVISOR")
    graph.add_conditional_edges(
        "HUMAN_APPROVAL",
        _route_after_approval,
        {"APPROVED": "FINISH", "REJECTED": "FINISH"},
    )
    graph.add_edge("FINISH", END)
    return graph.compile(checkpointer=checkpointer)
