import uuid

from src.config import DOCUMENTS_DIR

from src.loaders import DocumentLoader
from src.processing import TextSplitter
from src.vectorstores import PineconeManager


def ingest_documents() -> None:
    """
    Executes the ingestion pipeline.
    """

    print("Loading documents...")

    loader = DocumentLoader(DOCUMENTS_DIR)
    
    documents = loader.load()

    if not documents:
        print("No documents found. Exiting ingestion.")
        return

    print("Splitting documents...")

    splitter = TextSplitter()
    chunks = splitter.split_documents(documents)

    ids = [
        str(uuid.uuid4())
        for _ in chunks
    ]

    for doc_id, chunk in zip(ids, chunks):
        chunk.metadata.setdefault("document_id", doc_id)
        chunk.metadata.setdefault("text", chunk.page_content)

    print("Uploading documents to Pinecone...")

    pinecone = PineconeManager()

    pinecone.add_documents(
        documents=chunks,
        ids=ids,
    )

    print("Ingestion completed successfully.")


if __name__ == "__main__":
    ingest_documents()