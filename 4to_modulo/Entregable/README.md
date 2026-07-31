# Hybrid RAG with Pinecone, BM25 and Groq

## Description

This project implements a **Retrieval-Augmented Generation (RAG)** system using a **hybrid retrieval strategy**.

The retrieval process combines:

- **Dense retrieval** using Pinecone and HuggingFace embeddings.
- **Sparse retrieval** using BM25.
- **EnsembleRetriever** to combine both retrieval strategies.

The retrieved context is then used by a **Groq LLM** to answer user questions.

---

# Project Structure

```text
.
├── data/
│   ├── documents/
│   └── evaluation_dataset.json
│
├── src/
│   ├── config.py
│   ├── setup_pinecone.py
│   ├── ingest.py
│   ├── rag_system.py
│   ├── evaluate.py
│   │
│   ├── embeddings/
│   ├── llm/
│   ├── loaders/
│   ├── processing/
│   ├── retrievers/
│   ├── utils/
│   └── vectorstores/
│
├── requirements.txt
├── .env
└── README.md
```

---

# Components

### Document Loader

Loads all supported documents from the `data/documents` directory.

---

### Text Splitter

Splits documents into overlapping chunks before indexing.

---

### Embedding Service

Generates dense embeddings using a HuggingFace model.

---

### Pinecone Manager

Creates and manages the Pinecone vector index.

Responsible for:

- inserting documents
- similarity search
- retriever creation

---

### Hybrid Retriever

Builds two retrieval systems:

- Pinecone semantic search
- BM25 lexical search

Both are combined using LangChain's `EnsembleRetriever`.

---

### LLM Service

Creates the Groq language model used to generate answers.

---

### Evaluation

Runs predefined questions stored in `evaluation_dataset.json` and computes retrieval metrics:

- Precision@K
- Recall@K

---

# Environment Variables

Create a `.env` file with:

```env
PINECONE_API_KEY=your_pinecone_api_key
GROQ_API_KEY=your_groq_api_key
```

---

# Installation

Create a virtual environment

```bash
python -m venv .venv
```

Activate it

Windows

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# Running the Project

## 1. Create the Pinecone index

```bash
python -m src.setup_pinecone
```

---

## 2. Ingest the documents

```bash
python -m src.ingest
```

This step:

- loads the documents
- splits them into chunks
- generates embeddings
- uploads vectors to Pinecone

---

## 3. Evaluate retrieval

```bash
python -m src.evaluate
```

The evaluation script executes all questions from:

```
data/evaluation_dataset.json
```

and reports:

- retrieved documents
- Precision@K
- Recall@K
- average metrics

---

# Retrieval Pipeline

```
Documents
     │
     ▼
Document Loader
     │
     ▼
Text Splitter
     │
     ▼
HuggingFace Embeddings
     │
     ▼
Pinecone Vector Store
     │
     ▼
Hybrid Retriever
(Pinecone + BM25)
     │
     ▼
Relevant Context
     │
     ▼
Groq LLM
     │
     ▼
Final Answer
```

---

# Technologies

- Python
- LangChain
- Pinecone
- HuggingFace Embeddings
- Sentence Transformers
- BM25
- Groq
- dotenv

---

# Notes

This implementation focuses on demonstrating a modular Hybrid RAG architecture, including:

- document ingestion
- vector indexing
- hybrid retrieval
- retrieval evaluation
- modular project organization