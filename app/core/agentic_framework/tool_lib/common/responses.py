"""Common tool response formatters.

Provides standardized YAML response formatting for all tools.
Follows DRY principle by centralizing response format logic.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import yaml

_LONG_STRING_THRESHOLD = 200
_YAML_WIDTH = 10_000


class _ToolResponseDumper(yaml.SafeDumper):
    pass


def _str_representer(dumper: yaml.Dumper, value: str):
    if "\n" in value or len(value) > _LONG_STRING_THRESHOLD:
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


def _unknown_representer(dumper: yaml.Dumper, value: Any):
    if hasattr(value, "model_dump"):
        try:
            return dumper.represent_data(value.model_dump())
        except Exception:
            pass

    if hasattr(value, "dict") and callable(getattr(value, "dict")):
        try:
            return dumper.represent_data(value.dict())
        except Exception:
            pass

    try:
        if dataclasses.is_dataclass(value):
            return dumper.represent_data(dataclasses.asdict(value))
    except Exception:
        pass

    return dumper.represent_scalar("tag:yaml.org,2002:str", str(value))


_ToolResponseDumper.add_representer(str, _str_representer)
_ToolResponseDumper.add_multi_representer(object, _unknown_representer)


def dump_yaml(payload: Any) -> str:
    return yaml.dump(
        payload,
        Dumper=_ToolResponseDumper,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=_YAML_WIDTH,
    )


def success_response(data: Any) -> str:
    """Format successful tool response as YAML."""
    return dump_yaml({"success": True, "data": data})


def error_response(error: str | Exception) -> str:
    """Format error tool response as YAML."""
    return dump_yaml({"success": False, "error": str(error)})
