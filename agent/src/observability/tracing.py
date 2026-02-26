"""Langfuse observability via OpenTelemetry for the OpenEMR healthcare agent.

Uses the standard OpenTelemetry OTLP exporter to send traces to Langfuse's
``/api/public/otel`` endpoint.  This avoids the ``langfuse`` Python SDK which
is incompatible with Python 3.14 (pydantic v1 breakage).

Provides:
- ``init_tracing``: one-time OTEL TracerProvider setup.
- ``create_langfuse_handler``: per-request LangChain callback handler that
  injects an OTEL-backed trace into every LLM call and tool invocation.
- ``log_feedback``: post user feedback to Langfuse REST API by trace ID.
"""

from __future__ import annotations

import base64
import logging
import time
import uuid
from typing import Any

import httpx
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from src.config import LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY

logger = logging.getLogger(__name__)

_langfuse_enabled: bool = bool(LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY)
_tracer: trace.Tracer | None = None


# ── OTEL initialisation ─────────────────────────────────────────────────────


def init_tracing() -> None:
    """Configure the global OpenTelemetry TracerProvider to export to Langfuse."""
    global _tracer

    if not _langfuse_enabled:
        logger.info("Langfuse not configured — tracing disabled")
        return

    auth = base64.b64encode(
        f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}".encode()
    ).decode()

    endpoint = f"{LANGFUSE_HOST.rstrip('/')}/api/public/otel"

    exporter = OTLPSpanExporter(
        endpoint=f"{endpoint}/v1/traces",
        headers={"Authorization": f"Basic {auth}"},
    )

    resource = Resource.create({"service.name": "openemr-agent"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    _tracer = trace.get_tracer("openemr-agent")
    logger.info("Langfuse OTEL tracing initialised → %s", endpoint)


# ── LangChain callback handler ──────────────────────────────────────────────


class LangfuseOtelHandler(BaseCallbackHandler):
    """LangChain callback that emits OTEL spans for Langfuse.

    Each handler instance represents one request trace.  It creates nested
    spans for LLM calls and tool invocations so that Langfuse renders a
    full waterfall with latency, token usage, and errors.
    """

    def __init__(
        self,
        trace_id: str,
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        super().__init__()
        self.trace_id = trace_id
        self.session_id = session_id
        self.user_id = user_id
        self.metadata = metadata or {}
        self._spans: dict[str, Any] = {}  # run_id → span
        self._root_span: Any = None

    # ── lifecycle ────────────────────────────────────────────────────────

    def _get_tracer(self) -> trace.Tracer:
        global _tracer
        if _tracer is None:
            _tracer = trace.get_tracer("openemr-agent")
        return _tracer

    def _start_root(self) -> None:
        if self._root_span is not None:
            return
        tracer = self._get_tracer()
        self._root_span = tracer.start_span(
            name="openemr-agent-request",
            attributes={
                "langfuse.trace.id": self.trace_id,
                "langfuse.session.id": self.session_id or "",
                "langfuse.user.id": self.user_id or "",
            },
        )

    # ── LLM callbacks ───────────────────────────────────────────────────

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        self._start_root()
        tracer = self._get_tracer()
        model = serialized.get("kwargs", {}).get("model", "unknown")
        ctx = trace.set_span_in_context(self._root_span)
        span = tracer.start_span(
            name=f"llm:{model}",
            context=ctx,
            attributes={
                "gen_ai.system": "anthropic",
                "gen_ai.request.model": model,
                "langfuse.trace.id": self.trace_id,
            },
        )
        self._spans[str(run_id)] = span

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        span = self._spans.pop(str(run_id), None)
        if span is None:
            return
        # Extract token usage if available.
        usage = (response.llm_output or {}).get("usage", {})
        if usage:
            span.set_attribute(
                "gen_ai.usage.input_tokens",
                usage.get("input_tokens", 0),
            )
            span.set_attribute(
                "gen_ai.usage.output_tokens",
                usage.get("output_tokens", 0),
            )
        span.end()

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        span = self._spans.pop(str(run_id), None)
        if span is None:
            return
        span.set_attribute("error", True)
        span.set_attribute("error.message", str(error))
        span.record_exception(error)
        span.end()

    # ── Tool callbacks ───────────────────────────────────────────────────

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        self._start_root()
        tracer = self._get_tracer()
        tool_name = serialized.get("name", "unknown_tool")
        ctx = trace.set_span_in_context(self._root_span)
        span = tracer.start_span(
            name=f"tool:{tool_name}",
            context=ctx,
            attributes={
                "tool.name": tool_name,
                "langfuse.trace.id": self.trace_id,
            },
        )
        self._spans[str(run_id)] = span

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        span = self._spans.pop(str(run_id), None)
        if span is None:
            return
        span.end()

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        span = self._spans.pop(str(run_id), None)
        if span is None:
            return
        span.set_attribute("error", True)
        span.set_attribute("error.message", str(error))
        span.record_exception(error)
        span.end()

    # ── Chain callbacks (for scope guard / disclaimer nodes) ─────────────

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        self._start_root()
        tracer = self._get_tracer()
        name = serialized.get("name", serialized.get("id", ["chain"])[-1])
        ctx = trace.set_span_in_context(self._root_span)
        span = tracer.start_span(
            name=f"chain:{name}",
            context=ctx,
            attributes={"langfuse.trace.id": self.trace_id},
        )
        self._spans[str(run_id)] = span

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        span = self._spans.pop(str(run_id), None)
        if span is not None:
            span.end()

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        span = self._spans.pop(str(run_id), None)
        if span is not None:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(error))
            span.record_exception(error)
            span.end()

    # ── Cleanup ──────────────────────────────────────────────────────────

    def flush(self) -> None:
        """End the root span and flush the OTEL provider."""
        if self._root_span is not None:
            self._root_span.end()
            self._root_span = None
        provider = trace.get_tracer_provider()
        if hasattr(provider, "force_flush"):
            provider.force_flush()


# ── Public factory ───────────────────────────────────────────────────────────


def create_langfuse_handler(
    trace_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict | None = None,
) -> tuple[LangfuseOtelHandler | None, str]:
    """Create a per-request callback handler that traces to Langfuse via OTEL.

    Returns:
        A (handler, trace_id) tuple.  ``handler`` is None when Langfuse
        credentials are not configured.
    """
    if trace_id is None:
        trace_id = uuid.uuid4().hex

    if not _langfuse_enabled:
        logger.debug("Langfuse not configured — tracing disabled")
        return None, trace_id

    return LangfuseOtelHandler(
        trace_id=trace_id,
        user_id=user_id,
        session_id=session_id,
        metadata=metadata,
    ), trace_id


# ── Feedback via Langfuse REST API ───────────────────────────────────────────


def log_feedback(trace_id: str, score: int, comment: str | None = None) -> bool:
    """Post user feedback to Langfuse REST API.

    Args:
        trace_id: The Langfuse trace ID returned from ``run_agent``.
        score:    1 (positive) or 0 (negative).
        comment:  Optional free-text comment.

    Returns:
        True if the score was submitted, False otherwise.
    """
    if not _langfuse_enabled:
        logger.warning("Langfuse not configured — feedback not recorded")
        return False

    url = f"{LANGFUSE_HOST.rstrip('/')}/api/public/scores"
    auth = (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY)
    payload: dict[str, Any] = {
        "traceId": trace_id,
        "name": "user-feedback",
        "value": score,
        "dataType": "NUMERIC",
    }
    if comment:
        payload["comment"] = comment

    try:
        resp = httpx.post(url, json=payload, auth=auth, timeout=10.0)
        resp.raise_for_status()
        logger.info("Feedback recorded for trace %s: score=%d", trace_id, score)
        return True
    except Exception:
        logger.exception("Failed to submit feedback for trace %s", trace_id)
        return False
