import asyncio
from collections.abc import Sequence
from re import findall

from rank_bm25 import BM25Okapi

from app.schemas import Evidence, RetrievalQuery
from app.observability import traced


def tokenize(text: str) -> list[str]:
    return findall(r"[a-záéíóúüñ0-9_]+", text.lower())


class BM25Retriever:
    def __init__(self, corpus: Sequence[Evidence], *, candidate_limit: int = 8) -> None:
        if not corpus:
            raise ValueError("BM25 corpus cannot be empty")
        self._corpus = list(corpus)
        self._candidate_limit = candidate_limit
        self._index = BM25Okapi([tokenize(item.content) for item in self._corpus])

    @traced("retriever.bm25", kind="RETRIEVER")
    async def search(self, query: RetrievalQuery) -> list[Evidence]:
        return await asyncio.to_thread(self._search_sync, query)

    def _search_sync(self, query: RetrievalQuery) -> list[Evidence]:
        scores = self._index.get_scores(tokenize(query.text))
        allowed = set(query.categories)
        ranked = sorted(
            (
                (index, float(score))
                for index, score in enumerate(scores)
                if score > 0 and (not allowed or self._corpus[index].category in allowed)
            ),
            key=lambda pair: (-pair[1], self._corpus[pair[0]].evidence_id),
        )[: self._candidate_limit]
        return [
            self._corpus[index].model_copy(update={"sparse_score": score})
            for index, score in ranked
        ]
