import asyncio

from app.schemas import RetrievalQuery, RetrievalResult
from app.observability import traced

from .fusion import reciprocal_rank_fusion
from .interfaces import AsyncRetriever


class HybridRAGService:
    def __init__(
        self,
        dense: AsyncRetriever,
        sparse: AsyncRetriever,
        *,
        top_k_final: int = 5,
    ) -> None:
        self._dense = dense
        self._sparse = sparse
        self._top_k_final = top_k_final

    @traced("rag.hybrid_search", kind="CHAIN")
    async def search(self, query: RetrievalQuery) -> RetrievalResult:
        dense_results, sparse_results = await asyncio.gather(
            self._dense.search(query),
            self._sparse.search(query),
        )
        evidence = reciprocal_rank_fusion(
            [dense_results, sparse_results],
            limit=min(query.top_k, self._top_k_final),
        )
        return RetrievalResult(
            query=query.text,
            evidence=evidence,
            searched_dense=len(dense_results),
            searched_sparse=len(sparse_results),
        )
