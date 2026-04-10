"""Centralized default model and provider constants.

Single source of truth for LLM model identifiers used across agents.
Update these when model versions change instead of hunting through files.
"""


# ================================
# --> Default providers
# ================================

DEFAULT_PROVIDER = "anthropic"
WORKER_PROVIDER = "anthropic"
PLANNER_PROVIDER = "gemini"

# ================================
# --> Default models
# ================================

DEFAULT_MODEL = "claude-sonnet-4-6"
STRONG_MODEL = "claude-opus-4-6"
WORKER_MODEL = "claude-sonnet-4-6"
PLANNER_MODEL = "gemini-3.1-pro-preview"

# ================================
# --> Parser fallback chain
# ================================

PARSER_FALLBACK_CHAIN = [
    ("anthropic", "claude-sonnet-4-6"),
    ("openai", "gpt-5.2"),
    ("groq", "moonshotai/kimi-k2-instruct-0905"),
    ("fireworks", "accounts/fireworks/models/gpt-oss-120b"),
    ("together", "Qwen/Qwen3-235B-A22B-Instruct-2507-tput"),
]
