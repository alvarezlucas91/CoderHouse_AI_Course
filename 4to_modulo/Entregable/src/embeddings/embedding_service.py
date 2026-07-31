from langchain_huggingface import HuggingFaceEmbeddings

from src.config import EMBEDDING_MODEL


class EmbeddingService:
    """
    Creates the embedding model used throughout the application.
    """

    @staticmethod
    def get_embeddings() -> HuggingFaceEmbeddings:
        return HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
        )