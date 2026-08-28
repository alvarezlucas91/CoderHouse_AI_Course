import asyncio

from app.rag import HybridRAGService, reciprocal_rank_fusion
from app.schemas import Evidence, RetrievalQuery


def evidence(identifier: str, source: str) -> Evidence:
    return Evidence(
        evidence_id=identifier,
        content=f"Evidence {identifier}",
        source=source,
        title=source,
        fused_score=0,
    )


class FakeRetriever:
    def __init__(self, results: list[Evidence]) -> None:
        self.results = results
        self.called = False

    async def search(self, query: RetrievalQuery) -> list[Evidence]:
        await asyncio.sleep(0)
        self.called = True
        return self.results


def test_rrf_deduplicates_and_rewards_consensus() -> None:
    shared = evidence("shared-id", "shared.md")
    fused = reciprocal_rank_fusion(
        [[shared, evidence("dense-id", "dense.md")], [shared, evidence("sparse-id", "sparse.md")]],
        limit=3,
    )

    assert [item.evidence_id for item in fused] == ["shared-id", "dense-id", "sparse-id"]
    assert fused[0].fused_score > fused[1].fused_score


def test_hybrid_search_runs_both_retrievers() -> None:
    dense = FakeRetriever([evidence("dense-id", "dense.md")])
    sparse = FakeRetriever([evidence("sparse-id", "sparse.md")])
    service = HybridRAGService(dense, sparse, top_k_final=2)

    result = asyncio.run(
        service.search(RetrievalQuery(text="Diagnose query spill", top_k=2))
    )

    assert dense.called and sparse.called
    assert len(result.evidence) == 2
    assert result.searched_dense == 1
    assert result.searched_sparse == 1
