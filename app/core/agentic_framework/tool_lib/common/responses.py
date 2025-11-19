"""Common tool response formatters.

Provides standardized YAML response formatting for all tools.
Follows DRY principle by centralizing response format logic.
"""

import yaml
from typing import Any


def success_response(data: Any) -> str:
    """Format successful tool response as YAML.

    Args:
        data: Result data to return to agent

    Returns:
        YAML string with success=True and data

    Example:
        >>> success_response({"metric": 0.5})
        'success: true\\ndata:\\n  metric: 0.5\\n'
    """
        # Custom representer for multi-line strings to use literal block style
    def str_representer(dumper, data):
        if isinstance(data, str) and '\n' in data:  # Multi-line string
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)
    
    yaml.add_representer(str, str_representer)
    
    return yaml.dump({"success": True, "data": data}, default_flow_style=False)


def error_response(error: str | Exception) -> str:
    """Format error tool response as YAML.

    Args:
        error: Error message or exception

    Returns:
        YAML string with success=False and error message

    Example:
        >>> error_response("Invalid input")
        'success: false\\nerror: Invalid input\\n'
        >>> error_response(ValueError("Bad value"))
        'success: false\\nerror: Bad value\\n'
    """
    error_msg = str(error)
    return yaml.dump({"success": False, "error": error_msg}, default_flow_style=False)
