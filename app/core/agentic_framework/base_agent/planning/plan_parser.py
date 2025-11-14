from __future__ import annotations

from typing import Optional, Tuple

from app.core.agentic_framework.base_agent.utils.models import Plan
from app.utils.gpt_parser import parse_with_gpt

def parse_plan_with_gpt(content: str, system_prompt: Optional[str] = None) -> Tuple[Optional[Plan], Optional[str]]:
    """
    Use the OpenAI chat.completions.parse flow (see gpt_parser.parse_with_gpt)
    to convert a planning message's content into a Pydantic Plan.

    Returns (plan, error). On success, error is None.
    """
    try:
        # Provide a parsing-focused system prompt if none supplied
        sys_prompt = system_prompt or (
            "Parse the user's planning content into the Plan schema. "
            "If extra prose surrounds the JSON, infer a valid Plan."
        )
        plan = parse_with_gpt(query=content, target_model=Plan, system_prompt=sys_prompt)
        return plan, None
    except Exception as e:
        return None, str(e)


