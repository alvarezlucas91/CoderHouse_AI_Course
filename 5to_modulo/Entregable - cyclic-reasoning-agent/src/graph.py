from typing import Any

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    validate_project_configuration,
)
from src.tools import tools


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
Eres un asistente de soporte técnico especializado en dispositivos IoT.

Tu objetivo es resolver completamente las consultas utilizando la base de
conocimiento técnica disponible mediante herramientas.

Reglas:

1. No inventes información técnica que no esté disponible en la conversación
   o en los resultados de las herramientas.

2. Utiliza search_technical_knowledge cuando necesites consultar información
   sobre dispositivos, errores, firmware, configuración, batería, instalación
   o conectividad.

3. Una consulta del usuario puede requerir información proveniente de varios
   documentos. Debes asegurarte de responder TODOS los puntos solicitados
   antes de generar la respuesta final.

4. Si un resultado contiene:
       information_status = "incomplete"
   significa que todavía NO tienes información suficiente para responder.
   Debes analizar el campo next_step y realizar otra búsqueda más específica.

5. No respondas al usuario indicándole simplemente que consulte otra
   documentación si puedes obtener esa información utilizando
   search_technical_knowledge.

6. Puedes ejecutar search_technical_knowledge múltiples veces. El ciclo
   esperado puede ser:

       usuario
         -> búsqueda
         -> análisis
         -> segunda búsqueda
         -> análisis
         -> respuesta final

7. Si el usuario solicita dos datos, por ejemplo "causa" y "versión de
   firmware", no finalices hasta haber encontrado información para ambos.

8. Si después de realizar búsquedas razonables la información no existe,
   explica qué información falta o solicita una aclaración al usuario.

Responde de forma clara, concisa y basada exclusivamente en la información
recuperada.
""".strip()


# ============================================================
# MODELO
# ============================================================


def create_model() -> Runnable:
    """
    Crea y configura el modelo Groq utilizado por el agente.

    El modelo se vincula con las herramientas técnicas disponibles mediante
    bind_tools(), permitiendo que el LLM decida autónomamente cuándo consultar
    la base de conocimiento.

    Por ejemplo, ante una consulta sobre un Sensor-X200 que pierde conexión
    en ambientes húmedos, el modelo puede decidir utilizar
    search_technical_knowledge y realizar nuevas búsquedas si la primera
    respuesta no contiene toda la información necesaria.

    Returns:
        Runnable de LangChain que representa el modelo Groq con las
        herramientas vinculadas.

    Raises:
        RuntimeError:
            Si la configuración del proyecto es inválida o no puede
            inicializarse el modelo.
    """

    try:
        validate_project_configuration()

        llm = ChatGroq(
            model=GROQ_MODEL,
            api_key=GROQ_API_KEY,
            temperature=0,
        )

        return llm.bind_tools(tools)

    except Exception as exc:
        raise RuntimeError(
            f"No fue posible inicializar el modelo Groq: {exc}"
        ) from exc

    
model = create_model()


# ============================================================
# NODO DEL AGENTE
# ============================================================


async def call_model(state: MessagesState) -> dict[str, list[BaseMessage]]:
    """
    Ejecuta el nodo de razonamiento principal del agente.

    Recibe el historial acumulado de mensajes almacenado en MessagesState
    y lo envía al modelo Groq junto con el system prompt.

    El modelo puede realizar una de dos acciones:

    - responder directamente al usuario, o
    - generar una llamada a alguna herramienta disponible.

    Si una herramienta devuelve información incompleta, el resultado vuelve
    al mismo nodo y el modelo puede decidir ejecutar una segunda búsqueda.

    Ejemplo:

        agent
          ↓
        search_technical_knowledge("Sensor-X200 humedad")
          ↓
        agent
          ↓
        search_technical_knowledge("Sensor-X200 firmware")
          ↓
        agent
          ↓
        respuesta final

    Args:
        state:
            Estado actual del grafo. MessagesState contiene el historial
            completo de HumanMessage, AIMessage y ToolMessage.

    Returns:
        Diccionario con el nuevo mensaje generado por el modelo.

    Raises:
        ValueError:
            Si el estado no contiene mensajes.
        RuntimeError:
            Si ocurre un error durante la llamada al modelo.
    """

    messages = state.get("messages", [])

    if not messages:
        raise ValueError(
            "El estado del agente no contiene mensajes para procesar."
        )

    try:
        response = await model.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                *messages,
            ]
        )

        return {
            "messages": [response]
        }

    except Exception as exc:
        raise RuntimeError(
            f"Error durante la ejecución del modelo Groq: {exc}"
        ) from exc


# ============================================================
# TOOL NODE
# ============================================================

tool_node = ToolNode(tools)


# ============================================================
# CONSTRUCCIÓN DEL GRAFO
# ============================================================


def build_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> Any:
    """
    Construye y compila el grafo cíclico del agente.

    Arquitectura:

        START
          |
          v
        agent
          |
          | tools_condition
          |
          +------------------> END
          |
          v
        tools
          |
          v
        agent

    La arista condicional tools_condition inspecciona la salida del modelo.

    Si el LLM genera una tool call:
        agent -> tools

    Si el LLM responde directamente:
        agent -> END

    Luego de ejecutar una herramienta:
        tools -> agent

    Esta última conexión genera el ciclo de razonamiento que permite realizar
    múltiples consultas antes de producir una respuesta final.

    Args:
        checkpointer:
            Checkpointer opcional utilizado para persistir el estado del
            agente entre distintas ejecuciones. En desarrollo utilizaremos
            AsyncSqliteSaver.

    Returns:
        Grafo compilado y listo para utilizar con ainvoke() o astream().

    Raises:
        RuntimeError:
            Si ocurre un error durante la construcción del grafo.
    """

    try:
        workflow = StateGraph(MessagesState)

        workflow.add_node(
            "agent",
            call_model,
        )

        workflow.add_node(
            "tools",
            tool_node,
        )

        # Entrada del grafo
        workflow.add_edge(
            START,
            "agent",
        )

        # El LLM decide autónomamente si necesita ejecutar una herramienta.
        workflow.add_conditional_edges(
            "agent",
            tools_condition,
            {
                "tools": "tools",
                END: END,
            },
        )

        # Después de ejecutar una herramienta volvemos al modelo.
        # Esta arista es la que permite el ciclo ReAct.
        workflow.add_edge(
            "tools",
            "agent",
        )

        return workflow.compile(
            checkpointer=checkpointer
        )

    except Exception as exc:
        raise RuntimeError(
            f"No fue posible construir el grafo del agente: {exc}"
        ) from exc