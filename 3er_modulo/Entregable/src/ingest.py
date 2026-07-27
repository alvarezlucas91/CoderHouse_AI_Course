from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings



# =====================================================
# Cargar variables de entorno
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


DATA_DIR = BASE_DIR / "data"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
COLLECTION_NAME = "technical_documents"


def ingest_documents() -> None:
    """
    Reads .txt and .md files from the data directory,
    splits them into chunks and persists them in ChromaDB.
    """


    # Embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # Vector Store
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=VECTORSTORE_DIR,
        embedding_function=embeddings,
    )

    # Evitar reindexar si ya existe información
    existing_documents = vectorstore.get()

    if existing_documents["ids"]:
        print(
            "Vectorstore already populated. "
            "Skipping ingestion."
        )
        return

    documents = []

    files = [
        *DATA_DIR.glob("*.md"),
        *DATA_DIR.glob("*.txt"),
    ]

    if not files:
        raise FileNotFoundError(
            f"No .md or .txt files found in {DATA_DIR}"
        )

    # Leer documentos
    for file_path in files:

        content = file_path.read_text(
            encoding="utf-8"
        )

        documents.append(
            {
                "content": content,
                "metadata": {
                    "source": file_path.name,
                    "file_type": file_path.suffix,
                },
            }
        )

    # Chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=250,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            "",
        ],
    )

    chunks = []

    for document in documents:

        split_chunks = text_splitter.split_text(
            document["content"]
        )

        for index, chunk in enumerate(split_chunks):

            chunks.append(
                {
                    "page_content": chunk,
                    "metadata": {
                        **document["metadata"],
                        "chunk_index": index,
                    },
                }
            )

    # Persistir en ChromaDB
    vectorstore.add_texts(
        texts=[
            chunk["page_content"]
            for chunk in chunks
        ],
        metadatas=[
            chunk["metadata"]
            for chunk in chunks
        ],
    )

    print(
        f"Ingestion completed. "
        f"Persisted {len(chunks)} chunks."
    )


if __name__ == "__main__":
    ingest_documents()