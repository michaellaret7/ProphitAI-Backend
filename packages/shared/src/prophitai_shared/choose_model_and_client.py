"""Configuration-driven LLM provider backend factory.

`get_backend()` is the primary entry point.
`get_model_and_client()` remains as a compatibility shim for callers that still
expect a raw provider client object.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Optional, Tuple

from dotenv import load_dotenv

from prophitai_shared.llm_backends import AnthropicBackend, LLMBackend, OpenAICompatibleBackend

load_dotenv()

__all__ = [
    "ProviderConfig",
    "PROVIDER_CONFIGS",
    "MODEL_ALIASES",
    "get_backend",
    "get_model_and_client",
]


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for an LLM provider."""

    api_key_env: str
    model_env: str
    base_url: Optional[str] = None


PROVIDER_CONFIGS = {
    "openai": ProviderConfig("OPENAI_API_KEY", "OPENAI_MODEL"),
    "anthropic": ProviderConfig("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "https://api.anthropic.com/v1"),
    "gemini": ProviderConfig("GEMINI_API_KEY", "GEMINI_MODEL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    "grok": ProviderConfig("GROK_API_KEY", "GROK_MODEL", "https://api.x.ai/v1"),
    "bedrock": ProviderConfig("AWS_BEARER_TOKEN_BEDROCK", "BEDROCK_MODEL", "https://bedrock-mantle.us-west-2.api.aws/v1"),
    "deepseek": ProviderConfig("DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "https://api.deepseek.com"),
    "perplexity": ProviderConfig("PERPLEXITY_API_KEY", "PERPLEXITY_MODEL", "https://api.perplexity.ai"),
    "huggingface": ProviderConfig("HF_TOKEN", "HUGGINGFACE_MODEL", "https://router.huggingface.co/v1"),
    "together": ProviderConfig("TOGETHER_AI_API_KEY", "TOGETHER_MODEL", "https://api.together.xyz/v1"),
    "fireworks": ProviderConfig("FIREWORKS_API_KEY", "FIREWORKS_MODEL", "https://api.fireworks.ai/inference/v1"),
    "groq": ProviderConfig("GROQ_API_KEY", "GROQ_MODEL", "https://api.groq.com/openai/v1"),
}

# Model aliases: friendly_name -> {provider: actual_model_name}
MODEL_ALIASES = {
    "openai-gpt-oss-120b": {
        "together": "openai/gpt-oss-120b",
        "fireworks": "accounts/fireworks/models/gpt-oss-120b",
        "groq": "openai/gpt-oss-120b",
    },
    "openai-gpt-oss-20b": {
        "together": "openai/gpt-oss-20b",
        "fireworks": "accounts/fireworks/models/gpt-oss-20b",
        "groq": "openai/gpt-oss-20b",
    },
    "deepseek-v3p2": {
        "fireworks": "accounts/fireworks/models/deepseek-v3p2",
        "together": "deepseek-ai/DeepSeek-V3.2-Exp",
    },
    "Qwen3.5-397B-A17B": {
        "together": "Qwen/Qwen3.5-397B-A17B",
    },
    "Qwen3.5-9B": {
        "together": "Qwen/Qwen3.5-9B",
    },
    "Qwen3-235B-instruct": {
        "together": "Qwen/Qwen3-235B-A22B-Instruct-2507-tput",
        "fireworks": "accounts/fireworks/models/qwen3-235b-a22b-instruct-2507",
    },
    "Qwen3-235B-thinking": {
        "fireworks": "accounts/fireworks/models/qwen3-235b-a22b-thinking-2507",
    },
    "Kimi-K2-Thinking": {
        "together": "moonshotai/Kimi-K2-Thinking",
        "fireworks": "accounts/fireworks/models/kimi-k2-thinking",
    },
    "Kimi-K2-instruct": {
        "together": "moonshotai/Kimi-K2-Instruct-0905",
        "groq": "moonshotai/kimi-k2-instruct-0905",
        "fireworks": "accounts/fireworks/models/kimi-k2-instruct-0905",
    },
    "Kimi-K2.5": {
        "fireworks": "accounts/fireworks/models/kimi-k2p5",
    },
    "nemotron-nano-3-30b": {
        "fireworks": "accounts/fireworks/models/nemotron-nano-3-30b-a3b",
    },
    "glm-4-7": {
        "together": "zai-org/GLM-4.7",
        "fireworks": "accounts/fireworks/models/glm-4p7",
    },
    "glm-5": {
        "together": "zai-org/GLM-5",
        "fireworks": "accounts/fireworks/models/glm-5",
    },
    "minimax-m2.5": {
        "together": "MiniMaxAI/MiniMax-M2.5",
    },
    "llama-3.3-70b-versatile": {
        "groq": "llama-3.3-70b-versatile",
    },
    "llama-3.1-8B": {
        "groq": "llama-3.1-8b-instant",
    },
    "nemotron-super-3-120b": {
        "bedrock": "nvidia.nemotron-super-3-120b",
    },
}


def get_backend(provider: Optional[str], model: Optional[str] = None) -> LLMBackend[Any]:
    """Create a provider-native backend with its resolved model attached."""
    provider_key, model, config, api_key = _resolve_provider_setup(provider=provider, model=model)

    if provider_key == "anthropic":
        backend: LLMBackend[Any] = AnthropicBackend(model=model, api_key=api_key)
    else:
        backend = OpenAICompatibleBackend(
            provider=provider_key,
            model=model,
            api_key=api_key,
            base_url=config.base_url,
        )

    return backend


def get_model_and_client(provider: Optional[str], model: Optional[str] = None) -> Tuple[str, Any]:
    """Compatibility shim returning the underlying provider client.

    Prefer `get_backend()` for all new code.
    """
    backend = get_backend(provider=provider, model=model)
    return backend.model, backend.raw_client


def _resolve_provider_setup(
    *,
    provider: Optional[str],
    model: Optional[str],
) -> tuple[str, str, ProviderConfig, str]:
    if provider is None:
        raise ValueError("provider must be specified (e.g., 'openai', 'anthropic')")

    provider_key = provider.strip().lower()
    if provider_key not in PROVIDER_CONFIGS:
        raise ValueError(f"Unsupported provider: {provider}")

    config = PROVIDER_CONFIGS[provider_key]
    api_key = os.getenv(config.api_key_env)
    if model is None:
        model = os.getenv(config.model_env)

    if model in MODEL_ALIASES and provider_key in MODEL_ALIASES[model]:
        model = MODEL_ALIASES[model][provider_key]

    if not model:
        raise ValueError(f"No model configured for provider: {provider_key}")
    if not api_key:
        raise ValueError(f"Missing API key env var: {config.api_key_env}")

    return provider_key, model, config, api_key
