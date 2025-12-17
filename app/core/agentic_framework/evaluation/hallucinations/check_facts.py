from app.core.search.web_search.exa_search import ExaSearch
from pydantic import BaseModel, Field
from typing import Literal, List
from app.utils.choose_model_and_client import get_model_and_client
from app.core.agentic_framework.evaluation.hallucinations.extract_facts import extract_facts
import asyncio
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

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

async def check_fact(text: str) -> ClaimAssessment:
    """
    Async fact-checking function that can be run in parallel.
    Can be called with: await check_fact(claim) or asyncio.run(check_fact(claim))
    """
    search = ExaSearch()
    
    # Run sync search in thread pool to not block
    results = await asyncio.to_thread(search.web_search, query=text, num_results=3)

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

    # Get model and create async client
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
        List of ClaimAssessment objects in the same order as input claims
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def rate_limited_check(claim: str) -> ClaimAssessment:
        async with semaphore:
            result = await check_fact(claim)
            # Small delay to ensure we don't hit rate limits
            await asyncio.sleep(0.25)  # 4 requests per second max
            return result
    
    tasks = [rate_limited_check(claim) for claim in claims]
    return await asyncio.gather(*tasks)


if __name__ == "__main__":
    text = """
    {
        "ticker": "MP",
        "name": "MP Materials Corp.",
        "theme_fit": "Dominant US rare earths producer with heavy investments in processing capacity expansion. Negative current profitability (-8.59% ROE, -50.55% net margin) reflects recent capex, but market expects massive payoff with 336.99% forward EPS growth vs 115.99% industry average.",
        "rationale": "MP Materials has invested heavily in rare earth processing capacity to reduce US dependence on China. Despite negative profitability and free cash flow (-$1.32/share), the company maintains strong cash position ($11.15/share) and low debt (debt/equity 0.42). The extreme forward EPS growth expectations (336.99%) suggest market believes capex investments will pay off as production ramps up.",
        "key_metrics": "ROE: -8.59%; Forward EPS Growth: 336.99%; Price-to-Sales: 44.16; Debt/Equity: 0.42; Cash/Share: $11.15"
    },
    {
        "ticker": "UEC",
        "name": "Uranium Energy Corp.",
        "theme_fit": "Uranium miner positioned for nuclear energy renaissance with massive 274.67% revenue growth but negative profitability (-7.72% ROE) due to expansion investments. No debt and high cash position support continued investment phase.",
        "rationale": "UEC has made significant investments in uranium mining projects ahead of expected nuclear power growth. Despite negative operating cash flow (-$0.19/share), revenue growth of 274.67% shows operations ramping up. Forward EPS growth of 310.29% vs industry 115.99% indicates market expects profitability inflection as projects come online.",
        "key_metrics": "Revenue Growth: 274.67%; Forward EPS Growth: 310.29%; ROE: -7.72%; Cash Ratio: 23.21; Price-to-Sales: 119.98"
    },

    """
    claims = extract_facts(text)
    
    print(f"Checking {len(claims)} facts in parallel...\n")
    
    # Run all fact checks in parallel (much faster!)
    results = asyncio.run(check_facts_batch(claims))
    
    for result in results:
        print(f"\n{'-'*80}")
        if result.assessment == "refuted":
            print(f"Refuted: {result.correct_information}")
            print(f"Refuting sources: {result.claim}")

        print(f"{'-'*80}")
    
    # Alternative: Check single fact
    # result = asyncio.run(check_fact("Some claim"))
    # print(result)