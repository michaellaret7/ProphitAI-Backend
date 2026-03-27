"""
Ultra simple parser utility for converting data to Pydantic models.
"""
from typing import Type, TypeVar, Dict, List
from pydantic import BaseModel
from prophitai_shared.choose_model_and_client import get_model_and_client
from openai import RateLimitError, APIError, AuthenticationError, InternalServerError
from prophitai_atlas.models.defaults import PARSER_FALLBACK_CHAIN

T = TypeVar('T', bound=BaseModel)

def _call_parser_with_fallback(messages: List[Dict[str, str]], target_model: Type[T]) -> T:
    providers = PARSER_FALLBACK_CHAIN

    last_error = None

    for provider, model_name in providers:
        try:

            model, client = get_model_and_client(provider, model_name)

            # Reason: bypass langfuse class-level monkey-patch on Completions.parse
            parse_method = type(client.chat.completions).parse
            original_parse = getattr(parse_method, '__wrapped__', parse_method)
            completion = original_parse(
                client.chat.completions,
                model=model,
                messages=messages,
                response_format=target_model,
            )
            return completion.choices[0].message.parsed

        except (RateLimitError, APIError, AuthenticationError, InternalServerError) as e:
            print(f"[GPT Parser] {provider}/{model_name} failed: {e}, trying next...")
            last_error = e
            continue

    raise RuntimeError(f"All parser providers failed. Last error: {last_error}")

def parse_with_gpt(
    query: str,
    target_model: Type[T],
    system_prompt: str = None
) -> T:
    """
    Generic LLM parser that converts natural language to structured Pydantic models.

    Args:
        query: Natural language input to parse
        target_model: Pydantic model class to parse into
        system_prompt: Optional custom system prompt (default provides generic instructions)

    Returns:
        Parsed instance of target_model
    """

    if system_prompt is None:
        system_prompt = """Parse the user's input into the requested structured format.
        Preserve the user's exact wording — do not rephrase, summarize, or rewrite their input.
        If information is not provided, leave fields as None/null, do not make up any information."""

    parsed = _call_parser_with_fallback([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ], target_model)

    return parsed
