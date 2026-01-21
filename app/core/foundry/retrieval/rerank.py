import voyageai
from dotenv import load_dotenv
import os

load_dotenv()

def rerank(
    query: str,
    documents: list[str],
    model: str = "rerank-2.5",
) -> list[str]:

    client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

    response = client.rerank(
        query=query,
        documents=documents,
        model=model,
        top_k=5,
    )

    return response


if __name__ == "__main__":
    query = "What is the company's business model?"
    documents = [
        "The company is a technology company that provides software solutions for the energy industry.", 
        "The company is a technology company that provides software solutions for the energy industry.",
        "Quarterly earnings exceeded expectations due to strong demand in the Asia-Pacific region.",
        "New regulatory frameworks in the EU may impact our supply chain logistics.",
        "The merger with the leading competitor is expected to close by Q4 2025.",
        "We are investing heavily in AI research to improve our customer support automation.",
        "Dividend payouts have been suspended to prioritize debt repayment.",
        "Customer retention rates have dropped slightly following the recent price increase.",
        "The release of our flagship product has been delayed due to manufacturing constraints.",
        "Our sustainability initiative aims to reduce carbon emissions by 30% over the next five years.",
        "Market volatility has led to a cautious outlook for the upcoming fiscal year.",
        "We have secured a strategic partnership to expand our cloud infrastructure services."
    ]

    reranked = rerank(query, documents)

    for result in reranked.results:
        print(f"Document Index: {result.index}")
        print(f"Score: {result.relevance_score}")
        print(f"Text: {result.document}")
        print("-" * 30)