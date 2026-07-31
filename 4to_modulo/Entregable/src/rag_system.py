from langchain_core.documents import Document

from src.retrievers import HybridRetriever


class RAGSystem:
    """
    High-level interface for retrieving documents using a hybrid retriever.
    """

    def __init__(self):

        self.retriever = (
            HybridRetriever()
            .get_retriever()
        )

    def search(
        self,
        query: str,
    ) -> list[Document]:
        """
        Retrieves the most relevant documents for a query.
        """

        if not query.strip():
            raise ValueError("Query cannot be empty.")

        return self.retriever.invoke(query)