"""Reasoning tools for metacognitive analysis and synthesis.

These tools don't call external APIs—they prompt the agent to think deeply
about data it has already gathered.

Philosophy: Enable the agent to pause and reason about information rather than
mechanically executing the next tool call.
"""

from typing import List, Dict, Any, Optional


def synthesize_observations(
    observations: List[str],
    context: str,
    goal: str = "Identify key patterns and form actionable insights"
) -> Dict[str, Any]:
    """Analyze multiple observations together to form insights.

    This is a "reflection tool"—it doesn't fetch new data. Instead, it prompts
    you to synthesize information you've already gathered.

    Use this when:
    - You've run multiple analytical tools and need to connect the dots
    - You have conflicting data points to reconcile
    - You need to form a strategic decision from disparate evidence

    Args:
        observations: List of key observations to synthesize (2-10 items)
        context: What domain/problem these observations relate to
        goal: What you're trying to achieve with this synthesis

    Returns:
        Prompt guiding you to synthesize the observations

    Example:
        synthesize_observations(
            observations=[
                "Portfolio Sharpe ratio is 1.41 (good)",
                "Volatility is 23.6% (elevated)",
                "Correlation matrix shows 0.96 between QQQ-VUG",
                "Top 5 positions represent 53% of portfolio"
            ],
            context="Portfolio risk analysis",
            goal="Identify primary risk drivers and mitigation strategy"
        )
    """
    return {
        "instruction": "Synthesize the following observations",
        "context": context,
        "goal": goal,
        "observations": observations,
        "your_task": (
            "Based on these observations, provide:\n"
            "1. Key Insights: What are the 2-3 most important patterns or findings?\n"
            "2. Causal Relationships: How do these observations connect? What explains what?\n"
            "3. Strategic Implications: What do these findings mean for your goal?\n"
            "4. Recommended Next Steps: What actions or analyses follow from this synthesis?"
        ),
        "success": True
    }


def form_hypothesis(
    hypothesis: str,
    supporting_evidence: List[str],
    test_plan: str
) -> Dict[str, Any]:
    """Form a testable hypothesis and plan how to validate it.

    Use this when:
    - You have a theory about why something is happening
    - You want to test an approach before fully committing
    - You're in an iterative refinement phase

    Args:
        hypothesis: Your hypothesis statement (be specific)
        supporting_evidence: Evidence that led you to this hypothesis
        test_plan: How you'll test this hypothesis

    Returns:
        Confirmation that hypothesis is recorded and test plan is clear

    Example:
        form_hypothesis(
            hypothesis="Removing high-correlation tech stocks will reduce volatility without sacrificing Sharpe ratio",
            supporting_evidence=[
                "QQQ-VUG correlation 0.96 drives portfolio vol",
                "Non-tech defensive stocks have Sharpe >1.2",
                "Portfolio is overweight tech at 45%"
            ],
            test_plan="Build portfolio variant removing VUG, adding defensive stocks; compare metrics"
        )
    """
    return {
        "hypothesis_recorded": hypothesis,
        "supporting_evidence": supporting_evidence,
        "test_plan": test_plan,
        "next_action": "Execute your test plan and evaluate if hypothesis is validated",
        "reminder": (
            "After testing:\n"
            "1. Compare results to your prediction\n"
            "2. If validated: Proceed with confidence\n"
            "3. If rejected: Form a new hypothesis based on what you learned\n"
            "4. If partially validated: Refine hypothesis and test again"
        ),
        "success": True
    }


def reflect_on_strategy(
    current_approach: str,
    results_so_far: List[str],
    remaining_goals: List[str],
    challenges_encountered: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Reflect on your current strategy and decide if adjustment is needed.

    Use this when:
    - You're midway through a multi-step process
    - Results aren't matching expectations
    - You need to decide whether to persist or pivot

    Args:
        current_approach: Description of your current strategy
        results_so_far: What you've accomplished/learned
        remaining_goals: What you still need to achieve
        challenges_encountered: Any obstacles or unexpected findings

    Returns:
        Prompt guiding strategic reflection

    Example:
        reflect_on_strategy(
            current_approach="Removing tech stocks to reduce correlation",
            results_so_far=["Correlation reduced from 0.49 to 0.27", "But Sharpe dropped from 1.41 to 1.02"],
            remaining_goals=["Achieve Sharpe >1.3 while maintaining low correlation"],
            challenges_encountered=["Defensive replacements have lower returns than expected"]
        )
    """
    if challenges_encountered is None:
        challenges_encountered = []

    return {
        "reflection_prompt": "Evaluate your strategy",
        "current_approach": current_approach,
        "results_so_far": results_so_far,
        "remaining_goals": remaining_goals,
        "challenges": challenges_encountered,
        "your_task": (
            "Reflect on your progress and answer:\n"
            "1. Is this approach working? Are you making progress toward goals?\n"
            "2. What's working well? What patterns are emerging?\n"
            "3. What's not working? What obstacles exist?\n"
            "4. Should you persist with current approach, or pivot to a different strategy?\n"
            "5. If pivoting: What alternative approach would you try? Why?\n"
            "6. Next immediate action: What's the next step?"
        ),
        "success": True
    }


def compare_alternatives(
    alternatives: List[Dict[str, str]],
    criteria: List[str],
    context: str
) -> Dict[str, Any]:
    """Compare multiple alternatives against evaluation criteria.

    Use this when:
    - You have multiple candidate solutions
    - Need to make a selection decision
    - Want to explicitly evaluate trade-offs

    Args:
        alternatives: List of alternatives, each with 'name' and 'description'
        criteria: List of criteria to evaluate against
        context: What decision you're making

    Returns:
        Structured comparison framework

    Example:
        compare_alternatives(
            alternatives=[
                {"name": "Portfolio A", "description": "High Sharpe (1.4) but high correlation (0.45)"},
                {"name": "Portfolio B", "description": "Lower Sharpe (1.1) but low correlation (0.25)"},
                {"name": "Portfolio C", "description": "Moderate Sharpe (1.25) and moderate correlation (0.32)"}
            ],
            criteria=["Sharpe ratio", "Correlation", "Sector diversification", "Constraint compliance"],
            context="Selecting optimized portfolio for final output"
        )
    """
    return {
        "decision_context": context,
        "alternatives": alternatives,
        "evaluation_criteria": criteria,
        "your_task": (
            "For each alternative, evaluate against each criterion:\n"
            "1. Score each alternative on each criterion (1-10 scale)\n"
            "2. Identify trade-offs: What does each alternative optimize? What does it sacrifice?\n"
            "3. Consider user constraints and goals\n"
            "4. Make a recommendation with clear justification\n"
            "5. Explain why you chose this alternative over others"
        ),
        "success": True
    }
