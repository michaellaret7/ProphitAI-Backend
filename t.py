from perplexity import Perplexity
from dotenv import load_dotenv
import os
import asyncio
from perplexity import AsyncPerplexity

load_dotenv()

os.environ['PERPLEXITY_API_KEY'] = os.getenv('PERPLEXITY_API_KEY')

# PERPLEXITY RETURNS BOTH ARTICLES AND SUMMARIZED RESEARCH

# from openai import OpenAI

# client = OpenAI(
#     api_key=os.getenv('PERPLEXITY_API_KEY'),
#     base_url="https://api.perplexity.ai"
# )

# response = client.chat.completions.create(
#     model="sonar-reasoning-pro",
#     messages=[
#         {"role": "user", "content": "Analyze the feasibility of fusion energy becoming a mainstream power source by 2040."}
#     ]
# )

# print(response.choices[0].message.content)

# NOTE: Test Perplexity, Tavily, and Exa

async def main():
    async with AsyncPerplexity() as client:
        # Concurrent searches for better performance
        tasks = [
            client.search.create(
                query="NVIDIA financial performance analysis Q4 2025 earnings revenue growth market share analyst ratings",
                max_results=1
            ),
            # client.search.create(
            #     query="NVIDIA latest product launches GPU architecture updates AI software stack developments hardware roadmap 2025",
            #     max_results=1
            # ),
            # client.search.create(
            #     query="CoreWeave strategic partnerships acquisitions 2025",
            #     max_results=1,
            #     max_tokens=500_000,        # Total content budget across all results (default: 25,000, max: 1,000,000)
            #     max_tokens_per_page=10_000 # Content limit per individual result
            # )
        ]
        
        results = await asyncio.gather(*tasks)
        
        for i, search in enumerate(results):
            print(f"Query {i+1} results:")
            for result in search.results:
                print(f"  {result.title}: {result.url}")
                # print(f"  {result.content}")
                print(f"  {result.snippet}")
            print("---"*100)

asyncio.run(main())