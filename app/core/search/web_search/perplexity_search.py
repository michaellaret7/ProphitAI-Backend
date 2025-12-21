from perplexity import Perplexity
from dotenv import load_dotenv
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import List, Literal
from app.core.agentic_framework.evaluation.hallucinations.extract_facts import client
from app.utils.choose_model_and_client import get_model_and_client
from app.core.search.utils.clean_text import clean_text
from pydantic import Field

load_dotenv()


class PerplexityWebSearch:
    def __init__(self):
        self._api_key = os.getenv('PERPLEXITY_API_KEY')

    def _get_client(self) -> Perplexity:
        """Create a new sync client for thread-safe parallel execution."""
        return Perplexity(api_key=self._api_key)

    def _format_result(self, result) -> dict:
        """Convert a Pydantic result object to a clean dictionary."""
        return {
            "title": getattr(result, 'title', ''),
            "url": getattr(result, 'url', ''),
            "snippet": getattr(result, 'snippet', ''),
            "date": getattr(result, 'date', ''),
            "last_updated": getattr(result, 'last_updated', '')
        }

    def _deduplicate_results(self, nested_results) -> List[dict]:
        """
        Flatten and deduplicate results from multiple queries based on URL.
        Returns clean dictionaries instead of raw Pydantic objects.
        """
        seen_urls = set()
        unique_results = []

        for query_results in nested_results:
            for result in query_results:
                url = getattr(result, 'url', None)
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(self._format_result(result))

        return unique_results

    def _single_search(
        self,
        query: str,
        recency_filter: Literal["hour", "day", "week", "month", "year"] = None,
        max_results: int = 20,
        search_after_date_filter: str = None,
        search_before_date_filter: str = None,
        search_mode: Literal["web", "academic", "sec"] = None
    ):
        """Execute a single search query using sync client."""
        with self._get_client() as client:
            return client.search.create(
                query=query,
                max_results=max_results,
                max_tokens=500_000,
                max_tokens_per_page=10_000,
                search_recency_filter=recency_filter,
                search_after_date_filter=search_after_date_filter,
                search_before_date_filter=search_before_date_filter,
                search_mode=search_mode
            )

    def batch_search(
        self,
        queries: List[str],
        recency_filter: Literal["hour", "day", "week", "month", "year"] = None,
        max_results_per_query: int = 20,
        search_after_date_filter: str = None,
        search_before_date_filter: str = None,
        search_mode: Literal["web", "academic", "sec"] = None
    ):
        """Execute multiple search queries in parallel using ThreadPoolExecutor."""
        with ThreadPoolExecutor(max_workers=min(len(queries), 5)) as executor:
            futures = [
                executor.submit(
                    self._single_search,
                    query,
                    recency_filter,
                    max_results_per_query,
                    search_after_date_filter,
                    search_before_date_filter,
                    search_mode
                )
                for query in queries
            ]
            results = [f.result() for f in futures]

        cleaned_nested_results = [
            [r for r in result.results] for result in results
        ]
        return self._deduplicate_results(cleaned_nested_results) 

    def _single_synthesize(
        self,
        query: str,
        model: str,
        system_prompt: str,
        search_recency_filter: Literal["hour", "day", "week", "month", "year"] = None,
        reasoning_effort: Literal["minimal", "low", "medium", "high"] = None
    ) -> str:
        """Execute a single LLM-powered search query using sync client."""
        with self._get_client() as client:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                search_recency_filter=search_recency_filter,
                reasoning_effort=reasoning_effort
            )
            content = response.choices[0].message.content
            # Clean results - remove <think> tags
            return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

    def batch_synthesize_search(
        self,
        queries: List[str],
        search_recency_filter: Literal["hour", "day", "week", "month", "year"] = None,
        reasoning_effort: Literal["minimal", "low", "medium", "high"] = None,
        mode: Literal["deep-research", "regular-search"] = "regular-search"
    ) -> List[str]:
        """
        Batch search that synthesizes results using LLM reasoning.
        Uses ThreadPoolExecutor for parallel query execution.

        Args:
            queries: List of search queries to execute
            search_recency_filter: Filter results by recency
            reasoning_effort: Level of reasoning effort for the model
            mode: Search mode - deep-research or regular-search

        Returns:
            List of synthesized search results (one per query)
        """
        if mode == "deep-research":
            model = "sonar-deep-research"
        else:
            model = "sonar-reasoning-pro"

        system_prompt = """
You are an expert research assistant that searches the web for the most relevant and up-to-date information.

Think step by step and be as detailed and thorough as possible in your research, analysis and synthesis:
- Search for the most current and authoritative sources
- Synthesize information from multiple perspectives
- Provide comprehensive coverage of the topic
- Include specific data points, dates, and concrete details
- Cite key findings and insights
- Be analytical and objective in your assessment

Your goal is to deliver a complete, well-researched answer that leaves no important information uncovered."""

        with ThreadPoolExecutor(max_workers=min(len(queries), 3)) as executor:
            futures = [
                executor.submit(
                    self._single_synthesize,
                    query,
                    model,
                    system_prompt,
                    search_recency_filter,
                    reasoning_effort
                )
                for query in queries
            ]
            return [f.result() for f in futures]
    
