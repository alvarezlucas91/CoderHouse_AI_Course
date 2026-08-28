import asyncio

from app.rag.bm25 import BM25Retriever
from app.schemas import Evidence, RetrievalQuery


def evidence(identifier: str, content: str, category: str) -> Evidence:
    return Evidence(
        evidence_id=identifier,
        content=content,
        source=f"{identifier}.md",
        title=identifier,
        category=category,
        fused_score=0,
    )


def test_bm25_ranks_terms_and_applies_category_filter() -> None:
    retriever = BM25Retriever(
        [
            evidence("monitoring", "queue time execution time", "operations"),
            evidence("security", "role audit permissions", "security"),
            evidence("other-sec", "queue permission", "security"),
        ]
    )

    result = asyncio.run(
        retriever.search(RetrievalQuery(text="queue time", categories=["operations"], top_k=5))
    )

    assert [item.evidence_id for item in result] == ["monitoring"]
    assert result[0].sparse_score is not None
