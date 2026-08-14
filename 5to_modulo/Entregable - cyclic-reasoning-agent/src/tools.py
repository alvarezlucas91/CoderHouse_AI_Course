import json
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.config import KNOWLEDGE_BASE_PATH


class SearchKnowledgeInput(BaseModel):
    """
    Esquema de entrada para la búsqueda en la base de conocimiento técnica.
    """

    query: str = Field(
        ...,
        min_length=3,
        description=(
            "Consulta técnica sobre dispositivos IoT, por ejemplo: "
            "'Sensor-X200 desconexión por humedad' o "
            "'Gateway-G20 configuración DNS'."
        ),
    )

    limit: int = Field(
        default=1,
        ge=1,
        le=5,
        description=(
            "Cantidad máxima de documentos a devolver. "
            "Se recomienda usar 1 para obtener información específica "
            "y permitir búsquedas sucesivas si hace falta más contexto."
        ),
    )


def _load_knowledge_base() -> list[dict[str, Any]]:
    """
    Carga la base de conocimiento técnica desde el archivo JSON local.

    La base contiene incidentes, configuraciones, versiones de firmware
    y recomendaciones de soporte para sensores y gateways IoT.

    Returns:
        Lista de documentos técnicos.

    Raises:
        FileNotFoundError:
            Si el archivo technical_knowledge.json no existe.
        RuntimeError:
            Si el archivo no contiene JSON válido o no puede ser leído.
    """

    if not KNOWLEDGE_BASE_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró la base de conocimiento en: "
            f"{KNOWLEDGE_BASE_PATH}"
        )

    try:
        with KNOWLEDGE_BASE_PATH.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "El archivo technical_knowledge.json contiene JSON inválido."
        ) from exc

    except OSError as exc:
        raise RuntimeError(
            f"No fue posible leer la base de conocimiento: {exc}"
        ) from exc

    if not isinstance(data, list):
        raise RuntimeError(
            "La base de conocimiento debe contener una lista de documentos."
        )

    return data


def _calculate_score(query: str, document: dict[str, Any]) -> int:
    """
    Calcula un score simple de relevancia por coincidencia de palabras.

    No se utilizan embeddings porque el objetivo del proyecto es demostrar
    razonamiento cíclico, uso autónomo de herramientas y persistencia,
    no implementar un sistema RAG completo.

    La búsqueda compara la consulta con los campos device, category,
    title y content del documento.

    Args:
        query:
            Consulta enviada por el agente.
        document:
            Documento técnico de la base de conocimiento.

    Returns:
        Número de términos de la consulta encontrados en el documento.
    """

    query_terms = {
        word.strip(".,;:!?¿¡()[]").lower()
        for word in query.split()
        if len(word.strip(".,;:!?¿¡()[]")) > 2
    }

    searchable_text = " ".join(
        [
            str(document.get("device", "")),
            str(document.get("category", "")),
            str(document.get("title", "")),
            str(document.get("content", "")),
        ]
    ).lower()

    return sum(
        1
        for term in query_terms
        if term in searchable_text
    )


@tool(args_schema=SearchKnowledgeInput)
async def search_technical_knowledge(
    query: str,
    limit: int = 1,
) -> list[dict[str, Any]]:
    """
    Busca información en una base de conocimiento de soporte técnico para
    dispositivos IoT.

    Utiliza esta herramienta cuando el usuario consulte sobre problemas,
    configuraciones, firmware, conectividad, batería, instalación o
    comportamiento de dispositivos como Sensor-X100, Sensor-X200,
    Sensor-T300 o Gateway-G20.

    La información está distribuida en distintos documentos técnicos.
    Una única búsqueda puede no contener toda la respuesta necesaria.
    Si el resultado indica que debe consultarse firmware, configuración,
    instalación u otra documentación adicional, vuelve a utilizar esta
    herramienta con una consulta más específica.

    Ejemplo:
        Si el usuario pregunta:
        "Mi Sensor-X200 pierde conexión cuando hay mucha humedad.
        ¿Cuál es la causa y qué firmware debería utilizar?"

        Una primera búsqueda como:
        "Sensor-X200 pérdida conexión humedad"

        puede explicar la causa pero no indicar la versión de firmware.

        En ese caso debes realizar una segunda búsqueda como:
        "Sensor-X200 firmware humedad"

        antes de responder al usuario.

    Args:
        query:
            Consulta técnica que describe el dispositivo y el problema.
        limit:
            Cantidad máxima de documentos relevantes a devolver.

    Returns:
        Lista de documentos técnicos ordenados por relevancia.

        Si no se encuentra información relevante, devuelve una lista
        con un mensaje explícito indicando que no hubo resultados.

    Raises:
        RuntimeError:
            Si ocurre un problema al cargar o procesar la base de conocimiento.
    """

    try:
        knowledge_base = _load_knowledge_base()

        scored_documents: list[tuple[int, dict[str, Any]]] = []

        for document in knowledge_base:
            score = _calculate_score(query, document)

            if score > 0:
                scored_documents.append((score, document))

        scored_documents.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        results = [
            document
            for _, document in scored_documents[:limit]
        ]

        if not results:
            return [
                {
                    "status": "not_found",
                    "message": (
                        "No se encontró información relevante para la consulta. "
                        "Intenta reformular la búsqueda indicando el modelo del "
                        "dispositivo y el tipo de problema."
                    ),
                    "query": query,
                }
            ]

        return results

    except (FileNotFoundError, RuntimeError):
        raise

    except Exception as exc:
        raise RuntimeError(
            f"Error inesperado al buscar información técnica: {exc}"
        ) from exc


tools = [search_technical_knowledge]