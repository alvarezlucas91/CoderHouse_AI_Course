from langchain_openai import OpenAIEmbeddings

from src.config import (
    validate_config,
    OPENAI_API_KEY,
    EMBEDDING_MODEL,
)

validate_config()


class EmbeddingService:

    @staticmethod
    def get_embeddings() -> OpenAIEmbeddings:

        return OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            api_key=OPENAI_API_KEY,
        )