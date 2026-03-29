"""Theory Research Search Tool - Search investment theory and academic finance research.

Uses hybrid search (semantic + keyword) over academic papers and investment theory
documents covering portfolio theory, factor models, asset pricing, quantitative
strategies, behavioral finance, and market microstructure.
"""

from typing import Annotated

from prophitai_atlas.tools.decorator import agent_tool, Param
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_foundry.retrieval.search import HybridSearch
from prophitai_foundry.models.vector import QueryResult


# ================================
# --> Tools
# ================================

@agent_tool(name="theory_research", category="research")
def theory_research(
    query: str,
    top_k: Annotated[int, Param(min_val=3, max_val=15)] = 7,
) -> str:
    """
    Search investment theory and academic finance research using hybrid semantic + keyword search.

    Use this tool to find information about portfolio construction theory, factor models
    (Fama-French, CAPM, APT), asset pricing, quantitative strategies, risk management
    frameworks, behavioral finance, market microstructure, and academic finance papers.

    CRITICAL - Query Formulation:
    Write detailed, specific natural language queries. The search uses semantic
    embeddings - detailed queries retrieve far better results than keywords.

    GOOD queries (detailed, specific, natural language):
    - "How does the Fama-French five-factor model explain cross-sectional stock returns beyond market beta?"
    - "What are the theoretical foundations of risk parity portfolio construction and how does it compare to mean-variance optimization?"
    - "Academic evidence on momentum factor persistence and crash risk in equity portfolios"
    - "How does Black-Litterman model incorporate investor views into mean-variance optimization?"
    - "Behavioral finance research on loss aversion and its impact on asset pricing and portfolio allocation"

    BAD queries (too vague, keyword-style - DO NOT USE):
    - "Fama French"
    - "portfolio theory"
    - "momentum factor"
    - "CAPM beta"
    - "risk parity"

    Always cite your sources. Example: 'According to Fama and French (1993), the three-factor model captures size and value premiums beyond market risk.'[1]

    Args:
        query: A detailed natural language query describing exactly what investment
            theory or academic research you need. Be specific: include the theory
            or model (CAPM, Black-Litterman, HRP), the topic (factor returns,
            portfolio construction, risk decomposition), and context (empirical
            evidence, mathematical framework, practical application).
            Example: 'What is the theoretical basis for hierarchical risk parity
            and how does it address instability in mean-variance optimization?' NOT: 'HRP theory'
        top_k: Number of results to return (default: 7, max: 15)

    Returns:
        Search results with query, num_results, and results list containing
        id, score, text, doc_id, doc_type, and chunk_id for each match.

    Examples:
        theory_research(query="How does the Black-Litterman model blend market equilibrium with investor views?")
        >>> {"success": True, "data": {"query": "...", "num_results": 7, "results": [...]}}

        theory_research(query="Empirical evidence on low-volatility anomaly in equity markets", top_k=10)
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

    try:
        searcher = HybridSearch(use_rerank=True, enhanced=True)

        results: list[QueryResult] = searcher.search(
            query=query,
            top_k=top_k,
            namespace="theory_research",
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
            "results": formatted_results,
        })

    except ValueError as e:
        return error_response(f"Invalid filter: {str(e)}")
    except RuntimeError as e:
        return error_response(f"Search engine error: {str(e)}")
    except Exception as e:
        return error_response(f"Error searching theory research: {str(e)}")
