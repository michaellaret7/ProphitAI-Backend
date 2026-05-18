"""Web search via the Parallel AI Search API.

Posts to https://api.parallel.ai/v1beta/search and returns ranked URLs with
extended excerpts, formatted as plain text for direct LLM consumption.
"""

from __future__ import annotations

import os
from typing import Annotated, Literal

import requests

from prophitai_atlas.tools.decorator import Param, agent_tool
from prophitai_atlas.tools.responses import error_response, success_response


# ================================
# --> Constants
# ================================

# Reason: /v1/search rejects processor/max_results/max_chars_per_result; /v1beta accepts them.
ENDPOINT = "https://api.parallel.ai/v1beta/search"

# Reason: 'pro' processor can take 15-60s.
DEFAULT_TIMEOUT = 90

MAX_OUTPUT_CHARS = 16000


# ================================
# --> Helper funcs
# ================================

def _format_results(results: list[dict]) -> str:
    """Format the Parallel AI result list into a single LLM-friendly string."""
    blocks: list[str] = []

    for i, r in enumerate(results, 1):
        title = r.get("title") or "(untitled)"
        url = r.get("url") or "(no url)"
        publish_date = r.get("publish_date") or "n/a"
        excerpts = r.get("excerpts") or []

        header = f"[{i}] {title}\n{url}  (published: {publish_date})"
        body = "\n\n".join(excerpts) if excerpts else "(no excerpts)"

        blocks.append(f"{header}\n{body}")

    output = "\n\n---\n\n".join(blocks)

    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + f"\n\n... [truncated; {len(output) - MAX_OUTPUT_CHARS} more chars]"

    return output


# ================================
# --> Tool
# ================================

@agent_tool(name="web_search")
def web_search(
    objective: Annotated[str, Param(description="Natural-language description of what information you are seeking.")],
    search_queries: Annotated[list[str], Param(description="Keyword queries to dispatch in parallel.")],
    processor: Annotated[Literal["base", "pro"], Param(description="Search tier. 'base' is fast/cheap (2-5s); 'pro' is higher quality (15-60s). Default 'base'.")] = "base",
    max_results: Annotated[int, Param(description="Maximum results to return. Default 5.")] = 5,
    max_chars_per_result: Annotated[int, Param(description="Max characters per excerpt block. Min 100; values over 30000 are not guaranteed. Default 1500.")] = 1500,
) -> str:
    """Web search via the Parallel AI Search API. Returns ranked URLs with extended
page excerpts optimized for LLM consumption.

Use processor='base' (default, 2-5s) for routine queries; processor='pro' (15-60s)
for higher-quality retrieval prioritizing freshness and relevance. Provide a clear
natural-language `objective` describing what you are looking for, plus 1-N keyword
`search_queries` to dispatch in parallel.

    Args:
        objective: Natural-language description of what information you are seeking.
        search_queries: Keyword queries to dispatch in parallel.
        processor: 'base' for fast/cheap, 'pro' for higher quality.
        max_results: Maximum results to return.
        max_chars_per_result: Max characters per excerpt block.
    """
    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        return error_response("PARALLEL_API_KEY environment variable not set.")

    payload = {
        "objective": objective,
        "search_queries": search_queries,
        "processor": processor,
        "max_results": max_results,
        "max_chars_per_result": max_chars_per_result,
    }
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(ENDPOINT, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
    except requests.Timeout:
        return error_response(f"Parallel AI search timed out after {DEFAULT_TIMEOUT}s.")
    except requests.HTTPError as e:
        body = e.response.text[:500] if e.response is not None else ""
        status = e.response.status_code if e.response is not None else "unknown"
        return error_response(f"Parallel AI search returned HTTP {status}: {body}")
    except requests.RequestException as e:
        return error_response(f"Parallel AI search request failed: {type(e).__name__}: {e}")

    data = response.json()
    results = data.get("results") or []

    if not results:
        warnings = data.get("warnings") or []
        suffix = f"  warnings: {warnings}" if warnings else ""
        return error_response(f"[no results]{suffix}")

    return success_response(_format_results(results))
