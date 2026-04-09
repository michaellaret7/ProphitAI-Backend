"""WorkerSpec — Immutable definition for a scoped worker agent."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class WorkerSpec:
    """Defines a scoped worker agent's configuration.

    Each spec declares the tools (by name) and system prompt a worker
    receives at init. Projects register specs into WORKER_REGISTRY
    so the orchestrator can deploy them by type name.

    Attributes:
        name: Human-readable identifier (e.g., "equity_researcher").
        system_prompt: Custom system prompt for this worker type.
        tools: Set of tool name strings to resolve from the tool registry.
        max_iterations: Execution loop iteration cap.
        provider: Optional LLM provider override. Falls back to WORKER_PROVIDER default.
        model: Optional model override. Falls back to WORKER_MODEL default.
    """

    name: str
    system_prompt: str
    tools: frozenset[str]
    max_iterations: int = 30
    provider: Optional[str] = None
    model: Optional[str] = None
