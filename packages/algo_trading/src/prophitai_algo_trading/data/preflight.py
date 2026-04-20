"""Pre-backtest data health check.

Runs after ``DataResolver.resolve()`` populates ``df.attrs`` and before the
backtest engine consumes the data. Validates that every declared
``DataRequirement`` is actually populated across enough of the universe —
``scope="per_ticker"`` checks per-ticker presence; ``scope="shared"`` checks
that the single blob is non-None and non-empty.

A pipeline that produces a backtest from half-loaded data looks "successful"
to the validator, which then spends 12 tuning runs on corrupted signals.
Failing fast here turns every such run into a single, diagnostic
``DataCoverageError`` the validator recognises as ``build_failure``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from prophitai_algo_trading.indicators.data_requirements import DataRequirement
from prophitai_algo_trading.indicators.pipeline import BaseIndicatorSuite

logger = logging.getLogger(__name__)


# ================================
# --> Helper funcs
# ================================


def _is_blob_populated(value: Any) -> bool:
    """Return True when a shared-attr blob is usably populated."""

    if value is None:
        return False

    if isinstance(value, (pd.DataFrame, pd.Series)):
        return not value.empty

    if isinstance(value, dict):
        return len(value) > 0

    return True


def _collect_requirements(suite: BaseIndicatorSuite) -> list[DataRequirement]:
    """Walk the suite and return deduplicated DataRequirements.

    Mirrors ``DataResolver.collect_requirements`` so preflight can run
    independently without requiring a resolver instance.
    """

    from prophitai_algo_trading.data.resolver import DataResolver

    resolver = DataResolver()

    return resolver.collect_requirements(suite)


# ================================
# --> Errors
# ================================


@dataclass
class CoverageFailure:
    """One failed coverage check, used in DataCoverageError payloads."""

    attrs_key: str
    kind: str
    scope: str
    min_coverage: float
    actual_coverage: float
    missing_tickers: list[str] = field(default_factory=list)
    detail: str = ""

    def describe(self) -> str:
        """One-line human-readable summary of the failure."""

        base = (
            f"{self.attrs_key!r} (kind={self.kind}, scope={self.scope}) "
            f"coverage={self.actual_coverage:.0%} < required={self.min_coverage:.0%}"
        )

        if self.missing_tickers:
            sample = ", ".join(self.missing_tickers[:10])
            suffix = f" missing {len(self.missing_tickers)}: [{sample}"
            suffix += "..." if len(self.missing_tickers) > 10 else ""
            suffix += "]"

            return base + suffix

        if self.detail:
            return f"{base} ({self.detail})"

        return base


class DataCoverageError(RuntimeError):
    """Raised when one or more DataRequirements fail their coverage gate.

    The validator catches this specifically and emits a ``build_failure``
    verdict — no tuning, no signal tweaks, just a report of which data
    source failed and for which tickers.
    """

    def __init__(self, failures: list[CoverageFailure]):
        self.failures = failures
        lines = [f.describe() for f in failures]
        message = "Pre-backtest data health check failed:\n  - " + "\n  - ".join(lines)

        super().__init__(message)


# ================================
# --> Preflight check
# ================================


def preflight_check(
    suite: BaseIndicatorSuite,
    data: dict[str, pd.DataFrame],
    *,
    universe_min_size: int = 5,
) -> None:
    """Validate that declared data requirements loaded for enough of the universe.

    Args:
        suite: The strategy's indicator suite.
        data: Dict of {ticker: DataFrame} returned by the resolver, with
            ``df.attrs`` already populated (or not).
        universe_min_size: Minimum number of tickers that must have OHLCV data
            loaded. Defaults to 5 — anything lower is structurally unusable.

    Raises:
        DataCoverageError: One or more requirements failed their coverage gate.
    """

    if len(data) < universe_min_size:
        failures = [
            CoverageFailure(
                attrs_key="<universe>",
                kind="price_data",
                scope="universe",
                min_coverage=universe_min_size / max(len(data), 1),
                actual_coverage=float(len(data)),
                detail=f"only {len(data)} tickers loaded OHLCV, need >= {universe_min_size}",
            )
        ]

        raise DataCoverageError(failures)

    requirements = _collect_requirements(suite)

    if not requirements:
        return

    failures: list[CoverageFailure] = []
    universe_size = len(data)
    tickers = list(data.keys())

    for req in requirements:
        if req.scope == "per_ticker":
            missing = [
                ticker
                for ticker in tickers
                if not _is_blob_populated(data[ticker].attrs.get(req.attrs_key))
            ]
            populated = universe_size - len(missing)
            coverage = populated / universe_size

            if coverage < req.min_coverage:
                failures.append(
                    CoverageFailure(
                        attrs_key=req.attrs_key,
                        kind=req.kind,
                        scope=req.scope,
                        min_coverage=req.min_coverage,
                        actual_coverage=coverage,
                        missing_tickers=missing,
                    )
                )
        else:
            # Reason: scope="shared" — same blob should be on every ticker. We
            # probe a single ticker (the first one) to decide present/absent.
            first = data[tickers[0]]
            populated = _is_blob_populated(first.attrs.get(req.attrs_key))
            coverage = 1.0 if populated else 0.0

            if coverage < req.min_coverage:
                failures.append(
                    CoverageFailure(
                        attrs_key=req.attrs_key,
                        kind=req.kind,
                        scope=req.scope,
                        min_coverage=req.min_coverage,
                        actual_coverage=coverage,
                        detail=(
                            f"shared blob missing (params={req.params}); "
                            f"provider returned None/empty"
                        ),
                    )
                )

    if failures:
        raise DataCoverageError(failures)
