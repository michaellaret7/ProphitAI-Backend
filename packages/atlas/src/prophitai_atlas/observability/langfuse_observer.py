"""Langfuse-backed observability for Atlas agents."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Optional

from langfuse import get_client, propagate_attributes
from opentelemetry import context as otel_context


class LangfuseObserver:
    """Expose Atlas-domain observability methods backed by Langfuse."""

    def __init__(self) -> None:
        self._client = get_client()

    def agent_run(
        self,
        *,
        name: str,
        input: Any,
        provider: Optional[str],
        model: str,
    ):
        return self._client.start_as_current_observation(
            as_type="agent",
            name=name,
            input=input,
            metadata={"provider": provider, "model": model},
        )

    def trace_context(
        self,
        *,
        session_id: str,
        tags: list[str],
        metadata: dict[str, Any],
        trace_name: Optional[str] = None,
    ):
        kwargs: dict[str, Any] = {
            "session_id": session_id,
            "tags": tags,
            "metadata": metadata,
        }

        if trace_name is not None:
            kwargs["trace_name"] = trace_name

        return propagate_attributes(**kwargs)

    def execution_loop(self, *, input: dict[str, Any]):
        return self._client.start_as_current_observation(
            as_type="chain",
            name="execution_loop",
            input=input,
        )

    @contextmanager
    def iteration(self, *, number: int, input: dict[str, Any]) -> Iterator[Any]:
        with self._client.start_as_current_observation(
            as_type="span",
            name=f"iteration_{number}",
        ) as span:
            span.update(input=input, metadata={"iteration": str(number)})
            yield span

    @contextmanager
    def tool(self, *, name: str, args: dict[str, Any]) -> Iterator[Any]:
        with self._client.start_as_current_observation(
            as_type="tool",
            name=f"tool: {name}",
        ) as span:
            span.update(input=args, metadata={"tool_name": name})
            yield span

    def current_context(self) -> Any:
        return otel_context.get_current()

    @contextmanager
    def attach_context(self, context: Any) -> Iterator[None]:
        token = otel_context.attach(context)
        try:
            yield
        finally:
            otel_context.detach(token)
