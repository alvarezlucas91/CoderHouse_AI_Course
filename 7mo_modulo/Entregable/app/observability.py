from __future__ import annotations

import functools
import inspect
import logging
import os
from typing import Any, Callable

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)
_provider: Any = None


def configure_observability() -> Any:
    """Activa exportación a Phoenix. Si se deshabilita, conserva spans locales no-op."""
    global _provider
    if os.getenv("PHOENIX_ENABLED", "true").lower() not in {"1", "true", "yes"}:
        return None
    try:
        from phoenix.otel import register

        _provider = register(
            project_name=os.getenv("PHOENIX_PROJECT_NAME", "modulo-7-api-agente"),
            endpoint=os.getenv(
                "PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"
            ),
            protocol="http/protobuf",
            batch=True,
            auto_instrument=True,
        )
    except Exception:
        logger.exception("No se pudo inicializar Phoenix; la API seguirá disponible")
    return _provider


def traced_node(name: str, kind: str = "AGENT") -> Callable:
    """Decora nodos sync/async y registra excepciones en el span."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = trace.get_tracer("modulo7.agent-api")
            with tracer.start_as_current_span(
                name, attributes={"openinference.span.kind": kind}
            ) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("app.node.status", "ok")
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = trace.get_tracer("modulo7.agent-api")
            with tracer.start_as_current_span(
                name, attributes={"openinference.span.kind": kind}
            ) as span:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    raise

        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
    return decorator


def flush_traces() -> None:
    if _provider is not None:
        _provider.force_flush()
