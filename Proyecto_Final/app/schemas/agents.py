from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class AgentRoute(StrEnum):
    RESEARCH = "RESEARCH"
    DIAGNOSE = "DIAGNOSE"
    OPTIMIZE = "OPTIMIZE"
    VALIDATE = "VALIDATE"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"
    FINISH = "FINISH"


class SupervisorDecision(BaseModel):
    next_agent: AgentRoute
    reason: str = Field(min_length=5, max_length=1000)
    missing_information: list[str] = Field(default_factory=list, max_length=20)
    iteration: int = Field(ge=0, le=12)


class DiagnosticHypothesis(BaseModel):
    hypothesis: str = Field(min_length=5, max_length=2000)
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1)
    missing_evidence: list[str] = Field(default_factory=list)


class DiagnosticReport(BaseModel):
    summary: str = Field(min_length=10, max_length=5000)
    hypotheses: list[DiagnosticHypothesis] = Field(min_length=1, max_length=10)
    requested_metrics: list[str] = Field(default_factory=list, max_length=20)


class Recommendation(BaseModel):
    action: str = Field(min_length=5, max_length=2000)
    rationale: str = Field(min_length=5, max_length=3000)
    priority: int = Field(ge=1, le=10)
    risk: str = Field(pattern="^(low|medium|high|critical)$")
    evidence_ids: list[str] = Field(min_length=1)
    reversible: bool
    requires_approval: bool = False

    @model_validator(mode="after")
    def critical_actions_require_approval(self) -> "Recommendation":
        if self.risk in {"high", "critical"} and not self.requires_approval:
            raise ValueError("High-risk and critical recommendations require approval")
        return self


class RecommendationPlan(BaseModel):
    recommendations: list[Recommendation] = Field(min_length=1, max_length=10)
    overall_rationale: str = Field(min_length=10, max_length=3000)


class ValidationResult(BaseModel):
    passed: bool
    reason: str = Field(min_length=5, max_length=2000)
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    next_agent: AgentRoute

    @model_validator(mode="after")
    def passed_validation_must_finish(self) -> "ValidationResult":
        if self.passed and self.next_agent not in {AgentRoute.FINISH, AgentRoute.HUMAN_APPROVAL}:
            raise ValueError("A passed validation must finish or request approval")
        if not self.passed and self.next_agent in {AgentRoute.FINISH, AgentRoute.HUMAN_APPROVAL}:
            raise ValueError("A failed validation must return to a specialist")
        return self
