
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
        end_published_date: str = None,
        start_published_date: str = None,
    ):
        result = self.client.search_and_contents(
            query,
            text=True,
            summary=True,
            type=mode,
            category=doc_type,
            num_results=num_results,
            end_published_date = end_published_date,
            start_published_date = start_published_date,
        )

        # Get initial search results
        search_results = result.results
        urls = [r.url for r in search_results]
        
        # Clean the URLs
        cleaner = ContentCleaner(
            fetchers=[RequestsFetcher(), PlaywrightFetcher()], 
            min_chars=400, 
            min_html_len_for_requests_ok=20000
        )
        cleaned_articles = cleaner.clean_urls(urls)
        
        # Build final results with cleaned content
        final_results = []
        for i, article in enumerate(cleaned_articles):
            if article['quality_score'] > 0.5:
                final_results.append({
                    "title": search_results[i].title,
                    "url": article['url'],
                    "text": article['text'],
                    "quality_score": article['quality_score'],
                    "published_date": search_results[i].published_date if hasattr(search_results[i], 'published_date') else 'N/A'
                })
        
        return final_results


if __name__ == "__main__":
    search = ExaSearch()
    results = search.web_search(
        query="Macro economic research, on ai, ai boom, ai bubble, and other macro economic research. Published by a big bank, reputable research data company, or a hedge fund.", 
        num_results=12,
        end_published_date="2025-12-01",
        start_published_date="2025-01-01",
    )

    for result in results:
        print(f"{'='*80}")
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}")
        print(f"Quality Score: {result['quality_score']}")
        print(f"\nCleaned Content Preview (first 500 chars):")
        print(result['text'][:500] + "...")
        print(f"{'='*80}\n")
