"""Model/client resolver for base_agent."""

from typing import Optional, Tuple, Any

from app.utils.choose_model_and_client import (
    openai_model_and_client,
    claude_model_and_client,
    deepseek_model_and_client,
    grok_model_and_client,
    perplexity_model_and_client,
    huggingface_model_and_client,
    gemini_model_and_client,
    together_model_and_client,
)


def resolve_llm_and_client(
    *, provider: Optional[str], model: Optional[str]
) -> Tuple[Optional[str], Any]:
    """
    Decide which model/client factory to call based on provider and model.

    Args:
        provider: Which LLM provider to use (e.g., "openai", "anthropic").
        model: Optional explicit model name to override defaults.

    Returns:
        (model_name, client) tuple appropriate for the selected provider.

    Raises:
        ValueError: If provider is unsupported or missing.
    """

    if provider is None:
        raise ValueError("provider must be specified (e.g., 'openai', 'anthropic')")

    provider_key = provider.strip().lower()

    if provider_key == "openai":
        return openai_model_and_client(model=model)
    if provider_key == "anthropic":
        return claude_model_and_client(model=model)
    if provider_key == "deepseek":
        return deepseek_model_and_client(model=model)
    if provider_key == "grok":
        return grok_model_and_client(model=model)
    if provider_key == "perplexity":
        return perplexity_model_and_client(model=model)
    if provider_key in ("huggingface", "openai_hf", "hf"):
        return huggingface_model_and_client(model=model)
    if provider_key == "gemini":
        return gemini_model_and_client(model=model)
    if provider_key in ("together", "together_ai"):
        if model == "openai-gpt-oss-120b" or model == "openai/gpt-oss-120b":
            model = "openai/gpt-oss-120b"
        elif model == "Qwen3-235B-Instruct":
            model = "Qwen/Qwen3-235B-A22B-Instruct-2507-tput"
        elif model == "Qwen3-80B-A3B-Thinking":
            model = "Qwen/Qwen3-Next-80B-A3B-Thinking"
        elif model == "Kimi-K2-Thinking":
            model = "moonshotai/Kimi-K2-Thinking"
        elif model == "Kimi-K2-Instruct":
            model = "moonshotai/Kimi-K2-Instruct-0905"
        elif model == "meta-llama-4-maverick":
            model = "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"
        elif model == "meta-llama-4-scout":
            model = "meta-llama/Llama-4-Scout-17B-16E-Instruct"
        elif model == "ministral-3-14B":
            model = "mistralai/Ministral-3-14B-Instruct-2512"
        return together_model_and_client(model=model)

    raise ValueError(f"Unsupported provider: {provider}")

