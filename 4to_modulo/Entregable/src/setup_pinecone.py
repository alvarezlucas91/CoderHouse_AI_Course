from pinecone import Pinecone, ServerlessSpec
import time
import os

from src.config import (
    validate_config,
    PINECONE_API_KEY,
    INDEX_NAME,
    EMBEDDING_DIMENSION,
)

PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

validate_config()


def get_pinecone_client() -> Pinecone:
    """
    Returns an authenticated Pinecone client.
    """
    return Pinecone(api_key=PINECONE_API_KEY)


def create_index() -> None:
    """
    Creates the Pinecone index if it does not already exist.
    """

    pc = get_pinecone_client()

    existing_indexes = pc.list_indexes().names()

    if INDEX_NAME in existing_indexes:
        print(f"Index '{INDEX_NAME}' already exists.")
        return

    print(f"Creating index '{INDEX_NAME}'...")

    pc.create_index(
        name=INDEX_NAME,
        dimension=EMBEDDING_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(
            cloud=PINECONE_CLOUD,
            region=PINECONE_REGION,
        ),
    )

    while not pc.describe_index(INDEX_NAME).status["ready"]:
        print("Waiting for index to become ready...")
        time.sleep(2)

    print("Index created successfully.")


if __name__ == "__main__":
    create_index()