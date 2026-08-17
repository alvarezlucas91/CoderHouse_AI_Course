import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_imports_and_graph_build():
    from graph import build_graph

    graph = build_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")


def test_state_payload_validation():
    from schemas import MultiAgentStateModel

    payload = {
        "messages": [],
        "query": "¿Qué dice la documentación sobre Amazon Redshift?",
        "research_data": [{"content": "contenido", "metadata": {"source": "doc1"}, "distance": 0.1}],
        "analysis_results": {"valid": True, "sentiment": "neutral", "document_count": 1},
        "next_agent": "SUPERVISOR",
        "task_completed": False,
        "step_count": 0,
        "contributions": {"research": ["resumen"], "analysis": ["análisis"], "validation": []},
        "validation_status": "PENDING",
    }

    model = MultiAgentStateModel.model_validate(payload)
    assert model.query == payload["query"]
    assert model.next_agent == "SUPERVISOR"
    assert model.validation_status == "PENDING"

    with pytest.raises(ValueError):
        MultiAgentStateModel.model_validate({**payload, "next_agent": "INVALID_ROUTE"})


def test_agent_output_validation():
    from schemas import AnalysisResultModel, ResearchDocument

    doc = ResearchDocument.model_validate({
        "content": "contenido técnico",
        "metadata": {"source": "doc1"},
        "distance": 0.12,
    })
    assert doc.metadata["source"] == "doc1"

    result = AnalysisResultModel.model_validate({
        "sentiment": "positivo",
        "summary": "Resumen correcto",
        "valid": True,
        "document_count": 1,
        "sources": ["doc1"],
    })
    assert result.valid is True

    with pytest.raises(ValueError):
        AnalysisResultModel.model_validate({
            "sentiment": "positivo",
            "summary": "",
            "valid": "si",
            "document_count": -1,
            "sources": ["doc1"],
        })
