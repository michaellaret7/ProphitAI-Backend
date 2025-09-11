from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class EpisodicMemory:
    """Simple JSON-backed episodic memory store.

    - Stores a list of event objects in a JSON file
    - Each entry minimally includes: timestamp, title, event
    - Optional fields: context, outcome, tags, meta
    - Provides reset, append, recall, get_latest, summarize_older
    """

    def __init__(
        self,
        path: Optional[Union[str, Path]] = None,
        *,
        reset_on_init: bool = False,
    ) -> None:
        # Default to sibling memory_store/episodic_memory.json
        if path is None:
            path = Path(__file__).parent / "memory_store" / "episodic_memory.json"

        self.path: Path = Path(path)
        self._ensure_storage()

        if reset_on_init:
            self.reset()

    # Public API -----------------------------------------------------------------
    def reset(self) -> None:
        """Overwrite memory file with an empty list."""
        self._save([])

    def append(
        self,
        title: str,
        event: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        outcome: Optional[Union[str, Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Append a new episodic entry and return it.

        Args:
            title: Short human-readable label (e.g., "Portfolio V1 published")
            event: Machine-oriented event key (e.g., "portfolio_version_published")
            context: Arbitrary details about inputs/state
            outcome: Result snapshot (string or dict)
            tags: Optional tags for retrieval (e.g., ["cio","portfolio"]) 
            meta: Extra metadata (e.g., component, version)
        """
        if not isinstance(title, str) or not title.strip():
            raise ValueError("'title' must be a non-empty string")
        if not isinstance(event, str) or not event.strip():
            raise ValueError("'event' must be a non-empty string")

        entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "title": title.strip(),
            "event": event.strip(),
        }

        if context is not None:
            if not isinstance(context, dict):
                raise ValueError("'context' must be a dictionary if provided")
            entry["context"] = context

        if outcome is not None:
            if not isinstance(outcome, (str, dict)):
                raise ValueError("'outcome' must be a string or dictionary if provided")
            entry["outcome"] = outcome

        if tags is not None:
            if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
                raise ValueError("'tags' must be a list of strings if provided")
            entry["tags"] = tags

        if meta is not None:
            if not isinstance(meta, dict):
                raise ValueError("'meta' must be a dictionary if provided")
            entry["meta"] = meta

        entries = self._load()
        # If an entry exists with the same title, replace/update it by
        # removing the old one(s) and appending the new entry
        title_key = entry["title"]
        entries = [e for e in entries if e.get("title") != title_key]
        entries.append(entry)
        self._save(entries)
        return entry

    def recall(
        self,
        *,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        since: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Return recent entries filtered by naive keyword, tags, and time.

        - query: substring (case-insensitive) matched against title, event, and JSON of context/outcome/meta
        - tags: at least one overlapping tag
        - since: ISO timestamp; only entries at or after this time
        - limit: max number of entries returned (most recent first)
        """
        entries = self._load()
        q = (query or "").strip().lower()
        tagset = set(t.lower() for t in (tags or []))
        since_dt = self._parse_dt(since) if since else None

        def matches(e: Dict[str, Any]) -> bool:
            if since_dt:
                ts = self._parse_dt(e.get("timestamp"))
                if ts is None or ts < since_dt:
                    return False

            if tagset:
                etags = set(t.lower() for t in e.get("tags", []) if isinstance(t, str))
                if not (etags & tagset):
                    return False

            if q:
                # Search title/event quickly
                if q in (e.get("title", "").lower()) or q in (e.get("event", "").lower()):
                    return True
                # Fall back to scanning JSON payloads
                payload = json.dumps({
                    "context": e.get("context"),
                    "outcome": e.get("outcome"),
                    "meta": e.get("meta"),
                }, default=str).lower()
                return q in payload
            return True

        # Most recent first
        filtered = [x for x in entries if matches(x)]
        filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return filtered[: max(0, limit)]

    def get_latest(self, tag_or_event: str) -> Optional[Dict[str, Any]]:
        """Return the most recent entry with matching tag OR event/title substring."""
        if not tag_or_event:
            return None
        key = tag_or_event.strip().lower()

        entries = self._load()
        for e in reversed(entries):
            ev = str(e.get("event", "")).lower()
            title = str(e.get("title", "")).lower()
            etags = [str(t).lower() for t in e.get("tags", []) if isinstance(t, str)]
            if key == ev or key in title or key in etags:
                return e
        return None

    def summarize_older(self, cutoff_n: int = 300) -> Optional[Dict[str, Any]]:
        """Summarize entries older than the last cutoff_n entries into a single entry.

        Creates one summary entry containing the time range and count of summarized items.
        Returns the summary entry if summarization occurred; otherwise None.
        """
        if cutoff_n <= 0:
            return None

        entries = self._load()
        if len(entries) <= cutoff_n:
            return None

        keep_tail = entries[-cutoff_n:]
        summarized_block = entries[:-cutoff_n]

        oldest_ts = summarized_block[0].get("timestamp") if summarized_block else None
        newest_ts = summarized_block[-1].get("timestamp") if summarized_block else None

        summary: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "title": "Summarized older episodic entries",
            "event": "episodic_summary",
            "context": {
                "num_entries": len(summarized_block),
                "oldest_timestamp": oldest_ts,
                "newest_timestamp": newest_ts,
            },
            "tags": ["episodic", "summary"],
            "meta": {"cutoff_n": cutoff_n},
        }

        # Store summary + tail, keeping chronology simple (summary first)
        new_entries = [summary] + keep_tail
        self._save(new_entries)
        return summary

    # Internal helpers -----------------------------------------------------------
    def _ensure_storage(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save([])

    def _load(self) -> List[Dict[str, Any]]:
        try:
            raw = self.path.read_text(encoding="utf-8").strip()
            if not raw:
                return []
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            return []
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            # If corrupted, do not raise during runtime; return empty
            return []

    def _save(self, entries: List[Dict[str, Any]]) -> None:
        text = json.dumps(entries, ensure_ascii=False, indent=2)
        self.path.write_text(text, encoding="utf-8")

    def _parse_dt(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None

