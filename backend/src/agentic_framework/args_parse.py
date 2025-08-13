from backend.src.agentic_framework.base_tools.calculator import calculator
from backend.src.utils.formatting import round_floats_in_object

import inspect
from typing import Any, get_type_hints

def get_arg_info(func):
    sig = inspect.signature(func)
    hints = get_type_hints(func)
    info = []
    for name, p in sig.parameters.items():
        if name == 'self':
            continue
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            kind = p.kind.name
            info.append({
                'name': name,
                'required': False,   # cannot know; varies at runtime
                'default': None if p.default is inspect._empty else p.default,
                'kind': kind,
                'type': str(hints.get(name, Any)),
            })
            continue
        required = (p.default is inspect._empty)
        info.append({
            'name': name,
            'required': required,
            'default': None if p.default is inspect._empty else p.default,
            'kind': p.kind.name,
            'type': str(hints.get(name, Any)),
        })

    return info

