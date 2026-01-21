from app.core.foundry.chunking.earnings_calls.chunker import EarningsCallChunker
from app.repositories.transcripts_data import get_latest_transcript
from app.core.foundry.models.metadata import EarningsCallMetadata
from app.core.foundry.embeddings.voyage_embeddings import embed_chunks, embed_query
from app.core.foundry.embeddings.pinecone_manager import PineconeManager
from dotenv import load_dotenv
import os
from app.core.foundry.retrieval.vector import VectorSearch

load_dotenv()

vector_search = VectorSearch()
results = vector_search.search(
    query="Summarize new AI offerings, feature launches, and customer deployments mentioned on this call",
    ticker="MSFT",
    fiscal_quarter="2026Q1",
    fiscal_year=2026,
    namespace="earnings_calls",
    top_k=3,
)
for result in results:
    print(result.metadata)
    print(result.score)
    print("--------------------------------")
