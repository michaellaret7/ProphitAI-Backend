# from app.core.foundry.embeddings.pinecone_manager import PineconeManager
# from dotenv import load_dotenv
# import os
# from app.core.foundry.embeddings.sparse_encoder import SparseEncoder
# from app.repositories.transcripts_data import get_earnings_transcripts
# from app.core.foundry.models.metadata import EarningsCallMetadata
# from app.core.foundry.chunking.semantic import SemanticChunker
# from app.core.foundry.embeddings.voyage_embeddings import embed_chunks

# load_dotenv()                                                                                                                                                   
# transcripts = get_earnings_transcripts(ticker="AAL", start_year=2024, end_year=2025, limit=4)                                                               

# pm = PineconeManager()
# pm.connect_index(name=os.getenv("PINECONE_INDEX_NAME"), host=os.getenv("PINECONE_HOST"))

# chunker = SemanticChunker()

# all_chunks = []
# for transcript in transcripts["items"]:
#     transcript["ticker"] = transcripts["ticker"]
#     metadata = EarningsCallMetadata.from_transcript(transcript)

#     chunks = chunker.chunk(
#         transcript["content"],
#         doc_type="earnings_call",
#         metadata=metadata.to_chunk_metadata()
#     )

#     # Add chunk_ids
#     for chunk in chunks:
#         chunk.metadata["chunk_id"] = metadata.build_chunk_id(chunk.metadata["chunk_index"])

#     all_chunks.extend(chunks)
#     print(f"Chunked {metadata.ticker} {metadata.fiscal_quarter}: {len(chunks)} chunks")

# print(f"Total chunks: {len(all_chunks)}")

# for chunk in all_chunks:
#     print(chunk.metadata)


# # Embed all chunks
# embedded_chunks = embed_chunks(all_chunks)

# sparse_encoder = SparseEncoder()
# corpus = [chunk.text for chunk in all_chunks]
# sparse_encoder.fit(corpus)
# sparse_encoder.save()

# for chunk in embedded_chunks:
#     chunk.sparse_embedding = sparse_encoder.encode(chunk.text)

# pm.upsert_chunks(embedded_chunks, namespace="earnings_calls")

from app.core.foundry.retrieval.hybrid import HybridSearch
from app.core.foundry.retrieval.vector import VectorSearch
import time

start_time = time.time()
print("Starting hybrid search...")

search = HybridSearch(alpha=0.5)
results = search.search(
    query="Missed expectations and benchmarks.",
    ticker="AAL",
    fiscal_quarter="2025Q3",
    fiscal_year=2025,
    namespace="earnings_calls",
)

print(f"\nFound {len(results)} results:")
for i, result in enumerate(results[:5], 1):
    print(f"\n{i}. Score: {result.score:.4f}")
    print(f"   ID: {result.id}")
    print(f"   Text: {result.metadata['text']}")

end_time = time.time()
print(f"\nTime taken: {end_time - start_time:.2f} seconds")


vector_search = VectorSearch()
results = vector_search.search(
    query="Missed expectations and benchmarks.",
    ticker="AAL",
    fiscal_quarter="2025Q3",
    fiscal_year=2025,
    namespace="earnings_calls",
)
print(f"\nFound {len(results)} results:")
for i, result in enumerate(results[:5], 1):
    print(f"\n{i}. Score: {result.score:.4f}")
    print(f"   ID: {result.id}")
    print(f"   Text: {result.metadata['text']}")
