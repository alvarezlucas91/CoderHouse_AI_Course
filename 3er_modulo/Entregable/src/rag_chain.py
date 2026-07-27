from dotenv import load_dotenv
from pathlib import Path

from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.output_parsers import (
    PydanticOutputParser,
)
from langchain_core.prompts import ChatPromptTemplate
from src.schemas import (
    RAGAnswer,
    RAGResponse,
)


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
COLLECTION_NAME = "technical_documents"

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


vectorstore = Chroma(
    collection_name=COLLECTION_NAME,
    persist_directory=VECTORSTORE_DIR,
    embedding_function=embeddings,
)


retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={
        "k": 4,
    },
)

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
)


parser = PydanticOutputParser(
    pydantic_object=RAGAnswer
)


SYSTEM_PROMPT = """
You are a technical assistant.

You must answer the user's question using ONLY
the information contained in the CONTEXT.

If the answer cannot be found in the CONTEXT,
you MUST answer exactly:

"No lo sé. La información no está disponible
en los documentos proporcionados."

Do not use external knowledge.

Do not infer facts that are not explicitly
supported by the context.

Do not generate references.

{format_instructions}
"""


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            SYSTEM_PROMPT,
        ),
        (
            "human",
            """
CONTEXT:
{context}

USER QUESTION:
{question}
""",
        ),
    ]
).partial(
    format_instructions=(
        parser.get_format_instructions()
    )
)


async def get_rag_response(
    query: str,
) -> RAGResponse:

    documents = await retriever.ainvoke(
        query
    )

    context = "\n\n".join(
                        f"[Fuente: {doc.metadata['source']}]\n{doc.page_content}"
                        for doc in documents
                    )   

    references = list(
        {
            document.metadata["source"]
            for document in documents
        }
    )

    chain = (
        prompt
        | llm
        | parser
    )

    response = await chain.ainvoke(
        {
            "context": context,
            "question": query,
        }
    )

    return RAGResponse(
        answer=response.answer,
        references=references,
    )