"""Execution utilities for the ExecutionLoop.

Contains helper functions for tool result processing.
"""

import dataclasses
import json
from typing import Any


def stringify_for_llm(obj: Any) -> str:
    """Convert any object to string for LLM consumption."""
    if isinstance(obj, str):
        return obj
    try:
        def default_handler(o):
            if hasattr(o, 'model_dump'):
                return o.model_dump()
            if hasattr(o, 'dict'):
                return o.dict()
            if dataclasses.is_dataclass(o) and not isinstance(o, type):
                return dataclasses.asdict(o)
            return str(o)
        return json.dumps(obj, default=default_handler, ensure_ascii=False)
    except Exception:
        return str(obj)


def check_tool_success(tool_validation_dict: dict) -> tuple[bool, str | None]:
    """Check if a tool call was successful."""
    success = tool_validation_dict.get("success", True)
    if not success:
        return False, tool_validation_dict.get("error", "Unknown error")
    data = tool_validation_dict.get("data")
    if data is None:
        return False, "Tool returned success=True but data is None (no data available)"
    if isinstance(data, (dict, list)) and len(data) == 0:
        return False, "Tool returned success=True but data is empty (no data available)"
    if isinstance(data, str) and data.strip() == "":
        return False, "Tool returned success=True but data is empty string (no data available)"
    return True, None
