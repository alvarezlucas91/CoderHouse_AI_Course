from __future__ import annotations

from app.hitl import HIGH_COST_USD, assess_risk, human_approval, route_after_approval


async def test_risk_by_explicit_flag():
    result = await assess_risk({"query": "analizar datos", "critical": True})
    assert result["critical"] is True
    assert "marcada crítica por el cliente" in result["risk_reasons"]


async def test_risk_by_cost_and_term():
    result = await assess_risk({
        "query": "Publicar cambios en producción",
        "critical": False,
        "estimated_cost_usd": HIGH_COST_USD,
    })
    assert result["critical"] is True
    assert len(result["risk_reasons"]) >= 2


def test_non_critical_does_not_interrupt():
    result = human_approval({"query": "consulta", "critical": False})
    assert result["approved"] is True
    assert route_after_approval(result) == "RESEARCH"


def test_rejected_routes_to_reject():
    assert route_after_approval({"approved": False}) == "REJECT"
