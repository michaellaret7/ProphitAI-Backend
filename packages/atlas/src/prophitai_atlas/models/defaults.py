"""Centralized default model constants.

Single source of truth for LLM model identifiers used across agents.
Update these when model versions change instead of hunting through files.

All models route through OpenRouter — slugs follow the
`<provider>/<model>` convention from openrouter.ai/models.
"""


# ================================
# --> Default models (OpenRouter slugs)
# ================================

DEFAULT_MODEL = "anthropic/claude-sonnet-4.6"
STRONG_MODEL = "anthropic/claude-opus-4.7"
WORKER_MODEL = "anthropic/claude-sonnet-4.6"
PLANNER_MODEL = "openai/gpt-5.4"

# Reason: parser path needs guaranteed structured-output support. GPT family
# supports `response_format=PydanticModel` (JSON schema mode) via OpenRouter.
PARSER_MODEL = "openai/gpt-5.4"
