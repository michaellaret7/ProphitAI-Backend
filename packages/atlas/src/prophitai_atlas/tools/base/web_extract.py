"""URL content extraction via the Parallel Extract API.

Posts to https://api.parallel.ai/v1/extract. Converts public URLs (including
JavaScript-rendered pages and PDFs) into clean markdown. The natural follow-up
to `web_search`: when an excerpt is promising but truncated, hand the URL to
`web_extract` to read the full article.

Two modes:
- focused (full_content=False, default) — API uses `objective` to pull only
  relevant chunks; lower cost, higher signal-to-noise.
- full (full_content=True) — entire page as markdown; use when chasing
  details or the objective is too broad to pre-filter.
"""

from __future__ import annotations

import os
import uuid
from typing import Annotated, Optional

import requests

from prophitai_atlas.models.defaults import DEFAULT_MODEL
from prophitai_atlas.tools.decorator import Param, agent_tool
from prophitai_atlas.tools.responses import error_response, success_response


# ================================
# --> Constants
# ================================

ENDPOINT = "https://api.parallel.ai/v1/extract"
CLIENT_MODEL = DEFAULT_MODEL

# Reason: full-page extracts of slow sites can take 60s+.
DEFAULT_TIMEOUT = 120

# Reason: API hard limit.
MAX_URLS = 20

# Reason: extracts are deeper than search excerpts; allow more room.
MAX_OUTPUT_CHARS = 24000

FULL_CONTENT_CHAR_CAP = 20000


# ================================
# --> Helper funcs
# ================================

def _format_output(results: list[dict], errors: list[dict], full_content: bool) -> str:
    """Format the Parallel AI extract results into a single LLM-friendly string."""
    blocks: list[str] = []

    for i, r in enumerate(results, 1):
        title = r.get("title") or "(untitled)"
        url = r.get("url") or "(no url)"
        publish_date = r.get("publish_date") or "n/a"

        header = f"[{i}] {title}\n{url}  (published: {publish_date})"

        if full_content and r.get("full_content"):
            body = r["full_content"]
        else:
            excerpts = r.get("excerpts") or []
            body = "\n\n".join(excerpts) if excerpts else "(no excerpts)"

        blocks.append(f"{header}\n{body}")

    output = "\n\n---\n\n".join(blocks)

    if errors:
        err_lines = [
            f"  - {e.get('url', '?')} ({e.get('error_type', '?')}, http={e.get('http_status_code', '?')})"
            for e in errors
        ]
        output += "\n\nerrors:\n" + "\n".join(err_lines)

    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + f"\n\n... [truncated; {len(output) - MAX_OUTPUT_CHARS} more chars]"

    return output


# ================================
# --> Tool
# ================================

@agent_tool(name="web_extract")
def web_extract(
    urls: Annotated[list[str], Param(description="1-20 public URLs to extract. JS-heavy pages and PDFs are supported.")],
    objective: Annotated[Optional[str], Param(description="Natural-language description of what you are looking for on these pages. When set, the API returns excerpts focused on this objective (ignored if full_content=True).")] = None,
    full_content: Annotated[bool, Param(description="If True, returns the entire page as markdown instead of focused excerpts. Use when the objective is too broad to pre-filter, or when you need details beyond what excerpts surface. Default False.")] = False,
    max_chars_per_result: Annotated[int, Param(description="Max characters per excerpt block. Values below 1000 are floored to 1000 by the API. Default 4000.")] = 4000,
) -> str:
    """Fetch and extract URL content via the Parallel Extract API. Returns clean
markdown — either focused excerpts aligned to `objective` (default) or the
full page when `full_content=True`. Handles JavaScript-rendered pages and
PDFs. Use this after `web_search` when an excerpt isn't enough to answer
the question.

    Args:
        urls: 1-20 public URLs to extract.
        objective: Natural-language description of what to look for on the pages.
        full_content: If True, return entire page markdown instead of excerpts.
        max_chars_per_result: Max characters per excerpt block.
    """
    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        return error_response("PARALLEL_API_KEY environment variable not set.")

    if not urls:
        return error_response("urls is empty.")

    if len(urls) > MAX_URLS:
        return error_response(f"Max {MAX_URLS} urls per request, got {len(urls)}.")

    advanced: dict = {
        "excerpt_settings": {"max_chars_per_result": max_chars_per_result},
    }

    if full_content:
        advanced["full_content"] = {"max_chars_per_result": FULL_CONTENT_CHAR_CAP}

    payload: dict = {
        "urls": urls,
        "client_model": CLIENT_MODEL,
        "session_id": uuid.uuid4().hex,
        "advanced_settings": advanced,
    }

    if objective:
        payload["objective"] = objective

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(ENDPOINT, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
    except requests.Timeout:
        return error_response(f"Parallel AI extract timed out after {DEFAULT_TIMEOUT}s.")
    except requests.HTTPError as e:
        body = e.response.text[:500] if e.response is not None else ""
        status = e.response.status_code if e.response is not None else "unknown"
        return error_response(f"Parallel AI extract returned HTTP {status}: {body}")
    except requests.RequestException as e:
        return error_response(f"Parallel AI extract request failed: {type(e).__name__}: {e}")

    data = response.json()
    results = data.get("results") or []
    errors = data.get("errors") or []

    if not results and not errors:
        warnings = data.get("warnings") or []
        suffix = f"  warnings: {warnings}" if warnings else ""
        return error_response(f"[no results]{suffix}")

    # Reason: if every URL failed, surface as a tool error so the execution-loop
    # validator routes it correctly and the LLM doesn't treat the empty payload
    # as a successful retrieval.
    if not results and errors:
        err_lines = [
            f"{e.get('url', '?')} ({e.get('error_type', '?')}, http={e.get('http_status_code', '?')})"
            for e in errors
        ]
        return error_response("All URLs failed:\n" + "\n".join(err_lines))

    return success_response(_format_output(results, errors, full_content))
