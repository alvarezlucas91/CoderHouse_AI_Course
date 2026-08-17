from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.analyst_agent import analyze_research_data
from agents.research_agent import run_research_agent
from schemas import validate_state_payload
from state import MultiAgentState
from supervisor import supervisor_node, validation_node


def build_graph():
    """Construye el grafo jerárquico con supervisor, investigación, análisis y validación."""
    workflow = StateGraph(MultiAgentState)

    def validate_state(state):
        validated = validate_state_payload(state)
        return validated.model_dump()

    workflow.add_node("VALIDATE_STATE", validate_state)
    workflow.add_node("SUPERVISOR", supervisor_node)
    workflow.add_node("RESEARCH", run_research_agent)
    workflow.add_node("ANALYZE", analyze_research_data)
    workflow.add_node("VALIDATE", validation_node)

    workflow.add_edge(START, "VALIDATE_STATE")
    workflow.add_edge("VALIDATE_STATE", "SUPERVISOR")

    workflow.add_conditional_edges(
        "SUPERVISOR",
        lambda state: state["next_agent"],
        {
            "RESEARCH": "RESEARCH",
            "ANALYZE": "ANALYZE",
            "VALIDATE": "VALIDATE",
            "END": END,
        },
    )

    workflow.add_edge("RESEARCH", "SUPERVISOR")
    workflow.add_edge("ANALYZE", "VALIDATE")
    workflow.add_conditional_edges(
        "VALIDATE",
        lambda state: state["next_agent"],
        {
            "ANALYZE": "ANALYZE",
            "END": END,
            "SUPERVISOR": "SUPERVISOR",
        },
    )

    return workflow.compile()


if __name__ == "__main__":
    app = build_graph()
    result = app.invoke({
        "messages": [],
        "query": "¿Qué dice la documentación sobre Amazon Redshift y su arquitectura?",
        "research_data": [],
        "analysis_results": {},
        "next_agent": "SUPERVISOR",
        "task_completed": False,
        "step_count": 0,
        "contributions": {"research": [], "analysis": [], "validation": []},
        "validation_status": "PENDING",
    })
    print(result)
