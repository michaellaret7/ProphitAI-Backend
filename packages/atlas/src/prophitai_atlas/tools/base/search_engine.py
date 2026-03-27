"""LLM web search tool for agents."""

from typing import Literal, Optional

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_atlas.tools.base.search import PerplexityWebSearch

_perplexity = PerplexityWebSearch()


@agent_tool(name="llm_web_search")
def llm_web_search(
    queries: list[str],
    recency_filter: Optional[Literal["hour", "day", "week", "month", "year"]] = None,
    reasoning_effort: Optional[Literal["minimal", "low", "medium", "high"]] = None,
    mode: Literal["regular-search"] = "regular-search",
) -> str:
    """Search the web via Perplexity for synthesized answers from real-time sources.

Batch multiple queries in a single call for efficiency.

Use for: current news, earnings, analyst opinions, macro data, Fed decisions,
industry trends, or any post-knowledge-cutoff information.

    Args:
        queries: List of search queries. Batch multiple for efficiency.
            (e.g., ["AAPL Q4 earnings", "MSFT Q4 earnings"])
        recency_filter: Filter by recency: hour, day, week, month, or year.
        reasoning_effort: Reasoning depth: minimal, low, medium, or high.
        mode: regular-search (faster).

    Examples:
        llm_web_search(queries=["AAPL Q4 earnings", "MSFT Q4 earnings"], recency_filter="week")
        llm_web_search(queries=["Fed rate decision"], recency_filter="day")
    """
    try:
        results = _perplexity.batch_synthesize_search(
            queries, recency_filter, reasoning_effort, mode
        )
        return success_response(results)
    except Exception as e:
        return error_response(
            f"Error searching the web: {str(e)}. Try again with different search parameters."
        )
