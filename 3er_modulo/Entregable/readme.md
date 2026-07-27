# End-to-End RAG con LangChain y ChromaDB

## Tecnologías utilizadas

- Python 3.11+
- LangChain
- ChromaDB
- HuggingFace Embeddings (`sentence-transformers/all-MiniLM-L6-v2`)
- Groq (Llama 3.3 70B Versatile)
- Pydantic

## Descripción

Este proyecto implementa un sistema **Retrieval-Augmented Generation (RAG)** que permite responder preguntas utilizando únicamente la información contenida en un conjunto de documentos.

El sistema implementa un flujo Retrieval-Augmented Generation (RAG) compuesto por dos etapas principales:

1. **Ingesta de documentos:** lectura de archivos, fragmentación (chunking) e indexación en ChromaDB.
2. **Consulta RAG:** recuperación de los fragmentos más relevantes y generación de una respuesta basada exclusivamente en ese contexto.

---

# Estructura del proyecto

```text
.
├── data/
│   ├── *.md
│   └── *.txt
│
├── src/
│   ├── ingest.py
│   ├── rag_chain.py
│   └── schemas.py
│
├── tests/
│   └── test_rag.py
│
├── vectorstore/
│
├── requirements.txt
├── .env
└── README.md
```

## Descripción de cada carpeta

* **data/**: contiene los documentos que serán indexados por el sistema.
* **src/ingest.py**: realiza la carga de documentos, el chunking y la persistencia en ChromaDB.
* **src/rag_chain.py**: implementa el retriever y la cadena RAG utilizando LangChain (LCEL).
* **src/schemas.py**: define el modelo Pydantic utilizado para estructurar la respuesta.
* **tests/test_rag.py**: ejecuta dos consultas de prueba para verificar el funcionamiento del sistema.
* **vectorstore/**: almacena la base vectorial persistente generada por ChromaDB.

---

# Instalación

Crear un entorno virtual:

```bash
python -m venv .venv
```

Activarlo:

Windows

```bash
.venv\Scripts\activate
```

Instalar las dependencias:

```bash
pip install -r requirements.txt
```

Crear un archivo `.env` con la API Key del proveedor utilizado.

---

# Ejecución

## 1. Ingestar los documentos

Este paso lee todos los archivos ubicados en la carpeta `data/`, los divide en fragmentos utilizando `RecursiveCharacterTextSplitter`, genera sus embeddings y los almacena en una colección persistente de ChromaDB.

```bash
python -m src.ingest
```

La ingesta solo se ejecuta una vez. Si la colección ya existe, el script evita volver a indexar los documentos.

---

## 2. Ejecutar el sistema RAG

Una vez creada la base vectorial, el sistema puede responder consultas recuperando los fragmentos más relevantes y enviándolos al modelo de lenguaje como contexto.

Para probar el funcionamiento se ejecuta:

```bash
python -m tests.test_rag
```

El script realiza dos pruebas:

* Una consulta cuya respuesta se encuentra en los documentos.
* Una consulta cuya respuesta no existe en la base documental, verificando que el modelo responda **"No lo sé"** en lugar de generar información inventada.

---

## Embeddings

Los documentos son indexados y consultados utilizando el mismo modelo de embeddings:

- sentence-transformers/all-MiniLM-L6-v2

De esta manera se garantiza que la búsqueda semántica se realice sobre el mismo espacio vectorial.

---

# Flujo del sistema

```text
Documentos (.md/.txt)
        │
        ▼
ingest.py
        │
        ▼
Chunking
        │
        ▼
Embeddings
        │
        ▼
ChromaDB
        │
        ▼
Consulta del usuario
        │
        ▼
Retriever
        │
        ▼
LLM
        │
        ▼
Respuesta estructurada
```
