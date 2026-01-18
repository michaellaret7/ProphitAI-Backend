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
import re
from typing import Any, Optional, Union

from chonkie import SemanticChunker as ChonkieSemanticChunker
from chonkie.embeddings import OpenAIEmbeddings, VoyageAIEmbeddings

from app.core.foundry.models.chunk import Chunk


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
        embedding_model: Union[str, object] = VoyageAIEmbeddings(
            model="voyage-finance-2", api_key=os.getenv("VOYAGE_API_KEY")
        ),
        threshold: float = 0.5,
        chunk_size: int = 512,
        similarity_window: int = 3,
        min_sentences_per_chunk: int = 2,
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
            embedding_model: Model for generating embeddings. Can be:
                - String model identifier (e.g., "text-embedding-3-large")
                - Chonkie embedding instance (OpenAIEmbeddings, etc.)
            threshold: Similarity threshold (0-1). Lower values create larger
                chunks by grouping more sentences together. Default 0.5.
            chunk_size: Maximum tokens per chunk. Default 512.
            similarity_window: Number of sentences to consider when calculating
                similarity between groups. Default 3.
            min_sentences_per_chunk: Minimum sentences required per chunk. Default 2.
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

        # Reason: Store config for inclusion in chunk metadata
        self._embedding_model_name = (
            embedding_model if isinstance(embedding_model, str) else type(embedding_model).__name__
        )
        self.config = {
            "chunker_type": "semantic",
            "embedding_model": self._embedding_model_name,
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

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text to handle abbreviations that break sentence detection.

        Removes periods from common abbreviations (U.S., Inc., etc.) to prevent
        the sentence splitter from incorrectly detecting sentence boundaries.

        Args:
            text: Raw input text.

        Returns:
            Text with abbreviation periods removed.
        """
        # Reason: These abbreviations contain periods that get mistakenly
        # treated as sentence boundaries, splitting sentences mid-phrase
        abbreviations = [
            (r"U\.S\.", "US"),
            (r"Inc\.", "Inc"),
            (r"Corp\.", "Corp"),
            (r"Ltd\.", "Ltd"),
            (r"Co\.", "Co"),
            (r"Mr\.", "Mr"),
            (r"Mrs\.", "Mrs"),
            (r"Ms\.", "Ms"),
            (r"Dr\.", "Dr"),
            (r"vs\.", "vs"),
            (r"etc\.", "etc"),
            (r"i\.e\.", "ie"),
            (r"e\.g\.", "eg"),
            (r"a\.m\.", "am"),
            (r"p\.m\.", "pm"),
            (r"No\.", "No"),
            (r"Vol\.", "Vol"),
            (r"Rev\.", "Rev"),
            (r"Est\.", "Est"),
            (r"Ave\.", "Ave"),
            (r"St\.", "St"),
        ]
        for pattern, replacement in abbreviations:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    @classmethod
    def with_openai(
        cls,
        model: str = "text-embedding-3-small",
        threshold: float = 0.8,
        chunk_size: int = 512,
        **kwargs,
    ) -> "SemanticChunker":
        """
        Create chunker with OpenAI embeddings.

        Args:
            model: OpenAI embedding model name. Default "text-embedding-3-small".
            threshold: Similarity threshold (0-1). Default 0.8.
            chunk_size: Maximum tokens per chunk. Default 512.
            **kwargs: Additional arguments passed to SemanticChunker.

        Returns:
            SemanticChunker configured with OpenAI embeddings.
        """
        embeddings = OpenAIEmbeddings(model=model)
        return cls(
            embedding_model=embeddings,
            threshold=threshold,
            chunk_size=chunk_size,
            **kwargs,
        )

    def chunk(
        self,
        text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[Chunk]:
        """
        Split text into semantically coherent chunks.

        Args:
            text: Input text to chunk.
            metadata: Additional metadata to include with chunks. Merged with
                default_metadata set at initialization. Per-call metadata takes
                precedence over default metadata.

        Returns:
            List of Chunk objects with text, positions, token counts, and metadata.
        """
        if not text or not text.strip():
            return []

        processed_text = self._preprocess_text(text)
        chonkie_chunks = self.chunker.chunk(processed_text)

        total_chunks = len(chonkie_chunks)
        total_chars = len(text)

        # Reason: Merge default metadata with per-call metadata
        merged_metadata = {**self.default_metadata, **(metadata or {})}

        chunks = []
        for idx, c in enumerate(chonkie_chunks):
            chunk_metadata = {
                # Chunk position info
                "chunk_index": idx,
                "chunk_number": idx + 1,
                "total_chunks": total_chunks,
                # Source document info
                "total_chars": total_chars,
                "char_start_pct": round(c.start_index / total_chars * 100, 1),
                "char_end_pct": round(c.end_index / total_chars * 100, 1),
                # Chunker config
                **self.config,
                # Custom metadata
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

    def chunk_batch(self, texts: list[str]) -> list[list[Chunk]]:
        """
        Chunk multiple texts in batch.

        Args:
            texts: List of texts to chunk.

        Returns:
            List of chunk lists, one per input text.
        """
        return [self.chunk(text) for text in texts]

    def __call__(
        self,
        text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[Chunk]:
        """Allow callable syntax: chunker(text, metadata={...})."""
        return self.chunk(text, metadata=metadata)


if __name__ == "__main__":
    from app.repositories.transcripts_data import get_latest_transcript

    chunker = SemanticChunker()
    transcript = get_latest_transcript("CRWV")
    chunks = chunker.chunk(transcript["content"])
    print(f"Generated {len(chunks)} chunks")
    for chunk in chunks:
        print("\n")
        print("--------------------------------")
        print(f"Chunk {chunk.start_index} - {chunk.end_index}: {chunk.text}")
        print("--------------------------------")
        print("\n")