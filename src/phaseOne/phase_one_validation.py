from __future__ import annotations

"""Phase-One specific JSON parsing and portfolio validation helpers.

Copied from *src/utils/validation.py* so that Phase One no longer relies on a
cross-package utility module.  The implementation remains unchanged aside from
the module path.
"""

from typing import Any, Dict, List
import json
import re
import difflib

from src.utils.file_utils import load_schema_data

# what is this?
__all__ = [
    "parse_json_with_openai",
    "validate_and_fix_allocations",
    "validate_asset_classes",
]


# ---------------------------------------------------------------------------
# JSON extraction helpers
# ---------------------------------------------------------------------------

def parse_json_with_openai(text: str) -> Dict[str, Any]:
    """Extract a JSON object containing a *portfolio* key from a raw LLM string."""

    json_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    for json_str in re.findall(json_pattern, text):
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and "portfolio" in parsed:
                return parsed
        except json.JSONDecodeError:
            continue

    curly_pattern = r"\{[\s\S]*\"portfolio\"[\s\S]*\}"
    for potential in re.findall(curly_pattern, text):
        try:
            parsed = json.loads(potential)
            if isinstance(parsed, dict) and "portfolio" in parsed:
                return parsed
        except json.JSONDecodeError:
            continue

    return {"error": "No valid JSON found", "portfolio": []}


# ---------------------------------------------------------------------------
# Allocation validation / normalisation
# ---------------------------------------------------------------------------

def _to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().strip("%"))
        except ValueError:
            pass
    return 0.0


def validate_and_fix_allocations(
    data: Any, *, min_allocation: float = 1.0, max_allocation: float = 20.0
) -> Dict[str, Any]:
    """Ensure allocations sum to 100 and sit within bounds."""

    if isinstance(data, str):
        data = parse_json_with_openai(data)

    if not isinstance(data, dict) or "portfolio" not in data:
        return {"portfolio": []}

    data = json.loads(json.dumps(data))  # deep-copy
    portfolio: List[Dict[str, Any]] = data["portfolio"]

    for asset in portfolio:
        if "allocation" in asset:
            asset["allocation"] = _to_float(asset["allocation"])

    total = sum(a.get("allocation", 0) for a in portfolio)
    if total and abs(total - 100) > 0.1:
        factor = 100 / total
        for a in portfolio:
            a["allocation"] = round(a.get("allocation", 0) * factor, 1)

    for asset in portfolio:
        alloc = asset.get("allocation", 0.0)
        if alloc < min_allocation:
            asset["allocation"] = min_allocation
        elif alloc > max_allocation:
            asset["allocation"] = max_allocation

    total = sum(a.get("allocation", 0) for a in portfolio)
    if total and abs(total - 100) > 0.1:
        factor = 100 / total
        for a in portfolio:
            a["allocation"] = round(a.get("allocation", 0) * factor, 1)

    return data


# ---------------------------------------------------------------------------
# Asset-class validation
# ---------------------------------------------------------------------------

def validate_asset_classes(data: Dict[str, Any]):
    """Replace invalid *asset_class* values with close matches or 'unknown'."""

    if not data or not isinstance(data, dict) or "portfolio" not in data:
        return data

    schema_data = load_schema_data()
    valid: set[str] = set()

    for sector_name, sector_info in schema_data.items():
        if not isinstance(sector_info, dict) or "schemas" not in sector_info:
            continue
        valid.add(sector_name.lower().replace(" ", "_"))
        for industry_name, industry_info in sector_info.get("schemas", {}).items():
            valid.add(industry_name.lower().replace(" ", "_"))
            for sub_name in industry_info.get("tables", {}).keys():
                valid.add(sub_name.lower().replace(" ", "_"))

    if "etf_data" in schema_data:
        for cat, info in schema_data["etf_data"].get("schemas", {}).items():
            valid.add(cat)
            for etf_type in info.get("tables", {}):
                valid.add(etf_type)

    valid.add("cash")
    valid_list = list(valid)

    for asset in data["portfolio"]:
        cls = asset.get("asset_class")
        if not cls:
            asset["asset_class"] = "unknown"
            continue
        if cls in valid:
            continue
        match = difflib.get_close_matches(cls, valid_list, n=1, cutoff=0.6)
        asset["asset_class"] = match[0] if match else "unknown"

    return data 