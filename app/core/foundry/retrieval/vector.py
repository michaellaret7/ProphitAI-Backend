from typing import Optional
from app.core.foundry.embeddings.voyage_embeddings import embed_query
from app.core.foundry.embeddings.pinecone_manager import PineconeManager
from app.core.foundry.models.vector import QueryResult
from dotenv import load_dotenv
import os

load_dotenv()

class VectorSearch:
    def __init__(self):
        self.manager = PineconeManager()
        self.manager.connect_index(name=os.getenv("PINECONE_INDEX_NAME"), host=os.getenv("PINECONE_HOST"))

    def search(
        self, 
        query: str, 
        top_k: int = 10, 
        namespace: str = "earnings_calls",
        ticker: Optional[str] = None,
        fiscal_quarter: Optional[str] = None,
        fiscal_year: Optional[int] = None,
    ) -> list[QueryResult]:

        filters = {
            key: value
            for key, value in (
                ("ticker", ticker),
                ("fiscal_quarter", fiscal_quarter),
                ("fiscal_year", fiscal_year),
            )
            if value is not None
        }
        print(filters)

        embedding = embed_query(query) # Embed the query

        results = self.manager.query(
            vector=embedding.dense,
            top_k=top_k,
            namespace=namespace,
            # filter={
            #     'ticker': 'CRWV'
            # },
            filter=filters,
        )

        return [QueryResult(id=result.id, score=result.score, metadata=result.metadata) for result in results]


if __name__ == "__main__":
    import time
    start_time = time.time()
    print("starting search")
    search = VectorSearch()
    results = search.search(
        query="What are the risks and uncertainties facing the company?",
        ticker="CRWV",
        fiscal_quarter="2025Q3",
        fiscal_year=2025,
        namespace="earnings_calls",
    )
    print(results)
    end_time = time.time()
    print(f"Time taken to search: {end_time - start_time} seconds")