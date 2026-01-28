from __future__ import annotations

import json
import re
from typing import Optional, Tuple

from pydantic import ValidationError

from app.core.atlas.models import Plan
from app.utils.gpt_parser import parse_with_gpt


def _extract_json_from_content(content: str) -> Optional[str]:
    """
    Extract JSON from content that may contain markdown code blocks or prose.

    Tries multiple strategies:
    1. Extract from ```json ... ``` code blocks
    2. Extract from ``` ... ``` code blocks
    3. Find JSON object by matching braces
    """
    # Strategy 1: Extract from ```json ... ``` blocks
    json_block_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if json_block_match:
        return json_block_match.group(1).strip()

    # Strategy 2: Extract from ``` ... ``` blocks
    code_block_match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    # Strategy 3: Find JSON object by matching first { to last }
    first_brace = content.find('{')
    last_brace = content.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return content[first_brace:last_brace + 1]

    return None


def _try_direct_parse(content: str) -> Optional[Plan]:
    """
    Attempt to parse content directly into a Plan without LLM assistance.

    Returns Plan if successful, None otherwise.
    """
    # Try to extract JSON from content
    json_str = _extract_json_from_content(content)
    if not json_str:
        return None

    try:
        # Parse JSON and validate with Pydantic
        data = json.loads(json_str)
        return Plan.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return None


def parse_plan_with_gpt(content: str, system_prompt: Optional[str] = None) -> Tuple[Optional[Plan], Optional[str]]:
    """
    Parse planning content into a Pydantic Plan.

    Strategy:
    1. First attempt direct JSON parsing (fast, no API call)
    2. Fall back to GPT parsing if direct parsing fails

    Returns (plan, error). On success, error is None.
    """
    # Try direct parsing first (faster, no API call needed)
    plan = _try_direct_parse(content)
    if plan is not None:
        return plan, None

    # Fall back to GPT parsing
    try:
        sys_prompt = system_prompt or (
            "Parse the user's planning content into the Plan schema. "
            "If extra prose surrounds the JSON, infer a valid Plan."
        )
        plan = parse_with_gpt(query=content, target_model=Plan, system_prompt=sys_prompt)
        return plan, None
    except Exception as e:
        return None, str(e)
