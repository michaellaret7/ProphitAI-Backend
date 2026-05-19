"""Constructors for chat-completion message dicts.

Plain dicts in the exact shape the OpenAI SDK expects on the wire — no
wrapper types, no flattening step. Provider-specific prompt caching is
opted into via `cached_text`, which OpenRouter forwards to upstream
caching (Anthropic explicit, Gemini explicit, etc.). Models without
caching support silently drop the field.
"""

from __future__ import annotations

from typing import Any, Dict, List


# ================================
# --> Content helpers
# ================================


def cached_text(text: str) -> List[Dict[str, Any]]:
    """Wrap text as a content-parts list with an Anthropic-style cache breakpoint."""
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


# ================================
# --> Message constructors
# ================================


def system_msg(content: str, *, cache: bool = False) -> Dict[str, Any]:
    return {"role": "system", "content": cached_text(content) if cache else content}


def user_msg(content: str) -> Dict[str, Any]:
    return {"role": "user", "content": content}


def assistant_msg(content: str, tool_calls: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    msg: Dict[str, Any] = {"role": "assistant", "content": content}

    if tool_calls:
        msg["tool_calls"] = tool_calls

    return msg


def tool_msg(tool_call_id: str, content: str) -> Dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }


# ================================
# --> Rolling cache breakpoint
# ================================


def refresh_rolling_cache_breakpoint(messages: List[Dict[str, Any]]) -> None:
    """Move the rolling cache_control marker to the last assistant/tool message.

    Strips any prior marker on assistant/tool messages first, then attaches one
    to the latest. Combined with the system anchor set via `system_msg(cache=True)`,
    this keeps the total breakpoint count at 2 — well under Anthropic's hard
    limit of 4. The system message's marker is not touched here.

    Idempotent — safe to call before every LLM request.
    """
    for m in messages:
        if m["role"] not in ("assistant", "tool"):
            continue

        content = m.get("content")

        if isinstance(content, list) and content and "text" in content[0]:
            m["content"] = content[0]["text"]

    for m in reversed(messages):
        if m["role"] not in ("assistant", "tool"):
            continue

        content = m.get("content")

        if isinstance(content, str) and content:
            m["content"] = cached_text(content)
            return
