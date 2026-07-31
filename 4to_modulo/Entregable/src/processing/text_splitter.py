from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)


class TextSplitter:
    """
    Splits LangChain documents into smaller chunks while preserving context.
    """

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ):

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True,
        )

    def split_documents(
        self,
        documents: list[Document],
    ) -> list[Document]:

        if not documents:
            print("No documents to split.")
            return []

        chunks = self.text_splitter.split_documents(documents)

        print(f"Generated {len(chunks)} chunk(s).")

        return chunks