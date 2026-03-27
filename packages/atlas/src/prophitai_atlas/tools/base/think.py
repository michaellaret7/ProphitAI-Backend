"""Think tool for structured reasoning."""

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response


@agent_tool(name="think")
def think(thought: str) -> str:
    """Use this tool to reason, reflect, and think through complex problems. It does NOT
retrieve new information or modify any state - it simply logs your thought into the conversation
history so you can build upon it in subsequent turns.

**USE THIS TOOL FREQUENTLY.** High-quality analytical work requires structured thinking. The best
analysts pause to reason through problems rather than rushing to conclusions.

**WHEN TO USE (call this tool liberally):**

Before Analysis:
- Before starting a complex multi-step task, think through your approach
- When you need to break down a problem into components
- To plan which tools to use and in what sequence

During Analysis:
- After receiving tool results, think about what they mean and implications
- When you see unexpected or contradictory data, reason through possible explanations
- To synthesize findings across multiple data sources
- When weighing trade-offs between different options (stocks, allocations, strategies)

Decision Points:
- Before making portfolio allocation decisions
- When evaluating competing investment theses
- To assess risk/reward trade-offs
- Before finalizing recommendations

Problem Solving:
- When you encounter errors or unexpected results
- To brainstorm multiple approaches to a problem
- To evaluate which solution is simplest and most effective
- When debugging why an analysis isn't producing expected results

Reflection:
- To check if your reasoning is sound before proceeding
- To identify gaps in your analysis that need filling
- To question assumptions you've been making
- To consolidate learnings before moving to the next phase

**PARAMETER CONSTRAINT:** This tool accepts EXACTLY ONE parameter: "thought" (string).
Do NOT pass any other parameters.

    Args:
        thought: Your reasoning, analysis, reflection, or plan. Be thorough - capture your full
            thought process including: observations from data, hypotheses you're forming,
            trade-offs you're weighing, decisions and their rationale, or plans for next steps.
    """
    return success_response({"thought": thought})
