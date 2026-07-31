from pathlib import Path
from dotenv import load_dotenv
import os
from langchain_huggingface import HuggingFaceEmbeddings


# Carga las variables de entorno
load_dotenv()

# ==========================
# API Keys
# ==========================

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "llama-3.3-70b-versatile"
)

# ==========================
# Pinecone
# ==========================

INDEX_NAME = os.getenv("INDEX_NAME", "technical-documents")
NAMESPACE = os.getenv("NAMESPACE", "default")

# ==========================
# Embeddings 
# ==========================

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "BAAI/bge-small-en-v1.5",
)

embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL
)

EMBEDDING_DIMENSION = 384

# ==========================
# Chunking
# ==========================

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# ==========================
# Paths
# ==========================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

DOCUMENTS_DIR = DATA_DIR / "documents"

EVALUATION_DATASET = DATA_DIR / "evaluation_dataset.json"

# ==========================
# Retrieval
# ==========================

TOP_K = 5

def validate_config() -> None:
    """Verifica que las variables de entorno obligatorias estén definidas."""

    required = {
        "PINECONE_API_KEY": PINECONE_API_KEY,
        "GROQ_API_KEY": GROQ_API_KEY
    }

    missing = [key for key, value in required.items() if not value]

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )