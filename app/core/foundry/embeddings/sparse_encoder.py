"""
Sparse encoder for BM25-based hybrid search.

Wraps pinecone-text's BM25Encoder with save/load functionality
for persistence across application restarts.
"""

from pathlib import Path

from pinecone_text.sparse import BM25Encoder

# Default directory for trained models (app/core/foundry/models/encoder/)
FOUNDRY_DIR = Path(__file__).parent.parent
MODELS_DIR = FOUNDRY_DIR / "models" / "encoder"
DEFAULT_MODEL_PATH = MODELS_DIR / "bm25_encoder.json"

class SparseEncoder:
    """BM25 sparse encoder for hybrid search."""

    def __init__(self):
        self.encoder = BM25Encoder()
        self.is_fitted = False

    def fit(self, corpus: list[str]) -> None:
        """Fit on a corpus."""
        self.encoder.fit(corpus)
        self.is_fitted = True

    def encode(self, text: str) -> dict:
        """Encode a document into a sparse vector."""
        if not self.is_fitted:
            raise RuntimeError("Encoder not fitted. Call fit() or load() first.")
        return self.encoder.encode_documents([text])[0]

    def encode_query(self, query: str) -> dict:
        """Encode a query into a sparse vector."""
        if not self.is_fitted:
            raise RuntimeError("Encoder not fitted. Call fit() or load() first.")
        return self.encoder.encode_queries([query])[0]

    def save(self, path: Path | str | None = None) -> Path:
        """Save the fitted encoder."""
        if not self.is_fitted:
            raise RuntimeError("Cannot save unfitted encoder.")

        save_path = Path(path) if path else DEFAULT_MODEL_PATH
        save_path.parent.mkdir(parents=True, exist_ok=True)
        self.encoder.dump(str(save_path))
        return save_path

    def load(self, path: Path | str | None = None) -> None:
        """Load a fitted encoder."""
        load_path = Path(path) if path else DEFAULT_MODEL_PATH
        if not load_path.exists():
            raise FileNotFoundError(f"No encoder found at {load_path}")

        self.encoder = BM25Encoder.load(str(load_path))
        self.is_fitted = True

if __name__ == "__main__":
    from app.core.foundry.chunking.semantic import SemanticChunker
    from app.repositories.transcripts_data import get_latest_transcript
    from app.core.foundry.models.metadata import EarningsCallMetadata
    from app.core.foundry.embeddings.voyage_embeddings import embed_chunks

    encoder = SparseEncoder()
    chunker = SemanticChunker()

    transcript = get_latest_transcript("CLH")
    print(transcript["content"][:100])

    metadata = EarningsCallMetadata.from_transcript(transcript)

    chunks = chunker.chunk(
        transcript["content"],
        doc_type="earnings_call",
        metadata=metadata.to_chunk_metadata(),
    )

    # Build chunk IDs
    for chunk in chunks:
        chunk.metadata["chunk_id"] = metadata.build_chunk_id(chunk.metadata["chunk_index"])

    # Fit on ALL chunks at once (not inside loop)
    encoder.fit([chunk.text for chunk in chunks])
    encoder.save()
    print(f"Saved encoder fitted on {len(chunks)} chunks")

    embedded_chunks = embed_chunks(chunks, sparse_encoder=encoder)
    print(embedded_chunks[0].sparse_embedding)
    print(embedded_chunks[0].embedding)