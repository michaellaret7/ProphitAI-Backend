"""
Semantic chunker for RAG pipelines.

Splits text into semantically coherent chunks using embedding similarity.
Uses Chonkie's SemanticChunker which analyzes sentence embeddings to find
natural topic boundaries, ensuring related content stays together.

Algorithm:
1. Split text into sentences using delimiters
2. Generate embeddings for each sentence (with similarity window context)
3. Calculate cosine similarity between consecutive sentence groups
4. Identify breakpoints where similarity drops below threshold
5. Group sentences into chunks respecting max chunk_size

Key features:
- Savitzky-Golay filtering for smoother boundary detection
- Skip-window merging for connecting related non-consecutive content
- Configurable similarity threshold and chunk sizing
"""

import os
from typing import Any, Literal, Optional, Union

from chonkie import SemanticChunker as ChonkieSemanticChunker
from chonkie.embeddings import (
    AutoEmbeddings,
    BaseEmbeddings,
    GeminiEmbeddings,
    LiteLLMEmbeddings,
    Model2VecEmbeddings,
    OpenAIEmbeddings,
    SentenceTransformerEmbeddings,
    VoyageAIEmbeddings,
)

from app.core.foundry.chunking.utils import preprocess_text
from app.core.foundry.models.chunk import Chunk

# Reason: Type alias for supported embedding providers
EmbeddingProvider = Literal[
    "voyage",
    "openai",
    "gemini",
    "sentence_transformer",
    "model2vec",
    "litellm",
    "auto",
]


def _create_embedding_model(
    provider: EmbeddingProvider,
    model_name: str,
) -> BaseEmbeddings:
    """
    Create an embedding model instance based on provider and model name.

    Uses environment variables for API keys:
        - VOYAGE_API_KEY: VoyageAI
        - OPENAI_API_KEY: OpenAI (auto-detected by library)
        - GOOGLE_API_KEY: Google Gemini

    Args:
        provider: Embedding provider name.
        model_name: Model identifier for the provider.
            - voyage: "voyage-finance-2", "voyage-3", "voyage-3-lite"
            - openai: "text-embedding-3-small", "text-embedding-3-large"
            - gemini: "models/text-embedding-004"
            - sentence_transformer: "all-MiniLM-L6-v2", "all-mpnet-base-v2"
            - model2vec: "minishlab/potion-base-8M", "minishlab/M2V_base_output"
            - litellm: Any model supported by LiteLLM
            - auto: Auto-selects best available

    Returns:
        Configured embedding model instance.

    Raises:
        ValueError: If provider is not supported.
    """
    if provider == "voyage":
        return VoyageAIEmbeddings(
            model=model_name,
            api_key=os.getenv("VOYAGE_API_KEY"),
        )
    elif provider == "openai":
        return OpenAIEmbeddings(model=model_name)
    elif provider == "gemini":
        return GeminiEmbeddings(
            model=model_name,
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
    elif provider == "sentence_transformer":
        return SentenceTransformerEmbeddings(model=model_name)
    elif provider == "model2vec":
        return Model2VecEmbeddings(model=model_name)
    elif provider == "litellm":
        return LiteLLMEmbeddings(model=model_name)
    elif provider == "auto":
        return AutoEmbeddings.get_embeddings(model_name)
    else:
        raise ValueError(
            f"Unsupported embedding provider: {provider}. "
            f"Supported: voyage, openai, gemini, sentence_transformer, "
            f"model2vec, litellm, auto"
        )


class SemanticChunker:
    """
    Semantic text chunker using embedding similarity for boundary detection.

    Splits text at points where semantic meaning changes, keeping related
    content together. Better than fixed-size chunking for maintaining
    contextual coherence in RAG retrieval.

    Attributes:
        chunker: Underlying Chonkie SemanticChunker instance.
        config: Dictionary of chunker configuration parameters.
        default_metadata: Default metadata to include with all chunks.
    """

    def __init__(
        self,
        model_name: str = "voyage-finance-2",
        embedding_provider: EmbeddingProvider = "voyage",
        threshold: float = 0.4,
        chunk_size: int = 768,
        similarity_window: int = 3,
        min_sentences_per_chunk: int = 3,
        min_characters_per_sentence: int = 24,
        skip_window: int = 0,
        filter_window: int = 5,
        filter_polyorder: int = 3,
        filter_tolerance: float = 0.2,
        delim: Union[str, list[str], None] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize the semantic chunker.

        Args:
            model_name: Model identifier for the embedding provider. Examples:
                - voyage: "voyage-finance-2", "voyage-3", "voyage-3-lite"
                - openai: "text-embedding-3-small", "text-embedding-3-large"
                - gemini: "models/text-embedding-004"
                - sentence_transformer: "all-MiniLM-L6-v2", "all-mpnet-base-v2"
                - model2vec: "minishlab/potion-base-8M"
                - litellm: Any LiteLLM-supported model
                - auto: Auto-selects best available
            embedding_provider: Embedding provider to use. Default "voyage".
                Options: voyage, openai, gemini, sentence_transformer,
                model2vec, litellm, auto.
            threshold: Similarity threshold (0-1). Lower values create larger
                chunks by grouping more sentences together. Default 0.4.
            chunk_size: Maximum tokens per chunk. Default 768.
            similarity_window: Number of sentences to consider when calculating
                similarity between groups. Default 3.
            min_sentences_per_chunk: Minimum sentences required per chunk. Default 3.
            min_characters_per_sentence: Minimum characters for a valid sentence.
                Shorter sequences are merged with neighbors. Default 24.
            skip_window: Groups to skip when looking for similar content to merge.
                0 (default) uses standard semantic grouping.
                1+ enables merging of semantically similar non-consecutive groups.
            filter_window: Savitzky-Golay filter window length for smoother
                boundary detection. Must be odd. Default 5.
            filter_polyorder: Polynomial order for Savitzky-Golay filter.
                Must be less than filter_window. Default 3.
            filter_tolerance: Tolerance for boundary detection after filtering.
                Higher values create more stable boundaries. Default 0.2.
            delim: Sentence delimiters. Default [". ", "! ", "\\n"].
                Note: "? " is excluded to keep Q&A exchanges intact in transcripts.
            metadata: Custom metadata to include with all chunks. Can include
                any key-value pairs (e.g., source, document_id, author).
        """
        delim_value: Union[str, list[str]] = (
            delim if delim is not None else [". ", "! ", "\n"]
        )

        embedding_model = _create_embedding_model(embedding_provider, model_name)

        self.config = {
            "chunker_type": "semantic",
            "embedding_provider": embedding_provider,
            "embedding_model": model_name,
            "threshold": threshold,
            "chunk_size": chunk_size,
            "similarity_window": similarity_window,
            "min_sentences_per_chunk": min_sentences_per_chunk,
        }
        self.default_metadata = metadata or {}

        self.chunker = ChonkieSemanticChunker(
            embedding_model=embedding_model,
            threshold=threshold,
            chunk_size=chunk_size,
            similarity_window=similarity_window,
            min_sentences_per_chunk=min_sentences_per_chunk,
            min_characters_per_sentence=min_characters_per_sentence,
            skip_window=skip_window,
            filter_window=filter_window,
            filter_polyorder=filter_polyorder,
            filter_tolerance=filter_tolerance,
            delim=delim_value,
            include_delim="prev",
        )

    def chunk(
        self,
        text: str,
        doc_type: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[Chunk]:
        """
        Split text into semantically coherent chunks.

        Args:
            text: Input text to chunk.
            doc_type: Document type for filtering (e.g., "transcript", "filing",
                "news", "research", "10k", "10q", "8k").
            metadata: Additional metadata to include with chunks. Merged with
                default_metadata set at initialization. Per-call metadata takes
                precedence over default metadata.

        Returns:
            List of Chunk objects with text, positions, token counts, and metadata.
        """
        if not text or not text.strip():
            return []

        processed_text = preprocess_text(text)
        chonkie_chunks = self.chunker.chunk(processed_text)
        total_chunks = len(chonkie_chunks)

        # Reason: Merge default metadata with per-call metadata
        merged_metadata = {**self.default_metadata, **(metadata or {})}

        chunks = []
        for idx, c in enumerate(chonkie_chunks):
            chunk_metadata = {
                "chunk_index": idx,
                "total_chunks": total_chunks,
                "doc_type": doc_type,
                **merged_metadata,
            }

            chunks.append(
                Chunk(
                    text=c.text,
                    start_index=c.start_index,
                    end_index=c.end_index,
                    token_count=c.token_count,
                    metadata=chunk_metadata,
                )
            )

        return chunks

    def chunk_batch(
        self,
        texts: list[str],
        doc_type: str,
    ) -> list[list[Chunk]]:
        """
        Chunk multiple texts in batch.

        Args:
            texts: List of texts to chunk.
            doc_type: Document type for filtering.

        Returns:
            List of chunk lists, one per input text.
        """
        return [self.chunk(text, doc_type) for text in texts]

    def __call__(
        self,
        text: str,
        doc_type: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[Chunk]:
        """Allow callable syntax: chunker(text, doc_type, metadata={...})."""
        return self.chunk(text, doc_type, metadata=metadata)


if __name__ == "__main__":
    from app.repositories.transcripts_data import get_latest_transcript

    chunker = SemanticChunker()
    transcript = get_latest_transcript("CRWV")
    print(transcript["content"][:1000])
    chunks = chunker.chunk(transcript["content"], doc_type="transcript")
    print(f"Generated {len(chunks)} chunks")
    for chunk in chunks:
        print("\n")
        print("--------------------------------")
        print(f"Chunk {chunk.start_index} - {chunk.end_index}: {chunk.text}")
        print("--------------------------------")
        print("\n")