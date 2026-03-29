"""Tool validation utilities."""

from typing import Any
import yaml

from prophitai_atlas.tools.responses import dump_yaml


def validate_tool_call(name: str, args: dict, result: Any, agent: Any) -> str:
    """Validate tool execution success and format result for message history."""
    try:
        if isinstance(result, dict):
            tool_payload = result
        else:
            tool_payload = yaml.safe_load(result)

        success = tool_payload.get("success", False)
        data = tool_payload.get("data", {})
        error = tool_payload.get("error") if not success else None

        return dump_yaml({
            "success": success,
            "tool_name": name,
            "args": args,
            "data": data,
            "error": error,
        })

    except Exception as e:
        print(f"Warning: Error validating tool result: {e}")
        return dump_yaml({
            "success": False,
            "error": f"Tool validation failed: {str(e)}",
            "tool_name": name,
            "args": args,
        })
