"""Violation records emitted by the manifest-check validator."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class ManifestViolation:
    """One problem found in a strategy's manifest or generated code.

    Attributes:
        code: Stable error identifier (e.g. ``"M001_UNKNOWN_DATA_KIND"``).
            Referenced by the framework reference doc and agent prompts.
        severity: ``"error"`` blocks handoff; ``"warning"`` is informational.
        path: Path the violation refers to, relative to the strategy dir
            when it is a file, or ``"MANIFEST.json"`` / ``"<manifest>"``
            for manifest-level issues.
        message: One-line human-readable description ending with the
            suggested fix.
    """

    code: str
    severity: Severity
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)
