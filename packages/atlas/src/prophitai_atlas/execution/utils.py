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
