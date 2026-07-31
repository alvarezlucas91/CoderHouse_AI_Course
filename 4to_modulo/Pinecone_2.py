import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any


# Mock del índice de Pinecone para testing.
# Simula únicamente los métodos que utilizaría el pipeline
# sin necesidad de conectarse a un servicio real.
class MockPineconeIndex:

    async def upsert(self, vectors: List[Dict]):
        # Simula la inserción de un lote de vectores.
        # Devuelve cuántos registros fueron "almacenados".
        return {"upserted_count": len(vectors)}

    async def query(
        self,
        vector: List[float],
        top_k: int,
        filter: Dict = None
    ):
        # Simula una búsqueda semántica mostrando
        # el filtro recibido.
        print(f"Query filter: {filter}")

        return {"matches": []}


class IngestionPipeline:

    def __init__(self, index: MockPineconeIndex):
        # El pipeline recibe una instancia del índice
        # para desacoplar la lógica de negocio de Pinecone.
        self.index = index

    def create_metadata(
        self,
        doc_text: str,
        category: str,
        author: str
    ) -> Dict[str, Any]:
        """
        Genera los metadatos que acompañarán a cada vector.
        Estos metadatos luego podrán utilizarse para realizar
        búsquedas filtradas.
        """

        return {
            "category": category,
            "author": author,
            "ingested_at": datetime.now().isoformat(),
            "text_size": len(doc_text)
        }

    async def process_and_upsert_batches(
        self,
        documents: List[Dict],
        batch_size: int = 100
    ):
        """
        Procesa una lista de documentos dividiéndola en batches.
        Cada documento se transforma en un vector con sus metadatos
        y luego se inserta en el índice.
        """

        results = []

        # Recorremos los documentos de a "batch_size" elementos.
        for i in range(0, len(documents), batch_size):

            batch = documents[i:i + batch_size]

            # Lista que contendrá los vectores de este batch.
            vectors = []

            for document in batch:

                # Extraemos la información del documento.
                doc_text = document["text"]
                category = document["category"]
                author = document["author"]

                # Construimos los metadatos asociados.
                metadata = self.create_metadata(
                    doc_text,
                    category,
                    author
                )

                # Simulamos un embedding y generamos
                # un identificador único para el vector.
                vector = {
                    "id": str(uuid.uuid4()),
                    "values": [0.0, 0.0, 0.0],
                    "metadata": metadata
                }

                vectors.append(vector)

            # Insertamos el batch completo en el índice.
            result = await self.index.upsert(vectors)

            # Guardamos el resultado de la operación.
            results.append(result)

        return results

    async def search_by_category(
        self,
        query_vector: List[float],
        category: str
    ):
        """
        Realiza una búsqueda semántica aplicando un filtro
        para recuperar únicamente documentos de una categoría.
        """

        # Construimos el filtro utilizando la sintaxis
        # habitual de Pinecone.
        filter = {
            "category": {
                "$eq": category
            }
        }

        # Ejecutamos la consulta sobre el índice.
        return await self.index.query(
            vector=query_vector,
            top_k=10,
            filter=filter
        )


async def main():

    # Creamos un índice simulado y el pipeline de ingesta.
    index = MockPineconeIndex()
    pipeline = IngestionPipeline(index)

    # Documentos de ejemplo que serán procesados.
    docs = [
        {
            "text": "Contenido A",
            "category": "legal",
            "author": "User1"
        },
        {
            "text": "Contenido B",
            "category": "hr",
            "author": "User2"
        }
    ]

    # ===============================
    # 1. INGESTA
    # ===============================
    # Cada documento se transforma en un vector con metadatos
    # y se inserta en el índice en batches de tamaño 1.
    results = await pipeline.process_and_upsert_batches(
        docs,
        batch_size=1
    )

    print("Upsert results:")
    print(results)

    # ===============================
    # 2. BÚSQUEDA
    # ===============================
    # Se simula una consulta vectorial restringiendo
    # los resultados únicamente a la categoría "legal".
    results = await pipeline.search_by_category(
        query_vector=[0.1, 0.2, 0.3],
        category="legal"
    )

    print("Search results:")
    print(results)


if __name__ == "__main__":
    # Inicia el event loop y ejecuta el flujo completo:
    # creación del índice, ingesta y búsqueda.
    asyncio.run(main())