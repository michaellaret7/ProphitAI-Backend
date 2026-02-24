"""@agent_tool decorator — auto-generates tool schemas from function signatures.

Eliminates the ~30 lines of boilerplate (DESCRIPTION, PARAMETERS, TOOL dict)
required per tool.  The decorator introspects type hints, defaults, docstrings,
and optional ``Param`` / ``Schema`` metadata attached via ``typing.Annotated``
to produce the exact dict shape that ``AgentBase.add_tool(**tool.tool)`` expects.

Usage
-----
Simple (name = function name, description = docstring)::

    @agent_tool
    def calculator(expression: str) -> str:
        \"\"\"Evaluate a math expression.\"\"\"
        ...

Advanced (custom name, Param constraints, Schema injection, Literal enums)::

    @agent_tool(name="portfolio_vol_es")
    @log_simulation_data_range()
    def vol_es(
        portfolio_dict: Annotated[dict, Schema(PORTFOLIO_DICT_SCHEMA)],
        horizon_days: Annotated[int, Param(min_val=1)] = 1,
        method: Literal['param', 'hist'] = 'param',
        *,
        _simulation_date: Optional[datetime] = None,
    ) -> str:
        \"\"\"Calculate portfolio volatility, VaR, and ES.\"\"\"
        ...

Parameters whose names start with ``_`` are automatically hidden from the
generated schema (e.g. ``_simulation_date``).
"""

from __future__ import annotations

import functools
import inspect
import re
from dataclasses import dataclass
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints


# ================================
# --> Helper dataclasses
# ================================

@dataclass(frozen=True)
class Param:
    """Attach to a parameter via ``Annotated[T, Param(...)]`` to add constraints."""

    description: str | None = None
    min_val: float | None = None
    max_val: float | None = None
    enum: list[str] | None = None


@dataclass(frozen=True)
class Schema:
    """Attach to a parameter via ``Annotated[T, Schema({...})]`` to inject a pre-built JSON Schema."""

    schema: dict[str, Any]


# ================================
# --> Helper funcs
# ================================

# Reason: maps Python types to JSON Schema type strings
_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    dict: "object",
    list: "array",
}


# Reason: matches section headers that start a param block we want to parse/strip
_PARAM_SECTION_RE = re.compile(
    r"^(Args|Arguments|Parameters|Params)\s*:?\s*$",
    re.IGNORECASE,
)

# Reason: matches section headers that signal end of param block (Returns, Raises, etc.)
_END_SECTION_RE = re.compile(
    r"^(Returns?|Raises?|Yields?|Examples?|Notes?|See Also)\s*:?\s*$",
    re.IGNORECASE,
)


def _parse_docstring(docstring: str) -> tuple[str, dict[str, str]]:
    """Parse a docstring into (description, {param_name: param_description}).

    Handles Google style (``Args:\\n    param: desc``) and dash-list style
    (``Parameters:\\n- param: desc``).  Only the Args/Parameters section is
    stripped; all other sections (Examples, Returns, Raises, etc.) are kept
    in the description so the LLM can see them.
    """
    lines = docstring.splitlines()
    desc_lines: list[str] = []
    param_descs: dict[str, str] = {}

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        # Reason: found an Args section — parse it and skip its lines
        if _PARAM_SECTION_RE.match(stripped):
            i += 1
            current_param: str | None = None
            current_desc_parts: list[str] = []

            while i < len(lines):
                line = lines[i]
                line_stripped = line.strip()

                # Reason: hit another section header — stop parsing args
                if _PARAM_SECTION_RE.match(line_stripped) or _END_SECTION_RE.match(line_stripped):
                    break

                match = re.match(r"^\s*-?\s*(\w+)\s*:\s*(.*)$", line)
                if match:
                    if current_param is not None:
                        param_descs[current_param] = " ".join(current_desc_parts).strip()
                    current_param = match.group(1)
                    current_desc_parts = [match.group(2)] if match.group(2) else []
                elif current_param is not None and line_stripped:
                    current_desc_parts.append(line_stripped)

                i += 1

            if current_param is not None:
                param_descs[current_param] = " ".join(current_desc_parts).strip()
            continue  # Reason: don't increment i — we're already at the next section

        desc_lines.append(lines[i])
        i += 1

    description = "\n".join(desc_lines).strip()
    return description, param_descs


def _resolve_type(tp: Any) -> tuple[str, dict[str, Any]]:
    """Resolve a Python type hint to a (json_type, extra_schema_fields) pair.

    Handles: primitives, Optional[T], List[str], Literal['a','b'], etc.
    Returns ("string", {}) as the safe fallback.
    """
    origin = get_origin(tp)
    args = get_args(tp)

    # Reason: Literal['param', 'hist'] → string + enum
    if origin is Literal:
        return "string", {"enum": list(args)}

    # Reason: Optional[T] is Union[T, None] — unwrap to T
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _resolve_type(non_none[0])

    # Reason: list[str] / List[str] → array of strings
    if origin is list:
        if args:
            inner_type, _ = _resolve_type(args[0])
            return "array", {"items": {"type": inner_type}}
        return "array", {}

    # Reason: direct primitive lookup
    json_type = _TYPE_MAP.get(tp)
    if json_type:
        return json_type, {}

    return "string", {}


def _extract_annotated_metadata(tp: Any) -> tuple[Any, Param | None, Schema | None]:
    """If ``tp`` is ``Annotated[T, ...]``, extract the base type plus any Param/Schema.

    Returns (base_type, param_or_none, schema_or_none).
    """
    origin = get_origin(tp)

    # Reason: typing.Annotated has __metadata__ on its args
    if origin is not None and hasattr(origin, "__mro__"):
        pass  # not Annotated

    # Reason: Annotated[X, Y, Z] → get_args returns (X, Y, Z)
    try:
        import typing
        if origin is getattr(typing, "Annotated", None):
            args = get_args(tp)
            base = args[0]
            param_meta: Param | None = None
            schema_meta: Schema | None = None
            for meta in args[1:]:
                if isinstance(meta, Param):
                    param_meta = meta
                elif isinstance(meta, Schema):
                    schema_meta = meta
            return base, param_meta, schema_meta
    except Exception:
        pass

    return tp, None, None


def _build_param_schema(
    name: str,
    tp: Any,
    default: Any,
    sig_param: inspect.Parameter,
    docstring_desc: str | None = None,
) -> dict[str, Any] | None:
    """Build the JSON Schema dict for a single parameter. Returns None if hidden."""
    # Reason: params starting with _ are internal-only (e.g. _simulation_date)
    if name.startswith("_"):
        return None

    # Reason: skip *args and **kwargs
    if sig_param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
        return None

    base_type, param_meta, schema_meta = _extract_annotated_metadata(tp)

    # Reason: Schema() provides a complete pre-built dict — use it directly
    if schema_meta is not None:
        return dict(schema_meta.schema)

    json_type, extra = _resolve_type(base_type)
    prop: dict[str, Any] = {"type": json_type}
    prop.update(extra)

    # Reason: Param(description=...) wins, then docstring fallback
    if param_meta is not None and param_meta.description:
        prop["description"] = param_meta.description
    elif docstring_desc:
        prop["description"] = docstring_desc

    # Reason: apply Param constraints (min, max, enum)
    if param_meta is not None:
        if param_meta.min_val is not None:
            prop["minimum"] = param_meta.min_val
        if param_meta.max_val is not None:
            prop["maximum"] = param_meta.max_val
        if param_meta.enum is not None:
            prop["enum"] = param_meta.enum

    # Reason: record default value so the LLM knows the tool's defaults
    if default is not inspect.Parameter.empty:
        prop["default"] = default

    return prop


def _build_tool_dict(func: Any, name: str | None) -> dict[str, Any]:
    """Introspect *func* and return the tool dict expected by AgentBase.add_tool()."""
    tool_name = name or func.__name__
    raw_doc = inspect.getdoc(func) or ""
    description, docstring_params = _parse_docstring(raw_doc)

    hints = get_type_hints(func, include_extras=True)
    sig = inspect.signature(func)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        tp = hints.get(param_name, str)
        prop = _build_param_schema(
            param_name, tp, param.default, param,
            docstring_desc=docstring_params.get(param_name),
        )
        if prop is None:
            continue

        properties[param_name] = prop

        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    parameters: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        parameters["required"] = required
    parameters["additionalProperties"] = False

    return {
        "name": tool_name,
        "description": description,
        "parameters": parameters,
        "function": func,
    }


# ================================
# --> Runtime validation
# ================================

def _extract_validators(
    func: Any,
) -> dict[str, tuple[Param | None, list | None]]:
    """Build a map of runtime validation rules from function type hints.

    Returns:
        {param_name: (param_meta_or_none, literal_values_or_none)}
        Only includes params that have constraints to enforce.
    """
    hints = get_type_hints(func, include_extras=True)
    sig = inspect.signature(func)
    validators: dict[str, tuple[Param | None, list | None]] = {}

    for param_name, param in sig.parameters.items():
        if param_name.startswith("_"):
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        tp = hints.get(param_name)
        if tp is None:
            continue

        base_type, param_meta, schema_meta = _extract_annotated_metadata(tp)

        # Reason: Schema() params use pre-built schemas, no Param constraints
        if schema_meta is not None:
            continue

        literal_values: list | None = None
        if get_origin(base_type) is Literal:
            literal_values = list(get_args(base_type))

        has_param_constraints = param_meta is not None and (
            param_meta.min_val is not None
            or param_meta.max_val is not None
            or param_meta.enum is not None
        )

        if has_param_constraints or literal_values:
            validators[param_name] = (param_meta, literal_values)

    return validators


def _validate_arg(
    param_name: str,
    value: Any,
    param_meta: Param | None,
    literal_values: list | None,
) -> str | None:
    """Validate a single argument against its constraints.

    Returns:
        Error message string if invalid, None if valid.
    """
    # Reason: Optional params may legitimately be None
    if value is None:
        return None

    if literal_values is not None and value not in literal_values:
        return f"'{param_name}' must be one of {literal_values}, got '{value}'"

    if param_meta is not None:
        if param_meta.min_val is not None and value < param_meta.min_val:
            return (
                f"'{param_name}' must be >= {param_meta.min_val}, got {value}"
            )
        if param_meta.max_val is not None and value > param_meta.max_val:
            return (
                f"'{param_name}' must be <= {param_meta.max_val}, got {value}"
            )
        if param_meta.enum is not None and value not in param_meta.enum:
            return (
                f"'{param_name}' must be one of {param_meta.enum}, got '{value}'"
            )

    return None


# ================================
# --> Decorator
# ================================

def agent_tool(func: Any = None, *, name: str | None = None) -> Any:
    """Decorator that attaches a ``.tool`` dict to the decorated function.

    Supports both bare ``@agent_tool`` and parameterised ``@agent_tool(name="x")``
    forms.  Must be the **outermost** decorator when stacked, since it reads
    ``__annotations__`` and ``__doc__`` (preserved by ``@functools.wraps``).

    The decorated function gains a ``.tool`` attribute containing the dict
    expected by ``AgentBase.add_tool(**func.tool)``.
    """
    def _wrap(fn: Any) -> Any:
        tool_dict = _build_tool_dict(fn, name)
        validators = _extract_validators(fn)

        if validators:
            cached_sig = inspect.signature(fn)

            @functools.wraps(fn)
            def _validated(*args: Any, **kwargs: Any) -> Any:
                bound = cached_sig.bind(*args, **kwargs)
                bound.apply_defaults()
                for pname, (p_meta, lit_vals) in validators.items():
                    if pname in bound.arguments:
                        err = _validate_arg(
                            pname, bound.arguments[pname], p_meta, lit_vals,
                        )
                        if err:
                            from app.core.atlas.tools_v2.responses import error_response
                            return error_response(err)
                return fn(*args, **kwargs)

            tool_dict["function"] = _validated
            _validated.tool = tool_dict  # type: ignore[attr-defined]
            return _validated

        # Reason: no constraints to enforce — attach .tool directly, no wrapper needed
        tool_dict["function"] = fn
        fn.tool = tool_dict  # type: ignore[attr-defined]
        return fn

    # Reason: support @agent_tool (no parens) — func is the decorated function itself
    if func is not None:
        return _wrap(func)

    # Reason: support @agent_tool(name="x") — returns the inner wrapper
    return _wrap
