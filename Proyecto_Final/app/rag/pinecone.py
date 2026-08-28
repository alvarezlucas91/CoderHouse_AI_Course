from collections.abc import Sequence
from typing import Any, Protocol

from pinecone import PineconeAsyncio

from app.schemas import Evidence, RetrievalQuery
from app.observability import traced


class AsyncEmbeddingProvider(Protocol):
    async def aembed_query(self, text: str) -> Sequence[float]: ...


class PineconeDenseRetriever:
    """Native asyncio Pinecone adapter; no blocking SDK calls are used."""

    def __init__(
        self,
        *,
        api_key: str,
        index_name: str,
        namespace: str,
        embeddings: AsyncEmbeddingProvider,
        candidate_limit: int = 8,
    ) -> None:
        self._api_key = api_key
        self._index_name = index_name
        self._namespace = namespace
        self._embeddings = embeddings
        self._candidate_limit = candidate_limit

    @traced("retriever.pinecone", kind="RETRIEVER")
    async def search(self, query: RetrievalQuery) -> list[Evidence]:
        vector = list(await self._embeddings.aembed_query(query.text))
        metadata_filter: dict[str, Any] | None = None
        if query.categories:
            metadata_filter = {"category": {"$in": query.categories}}

        async with PineconeAsyncio(api_key=self._api_key) as client:
            description = await client.describe_index(self._index_name)
            async with client.IndexAsyncio(host=description.host) as index:
                response = await index.query(
                    namespace=self._namespace,
                    vector=vector,
                    top_k=self._candidate_limit,
                    include_metadata=True,
                    include_values=False,
                    filter=metadata_filter,
                )

        results: list[Evidence] = []
        for match in response.matches:
            metadata = dict(match.metadata or {})
            content = str(metadata.pop("text", "")).strip()
            if not content:
                continue
            source_url = metadata.get("source_url") or None
            results.append(
                Evidence(
                    evidence_id=str(match.id),
                    content=content,
                    source=str(metadata.get("source", "unknown")),
                    title=str(metadata.get("title") or metadata.get("source") or "Unknown"),
                    category=str(metadata.get("category", "unknown")),
                    section=metadata.get("section"),
                    source_url=source_url,
                    dense_score=float(match.score),
                    fused_score=0,
                    metadata=metadata,
                )
            )
        return results
