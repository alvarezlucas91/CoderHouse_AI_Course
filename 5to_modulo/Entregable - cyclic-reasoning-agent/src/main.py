import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from src.config import (
    LOGS_DIR,
    RECURSION_LIMIT,
    SQLITE_DB_PATH,
)
from src.graph import build_graph


TRACE_PATH = LOGS_DIR / "execution_trace.json"


def _serialize_message(message: Any) -> dict[str, Any]:
    """
    Convierte un mensaje de LangChain en una estructura serializable a JSON.

    Esta función se utiliza para generar una traza legible de la ejecución
    del agente. La traza permite revisar mensajes del usuario, respuestas
    del modelo y llamadas a herramientas.

    Por ejemplo, si el agente consulta dos veces la base de conocimiento
    antes de responder, ambas tool calls quedarán registradas en el archivo
    execution_trace.json.

    Args:
        message:
            Mensaje generado dentro del flujo de LangGraph.

    Returns:
        Diccionario serializable con tipo, contenido y tool calls cuando
        estén disponibles.
    """

    serialized: dict[str, Any] = {
        "type": getattr(message, "type", message.__class__.__name__),
        "content": getattr(message, "content", ""),
    }

    tool_calls = getattr(message, "tool_calls", None)

    if tool_calls:
        serialized["tool_calls"] = tool_calls

    tool_call_id = getattr(message, "tool_call_id", None)

    if tool_call_id:
        serialized["tool_call_id"] = tool_call_id

    name = getattr(message, "name", None)

    if name:
        serialized["name"] = name

    return serialized


def save_trace(
    thread_id: str,
    user_input: str,
    messages: list[Any],
) -> None:
    """
    Guarda una traza de ejecución del agente en formato JSON.

    El archivo generado sirve como evidencia del razonamiento multi-paso.
    Permite observar cuándo Groq decide ejecutar una herramienta, qué
    argumentos utiliza y qué respuesta obtiene antes de continuar.

    Args:
        thread_id:
            Identificador de la conversación persistente.
        user_input:
            Consulta original enviada por el usuario.
        messages:
            Historial completo devuelto por LangGraph.

    Raises:
        RuntimeError:
            Si no es posible crear o escribir el archivo de traza.
    """

    try:
        LOGS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        trace = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "thread_id": thread_id,
            "input": user_input,
            "messages": [
                _serialize_message(message)
                for message in messages
            ],
        }

        with TRACE_PATH.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                trace,
                file,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

    except OSError as exc:
        raise RuntimeError(
            f"No fue posible guardar la traza en '{TRACE_PATH}': {exc}"
        ) from exc


async def run_agent_turn(
    app: Any,
    thread_id: str,
    user_input: str,
) -> dict[str, Any]:
    """
    Ejecuta una interacción del usuario contra el agente.

    Se utiliza un thread_id para que LangGraph pueda recuperar checkpoints
    anteriores almacenados en SQLite.

    El recursion_limit evita ciclos infinitos en escenarios donde el agente
    continúe llamando herramientas sin alcanzar una conclusión.

    Args:
        app:
            Grafo LangGraph compilado.
        thread_id:
            Identificador persistente de la conversación.
        user_input:
            Consulta enviada por el usuario.

    Returns:
        Estado final del grafo después de procesar la interacción.

    Raises:
        ValueError:
            Si el mensaje del usuario está vacío.
        RuntimeError:
            Si ocurre un error durante la ejecución del grafo.
    """

    if not user_input or not user_input.strip():
        raise ValueError(
            "La consulta del usuario no puede estar vacía."
        )

    config = {
        "configurable": {
            "thread_id": thread_id,
        },
        "recursion_limit": RECURSION_LIMIT,
    }

    try:
        result = await app.ainvoke(
            {
                "messages": [
                    HumanMessage(
                        content=user_input.strip()
                    )
                ]
            },
            config=config,
        )

        return result

    except Exception as exc:
        raise RuntimeError(
            f"Error durante la ejecución del agente: {exc}"
        ) from exc


async def main() -> None:
    """
    Ejecuta una demostración completa del agente IoT.

    La prueba contiene dos etapas.

    Etapa 1:
        Se realiza una consulta que requiere combinar información sobre
        conectividad y firmware del Sensor-X200. El agente debería utilizar
        la herramienta de conocimiento más de una vez antes de responder.

    Etapa 2:
        Se realiza una segunda consulta utilizando el mismo thread_id.
        El usuario no vuelve a mencionar explícitamente el modelo del sensor,
        por lo que la respuesta demuestra que LangGraph recupera el historial
        persistido desde SQLite.

    También se genera logs/execution_trace.json como evidencia de la
    ejecución del agente.
    """

    thread_id = "iot_support_demo_01"

    first_question = (
        "Tengo un Sensor-X200 que se desconecta cuando hay mucha humedad. "
        "Quiero saber cuál puede ser la causa y qué versión de firmware "
        "debería tener instalada."
    )

    second_question = (
        "¿Qué modelo de dispositivo te había mencionado anteriormente "
        "y cuál era el problema que tenía?"
    )

    try:
        print("=" * 70)
        print("AGENTE DE SOPORTE TÉCNICO IoT")
        print("=" * 70)

        # AsyncSqliteSaver mantiene la memoria del agente en disco.
        async with AsyncSqliteSaver.from_conn_string(
            str(SQLITE_DB_PATH)
        ) as checkpointer:

            app = build_graph(
                checkpointer=checkpointer
            )

            # ====================================================
            # PASO 1 - RAZONAMIENTO MULTI-STEP
            # ====================================================

            print("\n--- Paso 1: consulta técnica multi-paso ---")
            print(f"Usuario: {first_question}\n")

            result1 = await run_agent_turn(
                app=app,
                thread_id=thread_id,
                user_input=first_question,
            )

            final_message_1 = result1["messages"][-1]

            print(
                "Agente:",
                final_message_1.content,
            )

            # Guardamos la primera interacción como evidencia principal.
            save_trace(
                thread_id=thread_id,
                user_input=first_question,
                messages=result1["messages"],
            )

            # ====================================================
            # PASO 2 - MEMORIA PERSISTENTE
            # ====================================================

            print("\n--- Paso 2: prueba de memoria persistente ---")
            print(f"Usuario: {second_question}\n")

            result2 = await run_agent_turn(
                app=app,
                thread_id=thread_id,
                user_input=second_question,
            )

            final_message_2 = result2["messages"][-1]

            print(
                "Agente:",
                final_message_2.content,
            )

            print(
                f"\nTraza guardada en: {TRACE_PATH}"
            )

            print(
                f"Memoria SQLite guardada en: {SQLITE_DB_PATH}"
            )

    except ValueError as exc:
        print(
            f"Error de validación: {exc}"
        )

    except RuntimeError as exc:
        print(
            f"Error de ejecución: {exc}"
        )

    except Exception as exc:
        print(
            f"Error inesperado: {exc}"
        )


if __name__ == "__main__":
    asyncio.run(main())