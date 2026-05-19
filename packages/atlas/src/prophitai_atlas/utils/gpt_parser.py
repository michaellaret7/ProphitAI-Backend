"""Ultra simple parser utility for converting natural language into Pydantic models.

Uses OpenRouter's structured-output path via the OpenAI SDK's
`client.beta.chat.completions.parse(response_format=PydanticModel)`.
Routes through `PARSER_MODEL` (a GPT slug known to support JSON-schema mode).
"""

from typing import Dict, List, Type, TypeVar

from pydantic import BaseModel

from prophitai_atlas.models.defaults import PARSER_MODEL
from prophitai_shared import build_client

T = TypeVar("T", bound=BaseModel)


def _call_parser(messages: List[Dict[str, str]], target_model: Type[T]) -> T:
    client, model = build_client(PARSER_MODEL)

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=target_model,
    )

    parsed = completion.choices[0].message.parsed

    if parsed is None:
        raise RuntimeError(f"Parser returned no structured output (model={model})")

    return parsed


def parse_with_gpt(
    query: str,
    target_model: Type[T],
    system_prompt: str = None,
) -> T:
    """Parse natural-language input into a structured Pydantic model.

    Args:
        query: Natural-language input to parse.
        target_model: Pydantic model class to parse into.
        system_prompt: Optional custom system prompt.

    Returns:
        Parsed instance of target_model.
    """
    if system_prompt is None:
        system_prompt = (
            "Parse the user's input into the requested structured format. "
            "Preserve the user's exact wording — do not rephrase, summarize, or rewrite their input. "
            "If information is not provided, leave fields as None/null, do not make up any information."
        )

    return _call_parser(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        target_model,
    )
