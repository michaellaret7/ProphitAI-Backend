"""Tool result validation."""

from typing import Any

import yaml


def validate_tool_result(name: str, args: dict, result: Any) -> dict:
    """Inspect a tool result and produce a unified validation payload.

    Returns a dict with:
        success: True only if the tool reported success AND data is non-empty.
        error:   Reason string when success is False, else None.
        payload: The structured payload {success, tool_name, args, data, error}
                 used for LLM-facing error messages on failure.
    """
    try:
        tool_payload = result if isinstance(result, dict) else yaml.safe_load(result)
    except Exception as e:
        error = f"Tool validation failed: {str(e)}"

        return {
            "success": False,
            "error": error,
            "payload": {
                "success": False,
                "tool_name": name,
                "args": args,
                "error": error,
            },
        }

    reported_success = tool_payload.get("success", False)
    data = tool_payload.get("data")

    payload = {
        "success": reported_success,
        "tool_name": name,
        "args": args,
        "data": data,
        "error": tool_payload.get("error") if not reported_success else None,
    }

    if not reported_success:
        return {
            "success": False,
            "error": payload["error"] or "Unknown error",
            "payload": payload,
        }

    if data is None:
        return {
            "success": False,
            "error": "Tool returned success=True but data is None (no data available)",
            "payload": payload,
        }

    if isinstance(data, (dict, list)) and len(data) == 0:
        return {
            "success": False,
            "error": "Tool returned success=True but data is empty (no data available)",
            "payload": payload,
        }

    if isinstance(data, str) and data.strip() == "":
        return {
            "success": False,
            "error": "Tool returned success=True but data is empty string (no data available)",
            "payload": payload,
        }

    return {"success": True, "error": None, "payload": payload}
