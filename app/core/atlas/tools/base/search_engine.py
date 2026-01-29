"""Search engine tools for agents."""

from typing import List, Literal

from app.core.atlas.tools.responses import success_response, error_response
from app.core.search.web_search.perplexity_search import PerplexityWebSearch


class AgentSearchEngine:
    def __init__(self):
        self.perplexity = PerplexityWebSearch()

    def web_search(
        self,
        queries: List[str],
        recency_filter: Literal["hour", "day", "week", "month", "year"] = None,
        max_results_per_query: int = 20,
        search_after_date_filter: str = None,
        search_before_date_filter: str = None
    ) -> dict:
        """Execute batch web search with parallel query execution."""
        try:
            results = self.perplexity.batch_search(
                queries,
                recency_filter,
                max_results_per_query,
                search_after_date_filter,
                search_before_date_filter
            )
            return success_response(results)
        except Exception as e:
            return error_response(f"Error executing web search: {str(e)}. Try again with different queries or parameters.")

    def llm_web_search(
        self,
        queries: List[str],
        recency_filter: Literal["hour", "day", "week", "month", "year"] = None,
        reasoning_effort: Literal["minimal", "low", "medium", "high"] = None,
        mode: Literal["deep-research", "regular-search"] = "regular-search"
    ) -> dict:
        """Use LLM to search the web and synthesize results with parallel query execution."""
        try:
            results = self.perplexity.batch_synthesize_search(
                queries,
                recency_filter,
                reasoning_effort,
                mode
            )
            return success_response(results)
        except Exception as e:
            return error_response(f"Error searching the web: {str(e)}. Try again with different search parameters.")


LLM_WEB_SEARCH_DESCRIPTION = """Search the web using Perplexity's AI-powered search engine to get synthesized,
well-researched answers based on real-time sources.

**BATCH MULTIPLE QUERIES FOR EFFICIENCY:**
This tool accepts a LIST of queries. When researching multiple topics, batch them together
in a single call rather than making separate calls.

Good: queries: ["AAPL Q4 earnings", "MSFT Q4 earnings", "GOOGL Q4 earnings"]
Bad: Three separate calls with one query each

**USE THIS TOOL WHEN YOU NEED:**
- Current market news, earnings reports, or company announcements
- Recent analyst opinions, price targets, or rating changes
- Macroeconomic data, Fed decisions, or policy changes
- Industry trends, competitive dynamics, or sector developments
- Any information that may have changed since your knowledge cutoff

**QUERY TIPS:**
- Be specific: "NVIDIA Q4 2024 earnings results and guidance" vs "NVIDIA earnings"
- Include context: "Fed interest rate decision December 2024 and market impact"
- Specify what you want: "Analyst consensus price target for Apple as of January 2025"

**PARAMETERS:**

queries (REQUIRED - array): List of search queries. Batch multiple for efficiency.

recency_filter: Constrains results to a time window:
  - "hour": Breaking news, intraday moves
  - "day": Today's news
  - "week": Recent developments (good default)
  - "month": Quarterly trends
  - "year": Annual comparisons

reasoning_effort: Controls depth vs speed:
  - "minimal": Quick facts
  - "low": Standard queries
  - "medium": Balanced (good default)
  - "high": Complex topics

mode: Search depth:
  - "regular-search": Standard, faster (default)
  - "deep-research": Comprehensive, slower

**EXAMPLES:**

Example 1 - Batch earnings research:
  queries: ["Microsoft Q4 2024 earnings", "Apple Q4 2024 earnings", "Google Q4 2024 earnings"]
  recency_filter: "week"

Example 2 - Single breaking news:
  queries: ["Fed interest rate decision and Powell comments"]
  recency_filter: "day"

Example 3 - Deep competitive research:
  queries: ["NVIDIA vs AMD datacenter GPU market share 2024", "AI chip competitive landscape"]
  reasoning_effort: "high"
  mode: "deep-research" """

LLM_WEB_SEARCH_PARAMETERS = {
    "type": "object",
    "properties": {
        "queries": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "List of search queries. BATCH MULTIPLE QUERIES for efficiency. "
                "Example: [\"AAPL Q4 earnings\", \"MSFT Q4 earnings\"]"
            )
        },
        "recency_filter": {
            "type": "string",
            "enum": ["hour", "day", "week", "month", "year"],
            "description": "Filter by recency: hour, day, week, month, or year."
        },
        "reasoning_effort": {
            "type": "string",
            "enum": ["minimal", "low", "medium", "high"],
            "description": "Reasoning depth: minimal, low, medium, or high."
        },
        "mode": {
            "type": "string",
            "enum": ["regular-search", "deep-research"],
            "default": "regular-search",
            "description": "regular-search (faster) or deep-research (thorough)."
        }
    },
    "required": ["queries"]
}
