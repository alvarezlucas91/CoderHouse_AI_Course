import os
import asyncio
from pinecone import Pinecone, ServerlessSpec

# Asegúrate de tener tu PINECONE_API_KEY en las variables de entorno
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY no está configurada")


async def setup_vector_infrastructure(index_name: str, dimension: int):
    """
    Configura la infraestructura de Pinecone Serverless y realiza una carga inicial.
    """

    # 1. Inicializar el cliente de Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # 2. Crear el índice si no existe
    indexes = await asyncio.to_thread(
        pc.list_indexes
    )

    if index_name not in indexes.names():
        await asyncio.to_thread(
            pc.create_index,
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )

    # 3. Conectar al índice
    index = pc.Index(index_name)

    # 4. Implementar un Upsert de prueba usando un Namespace
    vectors = [
        (
            "vector-1",
            [0.1] * dimension,
            {"text": "Primer vector de prueba"}
        ),
        (
            "vector-2",
            [0.2] * dimension,
            {"text": "Segundo vector de prueba"}
        )
    ]

    await asyncio.to_thread(
        index.upsert,
        vectors=vectors,
        namespace="test-namespace"
    )

    # 5. Retornar las estadísticas del índice
    stats = await asyncio.to_thread(
        index.describe_index_stats
    )

    return stats


if __name__ == "__main__":
    stats = asyncio.run(
        setup_vector_infrastructure(
            "mi-indice-serverless",
            1536
        )
    )

    print(stats)