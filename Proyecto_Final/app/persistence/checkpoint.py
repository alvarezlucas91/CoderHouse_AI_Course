from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.redis.aio import AsyncRedisSaver


@asynccontextmanager
async def redis_checkpointer(redis_url: str) -> AsyncIterator[AsyncRedisSaver]:
    """Create the durable LangGraph checkpointer and ensure Redis indexes exist."""
    async with AsyncRedisSaver.from_conn_string(redis_url) as checkpointer:
        await checkpointer.asetup()
        yield checkpointer

