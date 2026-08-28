from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from .routes import router


@asynccontextmanager
async def production_lifespan(app: FastAPI):
    # Keep provider integrations lazy so importing the API for contract tests
    # does not initialize models or require every production extra.
    from .runtime import production_lifespan as configured_lifespan

    async with configured_lifespan(app):
        yield


def create_app(*, lifespan: Any = production_lifespan) -> FastAPI:
    application = FastAPI(
        title="Redshift Intelligence API",
        version="0.1.0",
        description="Asynchronous multi-agent diagnostic system for Amazon Redshift.",
        lifespan=lifespan,
    )
    application.include_router(router)
    return application


app = create_app()
