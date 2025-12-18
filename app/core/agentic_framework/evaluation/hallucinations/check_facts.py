from app.core.search.web_search.exa_search import ExaSearch
from pydantic import BaseModel, Field
from typing import Literal, List
from app.utils.choose_model_and_client import get_model_and_client
import asyncio
import logging
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class ClaimAssessment(BaseModel):
    claim: str = Field(description="The claim being assessed")
    assessment: Literal["supported", "refuted", "Insufficient information"] = Field(
        description="Whether the claim is supported, refuted, or there is insufficient information"
    )
    confidence_score: float = Field(
        ge=0.0, 
        le=1.0, 
        description="Confidence score between 0 and 1 (1 = fully confident the claim is true, 0 = fully confident the claim is false)"
    )
    correct_information: str = Field(
        default="",
        description="If the claim is refuted, provide the correct information from the sources. If supported or insufficient information, leave empty."
    )
    supporting_sources: List[str] = Field(
        default_factory=list,
        description="List of sources that support the claim"
    )
    refuting_sources: List[str] = Field(
        default_factory=list,
        description="List of sources that refute the claim"
    )

def _create_insufficient_info_assessment(claim: str, error_msg: str = "") -> ClaimAssessment:
    """Helper to create a ClaimAssessment when fact-checking cannot be completed."""
    return ClaimAssessment(
        claim=claim,
        assessment="Insufficient information",
        confidence_score=0.5,
        correct_information="",
        supporting_sources=[],
        refuting_sources=[error_msg] if error_msg else []
    )


async def check_fact(text: str) -> ClaimAssessment:
    """
    Async fact-checking function that can be run in parallel.
    Can be called with: await check_fact(claim) or asyncio.run(check_fact(claim))

    Returns a ClaimAssessment with "Insufficient information" if search or LLM calls fail.
    """
    # Run web search with error handling, if it fails return insufficient info in pydantic class
    try:
        search = ExaSearch()
        results = await asyncio.to_thread(search.web_search, query=text, num_results=3)
    except Exception as e:
        logger.error(f"Search failed for claim '{text[:50]}...': {e}")
        return _create_insufficient_info_assessment(text, f"Search failed: {str(e)}")

    # Handle empty search results
    if not results:
        logger.warning(f"No search results found for claim: {text[:50]}...")
        return _create_insufficient_info_assessment(text, "No search results found")

    # Format sources with titles and summaries for better context
    formatted_sources = []
    for idx, result in enumerate(results, 1):
        source_text = f"Source {idx}: {result['title']}\nURL: {result['url']}\n"
        if result.get('summary'):
            source_text += f"Summary: {result['summary']}\n"
        if result.get('published_date'):
            source_text += f"Published: {result['published_date']}\n"
        formatted_sources.append(source_text)

    sources_str = "\n\n".join(formatted_sources)

    # Get model and create async client, then call LLM with error handling
    try:
        model, _ = get_model_and_client('groq', 'Kimi-K2-instruct')
        api_key = os.getenv('GROQ_API_KEY')
        client = AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

        response = await client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": """
                You are an expert fact-checker.
                Given a claim and a set of sources, determine whether the claim is supported, refuted, or if there is insufficient information in the sources to make a determination.
                For your analysis, consider all the sources collectively.

                IMPORTANT:
                1. If a claim is refuted, you MUST extract the correct information from the sources and provide it in the "correct_information" field.
                2. Be specific and include exact numbers, dates, and details from the sources.
                3. For supporting_sources and refuting_sources, include the actual SOURCE TITLES (not "Source 1", "Source 2", etc.).

                Provide your answer as a JSON object with the following structure:
                {
                    "claim": "...",
                    "assessment": "supported" or "refuted" or "Insufficient information",
                    "confidence_score": a number between 0 and 1 (1 means fully confident the claim is true, 0 means fully confident the claim is false),
                    "correct_information": "If refuted, provide the actual correct information from sources (e.g., 'CoreWeave's Q2 2025 revenue was $1.7 billion'). Otherwise leave empty.",
                    "supporting_sources": [list of actual source titles that support the claim],
                    "refuting_sources": [list of actual source titles that refute the claim]
                }
                Do not include any additional text.
                """},
                {"role": "user", "content": f"Claim: {text}\n\nSources:\n{sources_str}"}
            ],
            response_format=ClaimAssessment
        )
        return response.choices[0].message.parsed
    except Exception as e:
        logger.error(f"LLM call failed for claim '{text[:50]}...': {e}")
        return _create_insufficient_info_assessment(text, f"LLM evaluation failed: {str(e)}")

async def check_facts_batch(claims: List[str], max_concurrent: int = 4) -> List[ClaimAssessment]:
    """
    Check multiple facts in parallel with rate limiting to respect API limits.

    Exa has a rate limit of 5 requests/second, so we use max_concurrent=4 by default
    to stay safely under the limit while still processing multiple requests in parallel.

    Usage:
        results = asyncio.run(check_facts_batch(claims))

    Args:
        claims: List of claim strings to fact-check
        max_concurrent: Maximum concurrent requests (default 4 to respect Exa's 5/sec limit)

    Returns:
        List of ClaimAssessment objects in the same order as input claims.
        Failed claims return ClaimAssessment with "Insufficient information" status.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def rate_limited_check(claim: str, index: int) -> tuple[int, ClaimAssessment]:
        async with semaphore:
            result = await check_fact(claim)
            # Small delay to ensure we don't hit rate limits
            await asyncio.sleep(0.25)  # 4 requests per second max
            return index, result

    tasks = [rate_limited_check(claim, i) for i, claim in enumerate(claims)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results, handling any unexpected exceptions
    ordered_results: List[ClaimAssessment] = [None] * len(claims)  # type: ignore
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Unexpected error in batch fact-check: {result}")
            continue
        index, assessment = result
        ordered_results[index] = assessment

    # Fill any None slots with insufficient info assessments
    for i, result in enumerate(ordered_results):
        if result is None:
            ordered_results[i] = _create_insufficient_info_assessment(
                claims[i], "Batch processing failed"
            )

    return ordered_results
