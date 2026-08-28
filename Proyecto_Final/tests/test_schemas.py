import pytest
from pydantic import ValidationError

from app.schemas import AgentRoute, Recommendation, ValidationResult


def test_high_risk_recommendation_requires_approval() -> None:
    with pytest.raises(ValidationError):
        Recommendation(
            action="Terminate the blocking session",
            rationale="It owns the lock required by the critical workload",
            priority=1,
            risk="high",
            evidence_ids=["evidence-123"],
            reversible=False,
            requires_approval=False,
        )


def test_failed_validation_cannot_finish() -> None:
    with pytest.raises(ValidationError):
        ValidationResult(
            passed=False,
            reason="The diagnosis has no supporting evidence",
            next_agent=AgentRoute.FINISH,
        )

