# Agente de Razonamiento Cíclico con Memoria Persistente

## Descripción

Este proyecto implementa un agente autónomo de soporte técnico utilizando **LangGraph**, **LangChain** y **Groq**.

El agente simula un asistente especializado en soporte de dispositivos IoT. Puede consultar una base de conocimiento técnica mediante herramientas, realizar múltiples búsquedas cuando necesita información adicional y mantener el contexto de una conversación utilizando persistencia con SQLite.

El objetivo principal es demostrar:

* Razonamiento cíclico con LangGraph.
* Uso autónomo de herramientas.
* Ejecución asíncrona.
* Razonamiento multi-paso.
* Persistencia de conversaciones mediante `thread_id`.
* Control de ciclos mediante `recursion_limit`.

---

## Arquitectura

El agente utiliza un `StateGraph` basado en `MessagesState`.

El flujo principal es:

```text
START
  |
  v
Agent
  |
  | tools_condition
  |
  +----------------------> END
  |
  v
Tools
  |
  v
Agent
```

El modelo decide autónomamente si necesita utilizar una herramienta.

Cuando el agente genera una llamada a una herramienta, `tools_condition` dirige el flujo hacia `ToolNode`. Una vez ejecutada la herramienta, el resultado vuelve al agente para que pueda analizarlo, realizar nuevas búsquedas si son necesarias o generar la respuesta final.

No se utilizan condiciones manuales basadas en el contenido del mensaje para decidir cuándo ejecutar herramientas.

---

## Caso de uso

El proyecto simula una base de conocimiento de soporte técnico para dispositivos IoT como:

* `Sensor-X100`
* `Sensor-X200`
* `Sensor-T300`
* `Gateway-G20`

La información está distribuida en diferentes documentos relacionados con conectividad, firmware, batería, configuración, instalación y calibración.

Por ejemplo, ante la consulta:

```text
Tengo un Sensor-X200 que se desconecta cuando hay mucha humedad.
Quiero saber cuál puede ser la causa y qué versión de firmware
debería tener instalada.
```

el agente puede realizar diferentes búsquedas:

```text
Sensor-X200 desconexión humedad

Sensor-X200 firmware humedad
```

y combinar los resultados antes de generar la respuesta final.

---

## Estructura del proyecto

```text
cyclic-reasoning-agent/
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── tools.py
│   ├── graph.py
│   └── main.py
│
├── data/
│   └── technical_knowledge.json
│
├── logs/
│   └── execution_trace.json
│
├── tests/
│   ├── __init__.py
│   └── test_agent.py
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

### `src/config.py`

Centraliza la configuración del proyecto:

* API Key de Groq.
* Modelo utilizado.
* Rutas de archivos.
* Ruta de SQLite.
* `recursion_limit`.

### `src/tools.py`

Define `search_technical_knowledge`, una herramienta asíncrona que permite al agente consultar la base de conocimiento de dispositivos IoT.

La herramienta utiliza un esquema Pydantic para validar sus argumentos.

### `src/graph.py`

Contiene la arquitectura principal de LangGraph:

* `MessagesState`
* `ChatGroq`
* `bind_tools()`
* `ToolNode`
* `tools_condition`
* ciclo `agent -> tools -> agent`

### `src/main.py`

Ejecuta una demostración del agente utilizando `asyncio`.

También configura la persistencia mediante `AsyncSqliteSaver`, ejecuta la prueba de memoria y genera la traza de ejecución.

### `data/technical_knowledge.json`

Base de conocimiento simulada utilizada por la herramienta de búsqueda.

### `logs/execution_trace.json`

Ejemplo de una ejecución real del agente donde pueden observarse los mensajes, llamadas a herramientas y resultados obtenidos.

---

## Requisitos

* Python 3.12+
* API Key de Groq

---

## Instalación

Crear un entorno virtual:

### Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instalar las dependencias:

```bash
pip install -r requirements.txt
```

---

## Variables de entorno

Crear un archivo `.env` en la raíz del proyecto.

Puede utilizarse `.env.example` como referencia:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
RECURSION_LIMIT=10
```

La API Key real no debe incluirse en el repositorio.

---

## Ejecución

Desde la raíz del proyecto:

```bash
python -m src.main
```

La ejecución realiza dos pruebas.

### 1. Razonamiento multi-paso

El usuario consulta por un problema técnico del `Sensor-X200`.

El agente decide utilizar `search_technical_knowledge` para obtener la información necesaria antes de responder.

Una ejecución puede generar llamadas como:

```text
search_technical_knowledge(
    query="Sensor-X200 desconexión humedad"
)

search_technical_knowledge(
    query="Sensor-X200 firmware humedad"
)
```

Finalmente combina la información obtenida y genera la respuesta.

### 2. Memoria persistente

La segunda interacción utiliza el mismo `thread_id`.

Por ejemplo:

```text
¿Qué modelo de dispositivo te había mencionado anteriormente
y cuál era el problema que tenía?
```

El modelo puede recuperar el contexto anterior porque LangGraph mantiene los checkpoints de la conversación en SQLite.

---

## Persistencia

La persistencia se implementa mediante:

```python
AsyncSqliteSaver
```

Cada conversación se identifica mediante un:

```python
thread_id
```

Mientras se utilice el mismo identificador, LangGraph puede recuperar el estado almacenado anteriormente.

Durante la ejecución se genera:

```text
agent_memory.db
```

Este archivo está excluido del repositorio mediante `.gitignore`.

---

## Prevención de ciclos infinitos

El grafo contiene un ciclo intencional:

```text
Agent -> Tools -> Agent
```

Para evitar ejecuciones infinitas se configura:

```text
RECURSION_LIMIT=10
```

LangGraph detendrá la ejecución si el agente supera el máximo de pasos permitido.

---

## Tests

Los tests utilizan `pytest` y `pytest-asyncio`.

Para ejecutarlos:

```bash
python -m pytest -v
```

Se validan los siguientes escenarios:

* Búsqueda correcta en la base de conocimiento.
* Manejo de consultas sin resultados.
* Persistencia del historial mediante `thread_id`.
* Acumulación de mensajes dentro de `MessagesState`.

---

## Traza de ejecución

Cada ejecución genera un ejemplo de traza en:

```text
logs/execution_trace.json
```

La traza permite observar el proceso seguido por el agente.

Por ejemplo:

```text
HumanMessage
    |
    v
AIMessage
    |
    +-- Tool Call: Sensor-X200 desconexión humedad
    |
    +-- Tool Call: Sensor-X200 firmware humedad
    |
    v
ToolMessage
    |
    v
ToolMessage
    |
    v
AIMessage
    |
    v
Respuesta final
```

Esto permite verificar que las herramientas fueron seleccionadas autónomamente por el modelo y que el agente utilizó diferentes fuentes de información antes de generar la respuesta.

---

## Tecnologías utilizadas

* Python 3.12+
* LangChain
* LangGraph
* Groq
* Pydantic
* SQLite / aiosqlite
* pytest
* pytest-asyncio

---

## Seguridad

Las credenciales se gestionan mediante variables de entorno.

El archivo `.env` está incluido en `.gitignore` y no debe subirse al repositorio.

El repositorio incluye únicamente `.env.example` como referencia de las variables necesarias para ejecutar el proyecto.
