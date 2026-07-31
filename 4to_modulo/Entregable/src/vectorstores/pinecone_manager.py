from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore

from src.config import (
    INDEX_NAME,
    NAMESPACE,
)

from src.embeddings import EmbeddingService


class PineconeManager:
    """
    Manages interactions with the Pinecone vector store.
    """

    def __init__(self):

        embeddings = EmbeddingService.get_embeddings()

        self.vectorstore = PineconeVectorStore(
            index_name=INDEX_NAME,
            embedding=embeddings,
            namespace=NAMESPACE,
        )

    def add_documents(
        self,
        documents: list[Document],
        ids: list[str] | None = None,
    ) -> None:

        if not documents:
            print("No documents to insert.")
            return

        self.vectorstore.add_documents(
            documents=documents,
            ids=ids,
        )

        print(f"Inserted {len(documents)} document(s).")

    def similarity_search(
        self,
        query: str,
        k: int = 5,
    ) -> list[Document]:
        """
        Performs a vector similarity search.
        """

        return self.vectorstore.similarity_search(
            query=query,
            k=k,
        )

    def as_retriever(
        self,
        k: int = 5,
    ):
        """
        Returns the LangChain retriever.
        """

        return self.vectorstore.as_retriever(
            search_kwargs={
                "k": k
            }
        )