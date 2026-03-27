"""
Structurally-aware chunker for earnings call transcripts.

Goal:
- Preserve high-level transcript structure (operator intro, IR safe harbor,
  prepared remarks, Q&A turns, media Q&A, closing).
- Avoid splitting in the middle of a Q&A turn (question + answers) unless forced.
- Produce Chunk objects compatible with the Foundry chunking pipeline.

Design (2-pass):
1) Parse speaker turns (Speaker: text) into Turn objects with character offsets.
2) Build structural units:
   - Prepared remarks: consecutive turns before Q&A.
   - Q&A: grouped by operator "Our next/first question comes from ..." boundaries,
     with separate analyst vs media Q&A sections when present.
3) Pack units into chunks up to chunk_size tokens (token-counted via Chonkie).
   If a unit is too large, split it with a fallback recursive splitter while
   trying to keep boundaries (paragraph/sentence) sensible.

This chunker is intentionally heuristic-based because transcript formats vary
across vendors (IR sites, Seeking Alpha, FactSet, etc.), but those variations
still share strong marker phrases.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Optional, Union

from chonkie import RecursiveChunker as ChonkieRecursiveChunker
from chonkie import RecursiveRules

from prophitai_foundry.chunking.utils import preprocess_text
from prophitai_foundry.models.chunk import Chunk

from .models import Turn, Unit
from .patterns import (
    CLOSING_RE,
    MEDIA_START_RE,
    OP_Q_INTRO_RE,
    QNA_START_RE,
    QUESTIONER_RE,
    SAFE_HARBOR_RE,
    SPEAKER_LINE_RE,
)
from .utils import mk_recursive_level


class EarningsCallChunker:
    """
    Structurally-aware earnings call chunker.

    Primary use: earnings call transcripts (operator + prepared remarks + Q&A).
    """

    def __init__(
        self,
        tokenizer: Union[str, Callable, object] = "gpt2",
        chunk_size: int = 512,
        chunk_overlap: int = 0,
        min_characters_per_chunk: int = 24,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """
        Args:
            tokenizer: Tokenizer for counting tokens (delegated to Chonkie).
            chunk_size: Max tokens per chunk.
            chunk_overlap: Token overlap between adjacent chunks (whitespace-token approx).
            min_characters_per_chunk: Drop/merge extremely small chunks.
            metadata: Default metadata to merge into every produced chunk.
        """
        self.default_metadata = metadata or {}
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._min_chars = min_characters_per_chunk

        # Fallback splitter for units that are too large to keep intact.
        # We split by paragraph -> sentence-ish -> word-ish.
        rules = RecursiveRules(
            levels=[
                mk_recursive_level(["\n\n", "\n"]),
                mk_recursive_level([". ", "? ", "! ", "; "]),
                mk_recursive_level(None, whitespace=True),
            ]
        )
        self._fallback_splitter = ChonkieRecursiveChunker(
            tokenizer=tokenizer,
            chunk_size=chunk_size,
            rules=rules,
            min_characters_per_chunk=min_characters_per_chunk,
        )

        # Token counter: huge chunk size so we can count by summing returned chunks.
        self._token_counter = ChonkieRecursiveChunker(
            tokenizer=tokenizer,
            chunk_size=max(10_000_000, chunk_size * 10_000),
            rules=rules,
            min_characters_per_chunk=1,
        )

    # -----------------------------
    # Public API
    # -----------------------------

    def chunk(
        self,
        text: str,
        doc_type: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[Chunk]:
        """
        Chunk an earnings call transcript with structure awareness.

        Args:
            text: Raw transcript text.
            doc_type: Document type for filtering (e.g., "transcript", "earnings_call").
            metadata: Per-call metadata merged into each chunk (overrides defaults).

        Returns:
            List[Chunk]
        """
        if not text or not text.strip():
            return []

        processed = preprocess_text(text)
        turns = self._parse_turns(processed)
        units = self._build_units(turns, processed)

        chunks = self._pack_units_into_chunks(units)

        # Attach metadata + chunk indices
        merged_default = {**self.default_metadata, **(metadata or {})}
        final: list[Chunk] = []
        total = len(chunks)

        for i, c in enumerate(chunks):
            chunk_meta = {
                "chunk_index": i,
                "total_chunks": total,
                "doc_type": doc_type,
                **merged_default,
            }
            final.append(
                Chunk(
                    text=c.text,
                    start_index=c.start_index,
                    end_index=c.end_index,
                    token_count=c.token_count,
                    metadata=chunk_meta,
                )
            )

        return self._apply_overlap(final)

    def chunk_batch(self, texts: list[str], doc_type: str) -> list[list[Chunk]]:
        return [self.chunk(t, doc_type) for t in texts]

    def __call__(
        self,
        text: str,
        doc_type: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> list[Chunk]:
        return self.chunk(text, doc_type, metadata=metadata)

    # -----------------------------
    # Turn parsing
    # -----------------------------

    def _parse_turns(self, processed: str) -> list[Turn]:
        """
        Parse transcript into speaker turns using "Speaker: ..." markers.
        If markers are missing, returns a single Turn("UNKNOWN", full_text).
        """
        matches = list(SPEAKER_LINE_RE.finditer(processed))
        if not matches:
            return [Turn(speaker="UNKNOWN", text=processed, start=0, end=len(processed))]

        turns: list[Turn] = []

        for i, m in enumerate(matches):
            speaker = (m.group("speaker") or "").strip()
            start = m.start()
            # Start content after the colon on that line
            body_start = m.start("body")
            next_start = matches[i + 1].start() if i + 1 < len(matches) else len(processed)
            body = processed[body_start:next_start].rstrip()

            turns.append(Turn(speaker=speaker, text=body, start=start, end=next_start))

        return turns

    # -----------------------------
    # Structure detection
    # -----------------------------

    def _build_units(self, turns: list[Turn], processed: str) -> list[Unit]:
        """
        Convert turns into higher-level structure-aware units.
        """
        if not turns:
            return []

        # Identify the first operator question intro; that's the most reliable Q&A boundary.
        qna_first_q_idx = None
        media_start_idx = None
        closing_idx = None

        for i, t in enumerate(turns):
            if qna_first_q_idx is None and self._is_operator(t) and OP_Q_INTRO_RE.search(t.text):
                qna_first_q_idx = i
            if media_start_idx is None and self._is_operator(t) and MEDIA_START_RE.search(t.text):
                media_start_idx = i
            if closing_idx is None and CLOSING_RE.search(t.text):
                closing_idx = i

        # If we don't see first question intro, fall back to "Q&A session" marker.
        if qna_first_q_idx is None:
            for i, t in enumerate(turns):
                if self._is_operator(t) and QNA_START_RE.search(t.text):
                    qna_first_q_idx = i
                    break

        # Prepared remarks are everything before qna_first_q_idx (if any).
        prepared_end = qna_first_q_idx if qna_first_q_idx is not None else len(turns)

        units: list[Unit] = []

        # 1) Prepared remarks units
        prepared_turns = turns[:prepared_end]
        if prepared_turns:
            units.extend(self._units_from_prepared_turns(prepared_turns))

        # 2) Q&A units (analyst then media)
        if qna_first_q_idx is not None:
            qna_turns = turns[qna_first_q_idx:]

            # If media marker exists, split analyst vs media
            if media_start_idx is not None and media_start_idx >= qna_first_q_idx:
                analyst_turns = turns[qna_first_q_idx:media_start_idx]
                media_turns = turns[media_start_idx:]
                units.extend(self._units_from_qna_turns(analyst_turns, qna_type="analyst"))
                units.extend(self._units_from_qna_turns(media_turns, qna_type="media"))
            else:
                units.extend(self._units_from_qna_turns(qna_turns, qna_type="analyst"))

        # 3) If we found a late closing marker and didn't treat it specially, it will
        # be inside prepared/qna units; that's fine. We still add metadata at chunk-level.

        return units

    def _units_from_prepared_turns(self, turns: list[Turn]) -> list[Unit]:
        """
        Create units for the pre-Q&A portion.

        Strategy:
        - Keep each speaker block as a unit (operator intro, IR safe-harbor, CEO remarks, CFO remarks, etc.)
        - But also label likely safe-harbor blocks.
        """
        units: list[Unit] = []
        for t in turns:
            t_text = self._format_turn(t)
            meta: dict[str, Any] = {
                "section_type": "prepared",
                "speaker": t.speaker,
                "is_operator": self._is_operator(t),
                "contains_safe_harbor": bool(SAFE_HARBOR_RE.search(t.text)),
            }
            # More specific operator intro vs executive prepared
            if self._is_operator(t):
                meta["prepared_subtype"] = "operator"
            elif meta["contains_safe_harbor"]:
                meta["prepared_subtype"] = "safe_harbor"
            else:
                meta["prepared_subtype"] = "remarks"

            units.append(Unit(unit_type="prepared", text=t_text, start=t.start, end=t.end, meta=meta))
        return units

    def _units_from_qna_turns(self, turns: list[Turn], qna_type: str) -> list[Unit]:
        """
        Group turns into Q&A units.

        Boundaries:
        - A new Q&A turn starts when Operator says "Our next/first question comes from ..."
        - The unit includes that operator intro + the question + all answers until the next operator intro.
        """
        if not turns:
            return []

        units: list[Unit] = []
        i = 0
        q_index = 0

        # If the first provided turn isn't an operator intro, we still proceed by
        # chunking them in a best-effort way (some transcripts omit repeated operator lines).
        while i < len(turns):
            # Find next question intro
            if self._is_operator(turns[i]) and OP_Q_INTRO_RE.search(turns[i].text):
                start_i = i
            else:
                # If we're not on an operator intro, treat current turn as start of a qna unit.
                start_i = i

            # The unit ends right before the next operator intro (or end)
            j = start_i + 1
            while j < len(turns):
                if self._is_operator(turns[j]) and OP_Q_INTRO_RE.search(turns[j].text):
                    break
                j += 1

            unit_turns = turns[start_i:j]
            unit_text = "\n\n".join(self._format_turn(t) for t in unit_turns).strip()

            # Questioner extraction from operator intro if present
            questioner = None
            if unit_turns and self._is_operator(unit_turns[0]):
                m = QUESTIONER_RE.search(unit_turns[0].text)
                if m:
                    questioner = m.group("name").strip()

            meta: dict[str, Any] = {
                "section_type": "qna",
                "qna_type": qna_type,
                "qna_turn_index": q_index,
                "questioner": questioner,
            }

            units.append(
                Unit(
                    unit_type="qna",
                    text=unit_text,
                    start=unit_turns[0].start,
                    end=unit_turns[-1].end,
                    meta=meta,
                )
            )

            q_index += 1
            i = j

        return units

    # -----------------------------
    # Packing units into chunks
    # -----------------------------

    def _pack_units_into_chunks(self, units: list[Unit]) -> list[Chunk]:
        """
        Pack units into size-bounded chunks, splitting oversized units if needed.
        """
        chunks: list[Chunk] = []
        buffer_texts: list[str] = []
        buffer_meta: dict[str, Any] = {}
        buffer_start: Optional[int] = None
        buffer_end: Optional[int] = None

        def flush():
            nonlocal buffer_texts, buffer_meta, buffer_start, buffer_end
            if not buffer_texts:
                return

            text = "\n\n".join(buffer_texts).strip()
            if not text or len(text) < self._min_chars:
                buffer_texts = []
                buffer_meta = {}
                buffer_start = None
                buffer_end = None
                return

            token_count = self._count_tokens(text)
            chunks.append(
                Chunk(
                    text=text,
                    start_index=buffer_start or 0,
                    end_index=buffer_end or (buffer_start or 0) + len(text),
                    token_count=token_count,
                    metadata=buffer_meta.copy(),
                )
            )
            buffer_texts = []
            buffer_meta = {}
            buffer_start = None
            buffer_end = None

        for u in units:
            u_tokens = self._count_tokens(u.text)

            # If a single unit is too large, split it (while keeping its metadata)
            if u_tokens > self._chunk_size:
                # Flush current buffer first
                flush()

                subchunks = self._fallback_split(u)
                for sc in subchunks:
                    chunks.append(sc)
                continue

            # Try appending to buffer
            candidate_text = ("\n\n".join(buffer_texts + [u.text]).strip()) if buffer_texts else u.text.strip()
            cand_tokens = self._count_tokens(candidate_text)

            if cand_tokens <= self._chunk_size:
                if buffer_start is None:
                    buffer_start = u.start
                buffer_end = u.end
                buffer_texts.append(u.text)

                # Merge metadata conservatively:
                # - Keep the *last* unit's section_type/qna_turn_index so retrieval knows what's inside.
                # - Also preserve a set of included section types.
                buffer_meta = self._merge_chunk_meta(buffer_meta, u.meta)
            else:
                flush()
                buffer_start = u.start
                buffer_end = u.end
                buffer_texts = [u.text]
                buffer_meta = u.meta.copy()

        flush()
        return chunks

    def _fallback_split(self, unit: Unit) -> list[Chunk]:
        """
        Split an oversized unit using recursive fallback splitting, and map indices
        back into the full transcript by offsetting with unit.start.

        We keep unit-level metadata and add split metadata.
        """
        # Chonkie returns chunks with start/end relative to unit.text.
        chonkie_chunks = self._fallback_splitter.chunk(unit.text)
        out: list[Chunk] = []
        for k, c in enumerate(chonkie_chunks):
            meta = {
                **unit.meta,
                "split_from_oversized_unit": True,
                "unit_type": unit.unit_type,
                "unit_split_index": k,
                "unit_total_splits": len(chonkie_chunks),
            }
            out.append(
                Chunk(
                    text=c.text,
                    start_index=unit.start + c.start_index,
                    end_index=unit.start + c.end_index,
                    token_count=c.token_count,
                    metadata=meta,
                )
            )
        return out

    def _merge_chunk_meta(self, current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
        """
        Merge metadata for a chunk that contains multiple units.
        """
        if not current:
            merged = incoming.copy()
            merged["included_section_types"] = {incoming.get("section_type")}
            return merged

        merged = current.copy()
        included = set(merged.get("included_section_types") or set())
        included.add(incoming.get("section_type"))
        merged["included_section_types"] = included

        # Prefer latest unit's granular fields
        for k in ("section_type", "prepared_subtype", "qna_type", "qna_turn_index", "speaker", "questioner"):
            if k in incoming and incoming.get(k) is not None:
                merged[k] = incoming[k]

        # Preserve booleans as OR
        if "contains_safe_harbor" in incoming:
            merged["contains_safe_harbor"] = bool(merged.get("contains_safe_harbor")) or bool(incoming.get("contains_safe_harbor"))

        return merged

    # -----------------------------
    # Overlap
    # -----------------------------

    def _apply_overlap(self, chunks: list[Chunk]) -> list[Chunk]:
        if self._chunk_overlap <= 0 or len(chunks) <= 1:
            return chunks

        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = result[-1]
            curr = chunks[i]

            overlap_text = self._last_n_tokens_text(prev.text, self._chunk_overlap)
            if not overlap_text:
                result.append(curr)
                continue

            new_text = (overlap_text + "\n\n" + curr.text).strip()
            # Start index moves backwards in a true offset world, but we don't know the
            # exact char offsets for token overlap; keep curr.start_index to avoid lying.
            result.append(
                Chunk(
                    text=new_text,
                    start_index=curr.start_index,
                    end_index=curr.end_index,
                    token_count=self._count_tokens(new_text),
                    metadata=curr.metadata,
                )
            )
        return result

    def _last_n_tokens_text(self, text: str, n: int) -> str:
        # Approximate by whitespace tokens; good enough for overlap context.
        toks = re.findall(r"\S+", text)
        if not toks:
            return ""
        return " ".join(toks[-n:])

    # -----------------------------
    # Helpers
    # -----------------------------

    def _count_tokens(self, text: str) -> int:
        if not text:
            return 0
        # Token-count by summing token_count from Chonkie's output.
        # With very large chunk_size, most texts will be 1 chunk, but sum is robust.
        return sum(c.token_count for c in self._token_counter.chunk(text))

    def _is_operator(self, t: Turn) -> bool:
        return t.speaker.strip().lower() == "operator"

    def _format_turn(self, t: Turn) -> str:
        # Standardize formatting for downstream retrieval.
        body = t.text.strip()
        if not body:
            return f"{t.speaker}:"
        return f"{t.speaker}: {body}"


if __name__ == "__main__":
    from app.repositories.transcripts_data import get_latest_transcript
    from prophitai_foundry.models.metadata import EarningsCallMetadata
    chunker = EarningsCallChunker()
    transcript = get_latest_transcript("CRWV")
    print(transcript["content"][:1000])
    chunks = chunker.chunk(
        transcript["content"], 
        doc_type="earnings_call",
        metadata=EarningsCallMetadata.from_transcript(transcript).to_chunk_metadata(),
    )
    print(f"Generated {len(chunks)} chunks")
    for chunk in chunks:
        print(chunk.metadata)
        print(chunk.text)
        print("--------------------------------")