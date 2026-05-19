"""OpenRouter-only OpenAI-compatible client builder.

Single LLM entry point for the platform. Returns a vanilla `openai.OpenAI`
pointed at OpenRouter, plus the model string to call it with. OpenRouter
speaks the OpenAI chat-completions wire format and forwards `cache_control`
to upstream models (Anthropic, Gemini, etc.) that support prompt caching —
so a single client covers every provider we care about.

When `LANGFUSE_PUBLIC_KEY` is set, `import langfuse.openai` patches the
OpenAI SDK process-globally so every call is auto-captured as a Langfuse
generation under the active span. The patch is a side-effect import — the
agent loop never sees it.
"""

from __future__ import annotations

import os
from typing import Tuple

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

__all__ = ["build_client", "DEFAULT_BASE_URL"]


# ================================
# --> Helper funcs
# ================================


def _maybe_enable_langfuse_instrumentation() -> None:
    """Trigger the langfuse.openai import side effect when keys are present.

    Idempotent — re-importing is a no-op.
    """
    if os.getenv("LANGFUSE_PUBLIC_KEY"):
        import langfuse.openai  # noqa: F401  (import-for-side-effect)


# ================================
# --> Builder
# ================================


def build_client(model: str) -> Tuple[OpenAI, str]:
    """Return (OpenRouter client, model). `model` must be a full OpenRouter slug.

    Reads `OPENROUTER_API_KEY` (required) and `OPENROUTER_API_URL`
    (optional, defaults to https://openrouter.ai/api/v1).
    """
    _maybe_enable_langfuse_instrumentation()

    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError("missing env var OPENROUTER_API_KEY")

    if not model:
        raise ValueError("model is required (pass an OpenRouter slug like 'anthropic/claude-sonnet-4.6')")

    base_url = os.getenv("OPENROUTER_API_URL", DEFAULT_BASE_URL)

    return OpenAI(api_key=api_key, base_url=base_url), model
