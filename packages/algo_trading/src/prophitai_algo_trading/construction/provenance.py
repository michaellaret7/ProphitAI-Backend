"""``ProvenanceTracker`` — shared trade-attribution helper for PCMs.

Centralizes the ``entry_alphas`` + PCM-induced ``exit_reason`` enrichment
so every PCM gets the same provenance contract for free. Each PCM holds
its own ``ProvenanceTracker`` instance and calls ``enrich(targets,
contributions, scores, portfolio)`` at the end of ``create_targets``.

Contract:
    contributions: ``{symbol: {alpha_name: signed_contribution}}`` —
        keyed by chosen symbols only (non-zero targets). For non-blending
        PCMs each chosen symbol is ``{source_alpha: 1.0}``; for blending
        PCMs each value is the alpha's signed contribution to the
        symbol's composite score.
    scores: ``{symbol: signed_score}`` — keyed by every symbol with an
        insight this bar (chosen *and* not-chosen). Lets the classifier
        split ``cohort_drop`` (no insight at all) from ``magnitude_decay``
        (insight present but didn't make the book).
    flush_reason: ``"pcm_rebalance"`` (or any opt-in string) — when set,
        every zero-target gets stamped with this reason instead of
        running through the per-symbol classifier.

Outputs:
    Replaces non-zero targets with ``entry_alphas`` populated and
    zero-targets with ``exit_reason`` populated. Updates ``_last_scores``
    as a side effect so the next bar can detect sign-flips.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prophitai_algo_trading.portfolio.portfolio import Portfolio
    from prophitai_algo_trading.core.models import PortfolioTarget


_DEFAULT_EPSILON = 0.05


class ProvenanceTracker:
    """Shared enrichment for ``entry_alphas`` and PCM-induced ``exit_reason``.

    Args:
        attribution_epsilon: Minimum normalized |contribution| for an
            alpha to appear in ``entry_alphas``. Filters noise from
            marginal contributors.
    """

    def __init__(self, attribution_epsilon: float = _DEFAULT_EPSILON):
        self._epsilon = attribution_epsilon
        self._last_scores: dict[str, float] = {}

    def enrich(
        self,
        targets: list["PortfolioTarget"],
        contributions: dict[str, dict[str, float]],
        scores: dict[str, float],
        portfolio: "Portfolio",
        flush_reason: str | None = None,
    ) -> list["PortfolioTarget"]:
        """Enrich a target list with provenance, then snapshot scores."""
        out: list["PortfolioTarget"] = []

        for target in targets:
            if target.target_shares != 0.0:
                entry_alphas = self._build_entry_alphas(
                    contributions.get(target.symbol, {}),
                )

                out.append(replace(target, entry_alphas=entry_alphas))
                continue

            if flush_reason is not None:
                out.append(replace(target, exit_reason=flush_reason))
                continue

            reason = self._classify_exit(target.symbol, scores, portfolio)

            out.append(replace(target, exit_reason=reason))

        self._last_scores = dict(scores)

        return out

    #     ================================
    # --> Internal
    #     ================================

    def _build_entry_alphas(
        self, per_alpha: dict[str, float],
    ) -> tuple[tuple[str, float], ...] | None:
        """Normalize signed contributions to fractions of total |composite|."""
        total_abs = sum(abs(c) for c in per_alpha.values())

        if total_abs <= 0.0:
            return None

        normalized = [
            (name, contrib / total_abs)
            for name, contrib in per_alpha.items()
            if abs(contrib / total_abs) > self._epsilon
        ]

        if not normalized:
            return None

        normalized.sort(key=lambda kv: -abs(kv[1]))

        return tuple(normalized)

    def _classify_exit(
        self,
        symbol: str,
        scores: dict[str, float],
        portfolio: "Portfolio",
    ) -> str:
        """Pick one of three PCM-induced subtypes for a zero-target close.

        Precedence:
            1. cohort_drop     — symbol absent from this bar's scores
               (no alpha emitted for it).
            2. alpha_reversal  — score sign is opposite the held direction
               or flipped vs the last bar's score.
            3. magnitude_decay — score same-sign but too weak to keep the
               symbol in the book.
        """
        if symbol not in scores:
            return "cohort_drop"

        score = scores[symbol]
        last_score = self._last_scores.get(symbol)

        position = portfolio.positions.get(symbol)
        held_direction = position.direction if position else 0

        if held_direction != 0 and score * held_direction < 0.0:
            return "alpha_reversal"

        if last_score is not None and score * last_score < 0.0:
            return "alpha_reversal"

        return "magnitude_decay"
