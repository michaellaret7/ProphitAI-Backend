
from __future__ import annotations

from exa_py import Exa
from dotenv import load_dotenv
import os
from typing import Literal
from app.core.search.utils.clean_articles import ContentCleaner, RequestsFetcher, PlaywrightFetcher

load_dotenv()

class ExaSearch:
    def __init__(self):
        self.client = Exa(api_key=os.getenv('EXA_API_KEY'))

    def web_search(
        self,
        query: str,
        mode: Literal["auto", "fast", "deep"] = "auto",
        doc_type: Literal["company", "research paper", "news article", "pdf", "github", "tweet", "personal site", "people", "financial report"] = None,
        num_results: int = 2,
        end_published_date: str = "2025-12-18T04:59:59.999Z",
        start_published_date: str = "2025-11-17T05:00:00.000Z",
    ):
        result = self.client.search_and_contents(
            query,
            text=True,
            summary=True,
            type=mode,
            category=doc_type,
            num_results=num_results,
            end_published_date = "2025-12-18T04:59:59.999Z",
            start_published_date = "2025-11-17T05:00:00.000Z",
        )

        final_results = []
        for result in result.results:
            final_results.append({
                "title": result.title,
                "url": result.url,
                "summary": result.summary,
                "published_date": result.published_date if hasattr(result, 'published_date') else 'N/A'
            })

        return final_results


