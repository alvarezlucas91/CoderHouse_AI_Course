from typing import Any

from pydantic import BaseModel, Field, HttpUrl, model_validator


class RetrievalQuery(BaseModel):
    text: str = Field(min_length=3, max_length=4000)
    categories: list[str] = Field(default_factory=list, max_length=10)
    top_k: int = Field(default=5, ge=1, le=20)


class Evidence(BaseModel):
    evidence_id: str = Field(min_length=8, max_length=128)
    content: str = Field(min_length=1, max_length=8000)
    source: str = Field(min_length=1, max_length=500)
    title: str = Field(min_length=1, max_length=500)
    category: str = Field(default="unknown", max_length=100)
    section: str | None = Field(default=None, max_length=300)
    source_url: HttpUrl | None = None
    dense_score: float | None = None
    sparse_score: float | None = None
    fused_score: float = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    query: str
    evidence: list[Evidence]
    searched_dense: int = Field(ge=0)
    searched_sparse: int = Field(ge=0)

    @model_validator(mode="after")
    def ensure_unique_evidence(self) -> "RetrievalResult":
        identifiers = [item.evidence_id for item in self.evidence]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("RetrievalResult contains duplicate evidence IDs")
        return self

