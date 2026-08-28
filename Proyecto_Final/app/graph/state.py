from typing import Any, TypedDict


class IntelligenceState(TypedDict, total=False):
    query: str
    context: dict[str, str | int | float | bool]
    evidence: list[dict[str, Any]]
    diagnosis: dict[str, Any] | None
    recommendation_plan: dict[str, Any] | None
    validation: dict[str, Any] | None
    supervisor_decision: dict[str, Any] | None
    approval_request: dict[str, Any] | None
    approval: dict[str, Any] | None
    final_answer: str | None
    rejected: bool
    iteration: int
    max_iterations: int
    audit_log: list[dict[str, Any]]

