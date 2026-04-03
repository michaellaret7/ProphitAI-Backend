"""Abstract base class for LLM backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, Sequence, TypeVar

from pydantic import BaseModel

from prophitai_shared.llm_backends.models import NormalizedLLMResponse

T = TypeVar("T", bound=BaseModel)

class LLMBackend(ABC, Generic[T]):
    """Abstract provider backend used by Atlas and Foundry."""

    def __init__(self, *, provider: str, model: str, raw_client: Any):
        self.provider = provider
        self.model = model
        self.raw_client = raw_client

    @abstractmethod
    def call_llm(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: Optional[Sequence[dict[str, Any]]] = None,
        temperature: Optional[float] = None,
    ) -> NormalizedLLMResponse:
        """Send one LLM turn and normalize the response."""

    @abstractmethod
    def call_llm_structured(
        self,
        *,
        messages: list[dict[str, Any]],
        target_model: type[T],
        temperature: Optional[float] = None,
    ) -> T:
        """Return a validated structured object from the provider."""

    @abstractmethod
    def call_llm_json(
        self,
        *,
        messages: list[dict[str, Any]],
        temperature: Optional[float] = None,
    ) -> str:
        """Return a JSON object string from the provider."""

    @abstractmethod
    def format_tools(self, tools: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """Render canonical tool definitions into provider wire format."""
