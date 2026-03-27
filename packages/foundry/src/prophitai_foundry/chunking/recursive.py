"""
Recursive chunker for RAG pipelines.

Splits text hierarchically using configurable delimiter rules. Processes
text through multiple levels of granularity - paragraphs, then sentences,
then words - preserving document structure naturally.

Algorithm:
1. Split text using highest-level delimiters (e.g., double newlines for paragraphs)
2. If chunks exceed chunk_size, recursively split using next-level delimiters
3. Continue until chunks fit within size limit or reach character-level splitting
4. Merge small adjacent chunks to meet minimum size requirements

Key features:
- Preserves hierarchical document structure
- Pre-built recipes for markdown and plain text
- Configurable delimiter levels and whitespace handling
- Better than fixed-size chunking for structured documents
"""

from typing import Any, Callable, Literal, Optional, Union

from chonkie import RecursiveChunker as ChonkieRecursiveChunker
from chonkie import RecursiveLevel, RecursiveRules

from prophitai_foundry.chunking.utils import preprocess_text
from prophitai_foundry.models.chunk import Chunk

class RecursiveChunker:
    """
    Recursive text chunker using hierarchical delimiter splitting.

    Splits text through multiple levels of granularity while respecting
    document structure. Ideal for well-structured documents like markdown,
    research papers, or code files.

    Attributes:
        chunker: Underlying Chonkie RecursiveChunker instance.
        config: Dictionary of chunker configuration parameters.
        default_metadata: Default metadata to include with all chunks.
    """

    def __init__(
        self,
        tokenizer: Union[str, Callable, object] = "gpt2",
        chunk_size: int = 512,
        chunk_overlap: int = 0,
        rules: Optional[RecursiveRules] = None,
        min_characters_per_chunk: int = 24,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize the recursive chunker.

        Args:
            tokenizer: Tokenizer for counting tokens. Can be:
                - "character": Count characters as tokens
                - "word": Count words as tokens
                - "gpt2", "cl100k_base": Use tiktoken tokenizer
                - Callable: Custom function (text: str) -> int
                - Tokenizer object with encode() method
            chunk_size: Maximum tokens per chunk. Default 512.
            chunk_overlap: Token overlap between consecutive chunks. Default 0.
                Note: Overlap is applied at the final chunk merge stage.
            rules: RecursiveRules defining delimiter hierarchy. Default uses
                standard text rules (paragraphs -> sentences -> words).
            min_characters_per_chunk: Minimum characters per chunk. Smaller
                chunks are merged with neighbors. Default 24.
            metadata: Custom metadata to include with all chunks. Can include
                any key-value pairs (e.g., source, document_id, author).
        """
        # Reason: Store config for inclusion in chunk metadata
        tokenizer_name = tokenizer if isinstance(tokenizer, str) else type(tokenizer).__name__
        self.config = {
            "chunker_type": "recursive",
            "tokenizer": tokenizer_name,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        }
        self.default_metadata = metadata or {}

        if rules is None:
            # Reason: Default rules follow natural text hierarchy -
            # paragraphs (double newline), then sentences, then words
            rules = RecursiveRules(
                levels=[
                    # Level 1: Paragraph breaks
                    RecursiveLevel(
                        delimiters=["\n\n", "\r\n\r\n"],
                        whitespace=False,
                        include_delim="prev",
                    ),
                    # Level 2: Sentence endings
                    RecursiveLevel(
                        delimiters=[". ", "! ", "? ", ".\n", "!\n", "?\n"],
                        whitespace=False,
                        include_delim="prev",
                    ),
                    # Level 3: Clause breaks
                    RecursiveLevel(
                        delimiters=["; ", ": ", ", "],
                        whitespace=False,
                        include_delim="prev",
                    ),
                    # Level 4: Word boundaries (whitespace)
                    RecursiveLevel(
                        delimiters=None,
                        whitespace=True,
                        include_delim=None,
                    ),
                ]
            )

        self._chunk_overlap = chunk_overlap
        self.chunker = ChonkieRecursiveChunker(
            tokenizer=tokenizer,
            chunk_size=chunk_size,
            rules=rules,
            min_characters_per_chunk=min_characters_per_chunk,
        )

    @classmethod
    def for_markdown(
        cls,
        tokenizer: Union[str, Callable, object] = "gpt2",
        chunk_size: int = 512,
        chunk_overlap: int = 0,
        **kwargs,
    ) -> "RecursiveChunker":
        """
        Create chunker optimized for markdown documents.

        Uses markdown-aware delimiters: headers, code blocks, lists,
        paragraphs, then sentences.

        Args:
            tokenizer: Tokenizer for token counting. Default "gpt2".
            chunk_size: Maximum tokens per chunk. Default 512.
            chunk_overlap: Token overlap between chunks. Default 0.
            **kwargs: Additional arguments passed to RecursiveChunker.

        Returns:
            RecursiveChunker configured for markdown.
        """
        markdown_rules = RecursiveRules(
            levels=[
                # Level 1: Major section breaks (headers)
                RecursiveLevel(
                    delimiters=["\n# ", "\n## ", "\n### ", "\n#### "],
                    whitespace=False,
                    include_delim="next",
                ),
                # Level 2: Code blocks and horizontal rules
                RecursiveLevel(
                    delimiters=["\n```", "\n---", "\n***", "\n___"],
                    whitespace=False,
                    include_delim="prev",
                ),
                # Level 3: Paragraph and list breaks
                RecursiveLevel(
                    delimiters=["\n\n", "\n- ", "\n* ", "\n1. "],
                    whitespace=False,
                    include_delim="prev",
                ),
                # Level 4: Sentences
                RecursiveLevel(
                    delimiters=[". ", "! ", "? "],
                    whitespace=False,
                    include_delim="prev",
                ),
                # Level 5: Words
                RecursiveLevel(
                    delimiters=None,
                    whitespace=True,
                    include_delim=None,
                ),
            ]
        )

        return cls(
            tokenizer=tokenizer,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            rules=markdown_rules,
            **kwargs,
        )

    @classmethod
    def from_recipe(
        cls,
        recipe: Literal["markdown", "text"] = "text",
        tokenizer: Union[str, Callable, object] = "gpt2",
        chunk_size: int = 512,
        chunk_overlap: int = 0,
        **kwargs,
    ) -> "RecursiveChunker":
        """
        Create chunker from a pre-defined recipe.

        Args:
            recipe: Recipe name - "markdown" or "text".
            tokenizer: Tokenizer for token counting. Default "gpt2".
            chunk_size: Maximum tokens per chunk. Default 512.
            chunk_overlap: Token overlap between chunks. Default 0.
            **kwargs: Additional arguments.

        Returns:
            RecursiveChunker configured for the specified recipe.

        Raises:
            ValueError: If recipe is not recognized.
        """
        if recipe == "markdown":
            return cls.for_markdown(
                tokenizer=tokenizer,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                **kwargs,
            )
        elif recipe == "text":
            return cls(
                tokenizer=tokenizer,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                **kwargs,
            )
        else:
            raise ValueError(f"Unknown recipe '{recipe}'. Use 'markdown' or 'text'.")

    def _apply_overlap(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        Apply overlap between consecutive chunks.

        Args:
            chunks: List of chunks without overlap.

        Returns:
            List of chunks with overlap text prepended.
        """
        if self._chunk_overlap <= 0 or len(chunks) <= 1:
            return chunks

        result = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]

            # Reason: Get overlap text from end of previous chunk
            overlap_text = prev_chunk.text[-self._chunk_overlap :]

            # Reason: Prepend overlap to current chunk
            new_text = overlap_text + curr_chunk.text
            new_start = max(0, curr_chunk.start_index - len(overlap_text))

            result.append(
                Chunk(
                    text=new_text,
                    start_index=new_start,
                    end_index=curr_chunk.end_index,
                    token_count=curr_chunk.token_count,  # Approximate
                    metadata=curr_chunk.metadata,
                )
            )

        return result

    def chunk(
        self,
        text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[Chunk]:
        """
        Split text into chunks using recursive hierarchical splitting.

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

        processed_text = preprocess_text(text)
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

        return self._apply_overlap(chunks)

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

    chunker = RecursiveChunker()
    transcript = get_latest_transcript("CRWV")
    chunks = chunker.chunk(transcript["content"])
    print(f"Generated {len(chunks)} chunks")
    for chunk in chunks:
        print(chunk.metadata)
        print(chunk.text)
        print("--------------------------------")