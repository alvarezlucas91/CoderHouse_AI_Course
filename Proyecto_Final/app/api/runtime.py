import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from redis.asyncio import Redis

from app.agents import LangChainStructuredModel
from app.config import get_settings
from app.graph import GraphDependencies, build_graph
from app.persistence import JobStore, redis_checkpointer
from app.observability import configure_observability, flush_traces
from app.rag import BM25Retriever, HybridRAGService, load_markdown_corpus
from app.rag.pinecone import PineconeDenseRetriever

from .worker import WorkerPool


logger = logging.getLogger(__name__)


@asynccontextmanager
async def production_lifespan(app: FastAPI):
    settings = get_settings()
    settings.require_external_services()
    logging.basicConfig(level=settings.log_level)
    configure_observability(settings)

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await redis.ping()
    corpus = await asyncio.to_thread(load_markdown_corpus, settings.documents_dir)
    sparse = BM25Retriever(corpus, candidate_limit=settings.rag_top_k_sparse)
    embeddings = await asyncio.to_thread(
        HuggingFaceEmbeddings,
        model_name=settings.embedding_model,
    )
    dense = PineconeDenseRetriever(
        api_key=settings.pinecone_api_key.get_secret_value(),
        index_name=settings.pinecone_index_name,
        namespace=settings.pinecone_namespace,
        embeddings=embeddings,
        candidate_limit=settings.rag_top_k_dense,
    )
    rag = HybridRAGService(dense, sparse, top_k_final=settings.rag_top_k_final)
    chat_model = ChatGroq(
        api_key=settings.groq_api_key.get_secret_value(),
        model=settings.llm_model,
        temperature=0,
    )

    async with redis_checkpointer(settings.redis_url) as checkpointer:
        graph = build_graph(
            GraphDependencies(model=LangChainStructuredModel(chat_model), rag=rag),
            checkpointer=checkpointer,
        )
        store = JobStore(redis, ttl_seconds=settings.job_ttl_seconds)
        workers = WorkerPool(graph, store, concurrency=settings.worker_concurrency)
        app.state.redis = redis
        app.state.job_store = store
        app.state.worker_pool = workers
        app.state.settings = settings
        await workers.start()
        try:
            yield
        finally:
            await workers.stop()
            flush_traces()
            await redis.aclose()

