"""Configuration-driven LLM provider client factory."""

import os
from dataclasses import dataclass
from typing import Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv
from langfuse.openai import openai

load_dotenv()

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
    "Qwen3.5-397B-A17B":{
        "together": "Qwen/Qwen3.5-397B-A17B",
    },
    "Qwen3.5-9B":{
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
    "Kimi-K2.5" :{
        "fireworks": "accounts/fireworks/models/kimi-k2p5",
    },
    "nemotron-nano-3-30b": {
        "fireworks": "accounts/fireworks/models/nemotron-nano-3-30b-a3b",
    },
    "glm-4-7": {
        "together": "zai-org/GLM-4.7",
        "fireworks": "accounts/fireworks/models/glm-4p7"
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
}

def get_model_and_client(provider: Optional[str], model: Optional[str] = None) -> Tuple[str, OpenAI]:
    """Create a model name and OpenAI-compatible client for any supported provider."""
    if provider is None:
        raise ValueError("provider must be specified (e.g., 'openai', 'anthropic')")

    provider_key = provider.strip().lower()

    if provider_key not in PROVIDER_CONFIGS:
        raise ValueError(f"Unsupported provider: {provider}")

    config = PROVIDER_CONFIGS[provider_key]

    api_key = os.getenv(config.api_key_env)
    if model is None:
        model = os.getenv(config.model_env)

    # Apply model aliases (friendly_name -> provider-specific name)
    if model in MODEL_ALIASES and provider_key in MODEL_ALIASES[model]:
        model = MODEL_ALIASES[model][provider_key]

    client_kwargs = {"api_key": api_key}
    if config.base_url:
        client_kwargs["base_url"] = config.base_url

    # Wrap the openai client with the langfuse openai client.
    return model, openai.OpenAI(**client_kwargs)
