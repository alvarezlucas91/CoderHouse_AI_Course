import pytest

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from src.graph import build_graph
from src.tools import search_technical_knowledge


# ============================================================
# TEST 1 - TOOL DE BÚSQUEDA
# ============================================================

@pytest.mark.asyncio
async def test_search_technical_knowledge_returns_result():
    """
    Verifica que la herramienta pueda recuperar información relevante
    desde la base de conocimiento técnica.

    Caso de prueba:
        Se consulta por problemas de conectividad del Sensor-X200
        en ambientes húmedos.

    Resultado esperado:
        La herramienta debe devolver al menos un documento relacionado
        con ese dispositivo y problema.
    """

    result = await search_technical_knowledge.ainvoke(
        {
            "query": "Sensor-X200 desconexión humedad",
            "limit": 1,
        }
    )

    assert result
    assert isinstance(result, list)

    first_result = result[0]

    assert "device" in first_result
    assert first_result["device"] == "Sensor-X200"


# ============================================================
# TEST 2 - BÚSQUEDA SIN RESULTADOS
# ============================================================

@pytest.mark.asyncio
async def test_search_technical_knowledge_not_found():
    """
    Verifica el comportamiento de la herramienta cuando la consulta
    no coincide con ningún documento de la base de conocimiento.

    Caso de prueba:
        Se consulta por un dispositivo inexistente llamado Sensor-Z999.

    Resultado esperado:
        La herramienta debe devolver una respuesta controlada con
        status = 'not_found' en lugar de producir una excepción.
    """

    result = await search_technical_knowledge.ainvoke(
        {
            "query": "Sensor-Z999 error desconocido",
            "limit": 1,
        }
    )

    assert result
    assert isinstance(result, list)

    first_result = result[0]

    assert first_result["status"] == "not_found"
    assert "message" in first_result


# ============================================================
# TEST 3 - MEMORIA DEL GRAFO
# ============================================================

@pytest.mark.asyncio
async def test_agent_keeps_conversation_history():
    """
    Verifica que LangGraph conserve el historial cuando se utiliza
    el mismo thread_id.

    Primera interacción:
        El usuario indica que tiene un Sensor-X200.

    Segunda interacción:
        El usuario pregunta qué modelo había mencionado anteriormente,
        sin repetir el nombre del dispositivo.

    Resultado esperado:
        El agente debe poder recuperar el contexto previo desde
        el checkpointer.
    """

    memory = MemorySaver()

    app = build_graph(
        checkpointer=memory
    )

    config = {
        "configurable": {
            "thread_id": "test_memory_01"
        },
        "recursion_limit": 10,
    }

    # Primera interacción
    first_result = await app.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        "Tengo un Sensor-X200 instalado en un depósito "
                        "con problemas de conectividad."
                    )
                )
            ]
        },
        config=config,
    )

    assert first_result["messages"]

    # Segunda interacción usando el mismo thread_id
    second_result = await app.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        "¿Qué modelo de dispositivo te había mencionado "
                        "anteriormente?"
                    )
                )
            ]
        },
        config=config,
    )

    assert second_result["messages"]

    final_response = second_result["messages"][-1].content

    assert "X200" in final_response


# ============================================================
# TEST 4 - ESTADO ACUMULATIVO
# ============================================================

@pytest.mark.asyncio
async def test_messages_state_accumulates_messages():
    """
    Verifica que MessagesState conserve los mensajes anteriores
    en lugar de reemplazarlos.

    Esto valida una parte central de la arquitectura del agente:
    el estado debe acumular HumanMessage, AIMessage y ToolMessage
    a medida que el grafo avanza.
    """

    memory = MemorySaver()

    app = build_graph(
        checkpointer=memory
    )

    config = {
        "configurable": {
            "thread_id": "test_accumulation_01"
        },
        "recursion_limit": 10,
    }

    result = await app.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content="Tengo un Sensor-X100."
                )
            ]
        },
        config=config,
    )

    assert "messages" in result
    assert len(result["messages"]) >= 2