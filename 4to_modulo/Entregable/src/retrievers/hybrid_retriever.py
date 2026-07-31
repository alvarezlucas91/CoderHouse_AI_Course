from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever

from src.config import (
    DOCUMENTS_DIR,
    TOP_K,
)

from src.loaders import DocumentLoader
from src.processing import TextSplitter
from src.vectorstores import PineconeManager


class HybridRetriever:
    """
    Creates an EnsembleRetriever combining vector and lexical search.
    """

    def __init__(self):

        # Vector Retriever
        self.vector_retriever = (
            PineconeManager()
            .as_retriever(k=TOP_K)
        )

        # BM25 Retriever
        loader = DocumentLoader(DOCUMENTS_DIR)

        documents = loader.load()

        splitter = TextSplitter()

        chunks = splitter.split_documents(documents)

        self.bm25_retriever = BM25Retriever.from_documents(
            chunks
        )

        self.bm25_retriever.k = TOP_K

        # Ensemble Retriever
        self.ensemble = EnsembleRetriever(
            retrievers=[
                self.vector_retriever,
                self.bm25_retriever,
            ],
            weights=[0.5, 0.5],
        )

    def get_retriever(self):
        """
        Returns the configured EnsembleRetriever.
        """

        return self.ensemble