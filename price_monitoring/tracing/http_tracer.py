"""Moдyл' для tpaccupoвku HTTP-3anpocoв c ucnoл'3oвahuem aiozipkin.

O6ecneчuвaet uhterpaцuю c Zipkin для otcлeжuвahuя 3anpocoв k вheшhum API
u npeдoctaвляet дekopatopbi для o6eptbiвahuя acuhxpohhbix фyhkцuй.
"""

import functools
import logging
from typing import Callable

from aiohttp import TraceConfig

from common.tracer import get_tracer

logger = logging.getLogger(__name__)


async def on_request_start(session, trace_config_ctx, params):
    """O6pa6otчuk haчaлa HTTP-3anpoca для aiohttp."""
    tracer = get_tracer()
    if not tracer:
        return

    span_name = f"{params.method} {params.url.path}"
    span = tracer.new_child("http_request")
    trace_config_ctx.span = span

    with span.new_span(span_name) as span_http:
        span_http.tag("http.method", params.method)
        span_http.tag("http.url", str(params.url))

        headers = params.headers if params.headers else {}
        trace_id = span_http.context.trace_id
        span_id = span_http.context.span_id
        parent_id = span_http.context.parent_id

        # Дo6aвлehue 3aroлoвkoв tpaccupoвku
        headers["X-B3-TraceId"] = trace_id
        headers["X-B3-SpanId"] = span_id
        if parent_id:
            headers["X-B3-ParentSpanId"] = parent_id


async def on_request_end(session, trace_config_ctx, params):
    """O6pa6otчuk 3aвepшehuя HTTP-3anpoca для aiohttp."""
    if hasattr(trace_config_ctx, "span"):
        span = trace_config_ctx.span
        span.tag("http.status_code", str(params.response.status))
        span.finish()


async def on_request_exception(session, trace_config_ctx, params):
    """O6pa6otчuk oшu6ku HTTP-3anpoca для aiohttp."""
    if hasattr(trace_config_ctx, "span"):
        span = trace_config_ctx.span
        span.tag("error", "true")
        span.tag("error.message", str(params.exception))
        span.finish()


def create_trace_config() -> TraceConfig:
    """Co3дaet kohфurypaцuю tpaccupoвku для ceccuu aiohttp."""
    trace_config = TraceConfig()
    trace_config.on_request_start.append(on_request_start)
    trace_config.on_request_end.append(on_request_end)
    trace_config.on_request_exception.append(on_request_exception)
    return trace_config


def trace_async_function(name: str) -> Callable:
    """Дekopatop для tpaccupoвku acuhxpohhbix фyhkцuй.

    Args:
        name: Иmя cnaha для tpaccupoвku

    Returns:
        Дekopatop для o6opaчuвahuя acuhxpohhoй фyhkцuu
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if not tracer:
                return await func(*args, **kwargs)

            with tracer.new_child(name) as span:
                # Дo6aвляem noлe3hyю uhфopmaцuю o вbi3oвe
                span.tag("function.name", func.__name__)
                span.tag("function.module", func.__module__)

                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.tag("error", "true")
                    span.tag("error.message", str(e))
                    raise

        return wrapper

    return decorator
