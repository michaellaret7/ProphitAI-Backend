"""Trading Strategy Research Tool - Search trading strategy research and documentation.

Uses hybrid search (semantic + keyword) over trading strategy research documents
covering equity strategies, factor-based approaches, anomaly research, and
systematic trading methodologies stored in Pinecone.
"""

from typing import Annotated, Optional

from prophitai_atlas.tools.decorator import agent_tool, Param
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_foundry.retrieval.search import HybridSearch
from prophitai_foundry.models.vector import QueryResult


# ================================
# --> Tools
# ================================

@agent_tool(name="strategy_research", category="research")
def strategy_research(
    query: str,
    top_k: Annotated[int, Param(min_val=3, max_val=15)] = 7,
    strategy_type: Optional[str] = None,
    asset_class: Optional[str] = None,
) -> str:
    """
    Search trading strategy research using hybrid semantic + keyword search.

    Use this tool to find information about trading strategies, factor-based investing,
    market anomalies, systematic trading approaches, backtesting results, signal
    construction, and strategy implementation details.

    CRITICAL - Query Formulation:
    Write detailed, specific natural language queries. The search uses semantic
    embeddings - detailed queries retrieve far better results than keywords.

    GOOD queries (detailed, specific, natural language):
    - "How does the accruals anomaly work in equity markets and what are the key signals for detecting earnings manipulation?"
    - "What is the evidence for momentum strategy profitability after accounting for transaction costs and market impact?"
    - "How do mean-reversion strategies perform in different volatility regimes and what are optimal holding periods?"
    - "What are the best systematic approaches for capturing the value premium using fundamental signals?"
    - "How does statistical arbitrage using pairs trading work and what cointegration tests are most reliable?"

    BAD queries (too vague, keyword-style - DO NOT USE):
    - "accruals anomaly"
    - "momentum strategy"
    - "mean reversion"
    - "pairs trading"
    - "value factor"

    Always cite your sources when presenting findings from strategy research.

    Args:
        query: A detailed natural language query describing exactly what trading
            strategy research you need. Be specific: include the strategy type
            (momentum, mean-reversion, statistical arbitrage), the asset class
            (equity, fixed income, commodities), and context (backtesting results,
            signal construction, implementation details, risk characteristics).
            Example: 'What is the empirical evidence for the accruals anomaly
            in equity markets and how is it constructed as a trading signal?' NOT: 'accruals anomaly'
        top_k: Number of results to return (default: 7, max: 15)
        strategy_type: Optional filter for strategy type (e.g., 'general', 'momentum', 'mean_reversion')
        asset_class: Optional filter for asset class (e.g., 'equity', 'fixed_income', 'commodities')

    Returns:
        Search results with query, num_results, filters_applied, and results list
        containing id, score, text, doc_id, doc_type, and chunk_id for each match.

    Examples:
        strategy_research(query="How does the accruals anomaly signal work for equity trading?")
        >>> {"success": True, "data": {"query": "...", "num_results": 7, "results": [...]}}

        strategy_research(query="Evidence on momentum crashes and tail risk in systematic strategies", top_k=10)
        >>> {"success": True, "data": {"query": "...", "num_results": 10, "results": [...]}}

    Raises:
        ValueError: If query is empty
    """
    if not query or not isinstance(query, str):
        return error_response("Query is required and must be a non-empty string")

    query = query.strip()
    if not query:
        return error_response("Query cannot be empty or whitespace only")

    if not isinstance(top_k, int) or top_k < 1:
        return error_response("top_k must be a positive integer")
    top_k = min(top_k, 25)

    filters: dict = {}
    if strategy_type:
        filters["strategy_type"] = strategy_type
    if asset_class:
        filters["asset_class"] = asset_class

    try:
        searcher = HybridSearch(use_rerank=True, enhanced=True)

        results: list[QueryResult] = searcher.search(
            query=query,
            top_k=top_k,
            namespace="trading_strategies",
            **filters,
        )

        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": round(result.score, 4),
                "text": result.metadata.get("text", ""),
                "doc_id": result.metadata.get("doc_id"),
                "doc_type": result.metadata.get("doc_type"),
                "chunk_id": result.metadata.get("chunk_id"),
            })

        return success_response({
            "query": query,
            "num_results": len(formatted_results),
            "filters_applied": filters if filters else None,
            "results": formatted_results,
        })

    except ValueError as e:
        return error_response(f"Invalid filter: {str(e)}")
    except RuntimeError as e:
        return error_response(f"Search engine error: {str(e)}")
    except Exception as e:
        return error_response(f"Error searching strategy research: {str(e)}")
