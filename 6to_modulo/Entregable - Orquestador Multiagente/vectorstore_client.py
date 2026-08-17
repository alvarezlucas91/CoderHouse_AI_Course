from __future__ import annotations

import os
from typing import Any

from chromadb import PersistentClient


class ChromaKnowledgeClient:
    """Cliente sencillo para consultar el vectorstore persistido del módulo 3."""

    def __init__(self, persist_directory: str | None = None):
        self.persist_directory = persist_directory or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "3er_modulo",
            "Entregable",
            "vectorstore",
        )
        self.client = PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(name="technical_documents")

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Recupera los documentos más relevantes para una consulta."""
        try:
            results = self.collection.query(query_texts=[query], n_results=k, include=["documents", "metadatas", "distances"])
            docs = []
            for doc, meta, distance in zip(results.get("documents", [[]])[0], results.get("metadatas", [[]])[0], results.get("distances", [[]])[0]):
                docs.append({
                    "content": doc,
                    "metadata": meta or {},
                    "distance": distance,
                })
            return docs
        except Exception as exc:
            return [{"content": f"Error al consultar el vectorstore: {exc}", "metadata": {}, "distance": 1.0}]

    def summarize(self, docs: list[dict[str, Any]]) -> str:
        """Construye un resumen compacto con citas serializadas."""
        if not docs:
            return "No se encontraron documentos relevantes."

        blocks = []
        for idx, doc in enumerate(docs, 1):
            source = doc.get("metadata", {}).get("source", f"documento_{idx}")
            text = (doc.get("content") or "").strip()
            blocks.append(f"[{idx}] {source}\n{text[:600]}...")
        return "\n\n".join(blocks)
