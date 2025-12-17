from perplexity import BaseModel, Perplexity
from dotenv import load_dotenv
import os
import asyncio
import re
from perplexity import AsyncPerplexity
from typing import List, Literal
from app.core.agentic_framework.evaluation.hallucinations.extract_facts import client
from app.utils.choose_model_and_client import get_model_and_client
from app.core.search.utils.clean_text import clean_text
from pydantic import Field

load_dotenv()

class PerplexityWebSearch:
    def __init__(self):
        self.client = Perplexity(api_key=os.getenv('PERPLEXITY_API_KEY'))
        self.async_client = AsyncPerplexity(api_key=os.getenv('PERPLEXITY_API_KEY'))

    def _deduplicate_results(self, nested_results):
        """
        Flatten and deduplicate results from multiple queries based on URL.
        """
        seen_urls = set()
        unique_results = []
        
        for query_results in nested_results:
            for result in query_results:
                # Basic check for URL existence and uniqueness
                if hasattr(result, 'url') and result.url and result.url not in seen_urls:
                    seen_urls.add(result.url)
                    unique_results.append(result)
        
        return unique_results

    async def batch_search(
        self, 
        queries: List[str], 
        recency_filter: Literal["hour", "day", "week", "month", "year"] = None, 
        max_results_per_query: int = 20,
        search_after_date_filter: str = None,
        search_before_date_filter: str = None,
        search_mode: Literal["web", "academic", "sec"] = None
    ):
        async with self.async_client as client:
            batch_size = 5
            results = []
            
            for i in range(0, len(queries), batch_size):
                batch = queries[i:i + batch_size]
                
                batch_tasks = [
                    client.search.create(
                        query=query, 
                        max_results=max_results_per_query,
                        max_tokens=500_000,
                        max_tokens_per_page=10_000,
                        search_recency_filter=recency_filter,
                        search_after_date_filter=search_after_date_filter,
                        search_before_date_filter=search_before_date_filter,
                        search_mode=search_mode
                    )
                    for query in batch
                ]
                
                batch_results = await asyncio.gather(*batch_tasks)
                results.extend(batch_results)
                
                # Add delay between batches
                if i + batch_size < len(queries):
                    await asyncio.sleep(1000 / 1000)
            
            cleaned_nested_results = [
                [r for r in result.results] for result in results
            ]

            return self._deduplicate_results(cleaned_nested_results) 

    def synthesize_search(
        self, 
        query: str, 
        search_recency_filter: Literal["hour", "day", "week", "month", "year"] = None,
        reasoning_effort: Literal["minimal", "low", "medium", "high"] = None,
        mode: Literal["deep-research", "regular-search"] = "regular-search"
    ):
        if mode == "deep-research":
            model = "sonar-deep-research"
        else:  # mode == "regular-search"
            model = "sonar-reasoning-pro"

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": """
                You are an expert research assistant that searches the web for the most relevant and up-to-date information.

                Think step by step and be as detailed and thorough as possible in your research, analysis and synthesis:
                - Search for the most current and authoritative sources
                - Synthesize information from multiple perspectives
                - Provide comprehensive coverage of the topic
                - Include specific data points, dates, and concrete details
                - Cite key findings and insights
                - Be analytical and objective in your assessment

                Your goal is to deliver a complete, well-researched answer that leaves no important information uncovered."""},
                {"role": "user", "content": query}
            ],
            search_recency_filter=search_recency_filter,
            reasoning_effort=reasoning_effort
        )

        content = response.choices[0].message.content
        # Remove <think>...</think> tags and their content
        cleaned_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        return cleaned_content.strip()
    