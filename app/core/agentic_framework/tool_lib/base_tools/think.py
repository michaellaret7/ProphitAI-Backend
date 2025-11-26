"""Think tool for BaseAgent v2.

Provides a dedicated space for structured reasoning, analysis, and reflection.
This tool does not retrieve new information or modify state - it simply records
the thought into the conversation history for the model to attend to later.
"""

from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response


def think(thought: str) -> str:
    """Record a structured thought process to the context window.

    Args:
        thought: The content of the thought, reasoning, or plan.

    Returns:
        YAML string with success status and the recorded thought
    """
    try:
        # The tool simply echoes the thought back.
        # This forces the thought into the conversation history (context window)
        # so the model can attend to it in subsequent turns.
        return success_response({
            "thought": thought
        })

    except Exception as e:
        return error_response(str(e))


# Tool schema for agent registration
THINK_DESCRIPTION = """Use this tool to reason, reflect, and think through complex problems. It does NOT
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

**EXAMPLES OF GOOD THINK CALLS:**

Example 1 - Before analysis:
"I need to analyze this 8-stock portfolio for concentration risk. My approach:
1. First check sector/industry breakdown to identify clustering
2. Then examine correlation matrix for hidden relationships
3. Calculate individual position sizes vs prudent limits
4. Synthesize findings into actionable recommendations"

Example 2 - After receiving data:
"The correlation matrix shows NVDA-AMD at 0.85 and MSFT-GOOGL at 0.72. This is concerning because:
- High correlations mean these pairs will move together in drawdowns
- Combined exposure to these correlated pairs is 45% of portfolio
- This effectively reduces diversification benefit
I should recommend either reducing one of each pair or adding uncorrelated assets."

Example 3 - Decision point:
"Weighing two portfolio options:
Option A: Higher expected return (12%) but 0.8 beta and tech-concentrated
Option B: Lower return (9%) but 0.5 beta and sector-diversified

Client is retirement-focused with low risk tolerance. Despite lower returns,
Option B better aligns with mandate. Will recommend B with explanation of trade-off."

Example 4 - Problem solving:
"The factor tilt analysis returned unexpected negative momentum exposure. Let me think through why:
- Check 1: Are any holdings recent IPOs with limited price history? Yes, 2 stocks.
- Check 2: Did any holdings have recent sharp reversals? TSLA down 30% in period.
- Check 3: Is the lookback period appropriate? Using 12mo, maybe 6mo better.
Hypothesis: Recent IPOs and TSLA reversal are skewing momentum calculation. Will
re-run excluding IPOs and note TSLA impact in findings."

**IMPORTANT:** Quality over brevity. A thorough thought that captures your full reasoning is more
valuable than a short note. Include your observations, hypotheses, trade-offs considered, and
conclusions reached."""

THINK_PARAMETERS = {
    "type": "object",
    "properties": {
        "thought": {
            "type": "string",
            "description": (
                "Your reasoning, analysis, reflection, or plan. Be thorough - capture your full "
                "thought process including: observations from data, hypotheses you're forming, "
                "trade-offs you're weighing, decisions and their rationale, or plans for next steps. "
                "This is your space for deep analytical thinking."
            )
        }
    },
    "required": ["thought"]
}

THINK_TOOL = {
    "name": "think",
    "description": THINK_DESCRIPTION,
    "parameters": THINK_PARAMETERS,
    "function": think
}