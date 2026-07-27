from pathlib import Path
from typing import Iterable

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentIngestion:
    """
    Módulo responsable de:

    1. Leer documentos .txt y .md.
    2. Fragmentarlos en chunks.
    3. Persistirlos en una colección de ChromaDB.
    """

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "technical_documents",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:

        self.client = chromadb.PersistentClient(
            path=persist_directory
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",
                "\n",
                ". ",
                " ",
                ""
            ],
        )