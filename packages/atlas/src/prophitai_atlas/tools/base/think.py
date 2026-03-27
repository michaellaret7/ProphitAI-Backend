"""Think tool for structured reasoning."""

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response


@agent_tool(name="think")
def think(thought: str) -> str:
    """Reason, reflect, and plan without retrieving data or modifying state.
Logs your thought into conversation history for subsequent turns.

Use frequently: before multi-step tasks, after receiving tool results,
at decision points, and when synthesizing findings.

    Args:
        thought: Your reasoning, analysis, or plan. Capture observations,
            hypotheses, trade-offs, decisions, and next steps.
    """
    return success_response({"thought": thought})
