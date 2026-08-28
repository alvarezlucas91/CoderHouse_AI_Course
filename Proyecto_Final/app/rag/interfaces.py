from typing import Protocol

from app.schemas import Evidence, RetrievalQuery


class AsyncRetriever(Protocol):
    async def search(self, query: RetrievalQuery) -> list[Evidence]: ...

