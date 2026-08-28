import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.config import Settings


logger = logging.getLogger(__name__)
_provider: Any = None


def configure_observability(settings: Settings) -> Any:
    global _provider
    if not settings.phoenix_enabled:
        return None
    try:
        from phoenix.otel import register

        _provider = register(
            project_name=settings.phoenix_project_name,
            endpoint=settings.phoenix_collector_endpoint,
            protocol="http/protobuf",
            batch=True,
            auto_instrument=True,
        )
    except Exception:
        logger.exception("Phoenix initialization failed; service will continue")
    return _provider


def traced(name: str, *, kind: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(function)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = trace.get_tracer("redshift-intelligence")
            with tracer.start_as_current_span(
                name, attributes={"openinference.span.kind": kind}
            ) as span:
                try:
                    result = await function(*args, **kwargs)
                    span.set_attribute("app.status", "ok")
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    raise

        @functools.wraps(function)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = trace.get_tracer("redshift-intelligence")
            with tracer.start_as_current_span(
                name, attributes={"openinference.span.kind": kind}
            ) as span:
                try:
                    return function(*args, **kwargs)
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    raise

        return async_wrapper if inspect.iscoroutinefunction(function) else sync_wrapper

    return decorator


def flush_traces() -> None:
    if _provider is not None:
        _provider.force_flush()

