"""No-op Atlas observer for focused tests."""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
from typing import Any, Iterator


class NoOpSpan:
    """Minimal span object matching the update API Atlas uses."""

    def update(self, *args: Any, **kwargs: Any) -> None:
        return None


class NoOpObserver:
    """Observer with the same domain-method surface and no side effects."""

    def agent_run(self, **kwargs: Any):
        return nullcontext(NoOpSpan())

    def trace_context(self, **kwargs: Any):
        return nullcontext()

    def execution_loop(self, **kwargs: Any):
        return nullcontext(NoOpSpan())

    def iteration(self, **kwargs: Any):
        return nullcontext(NoOpSpan())

    def tool(self, **kwargs: Any):
        return nullcontext(NoOpSpan())

    def current_context(self) -> None:
        return None

    @contextmanager
    def attach_context(self, context: Any) -> Iterator[None]:
        yield
