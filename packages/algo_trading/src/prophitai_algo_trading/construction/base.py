"""``BasePCM`` — shared scaffolding for PortfolioConstructionModels.

Single base class that standardizes the cross-cutting concerns every PCM
needs (rebalance cadence, provenance enrichment, orphan-close handling)
without forcing the construction algorithm. Subclasses follow one of two
contracts:

    Constructor pattern (3 of 4 in-tree PCMs):
        Subclass ``BasePCM``, implement ``_build(ctx, insights) ->
        BuildResult``. The base wraps your build with the standard
        skeleton: rebalance gate -> _build -> append_close_orphans ->
        ProvenanceTracker.enrich.

    Wrapper pattern (e.g. ``MultiAlphaBlendPCM``):
        Subclass ``BasePCM``, override ``create_targets`` directly. Use
        ``self._provenance`` for attribution. The default skeleton is
        skipped because wrapper construction shape is "transform insights
        -> delegate to inner -> enrich" — different from the constructor
        pipeline.

Both paths inherit ``self._provenance``, ``self._scheduler``, and any
future cross-cutting concerns added to the base. That's the alignment
guarantee: one place to add new universal behavior, every PCM picks it
up automatically.

The vectorized engine path (``build_weights``) is also declared here so
the contract is visible side-by-side with the event-driven path.
Subclasses implement the vectorized path independently when they want
to support the panel-based engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.models import (
        AlgorithmContext,
        Insight,
        PortfolioTarget,
    )

from prophitai_algo_trading.construction.helpers.event import (
    RebalanceScheduler,
    append_close_orphans,
)
from prophitai_algo_trading.construction.provenance import (
    ProvenanceTracker,
)


#     ================================
# --> Build result
#     ================================

@dataclass
class BuildResult:
    """Output of ``BasePCM._build``.

    Carries everything the base needs to enrich and emit targets. Using
    a dataclass over a positional triple keeps the contract forward-
    compatible — adding a new attribution dimension later is a field
    with a default, not a breaking signature change.

    Attributes:
        targets: Chosen targets — the *new* book this rebalance.
            Orphan closes (held symbols not in the new book) are
            appended automatically by the base. Don't include them
            here.
        contributions: ``{symbol: {alpha_name: signed_contribution}}``
            for every chosen non-zero target. For non-blending PCMs
            each entry is ``{source_alpha: 1.0}``; for blending PCMs
            each value is the alpha's signed contribution to the
            symbol's composite.
        scores: ``{symbol: signed_score}`` for every symbol with an
            insight this bar (chosen and not-chosen). Lets the
            provenance tracker classify orphan closes into
            ``cohort_drop`` (no insight) vs ``magnitude_decay``
            (insight present but didn't make the book).
        flush_reason: Optional opt-in label that overrides the
            classifier for *every* zero-target this bar. Use for PCMs
            that intentionally flush on a schedule (set to
            ``"pcm_rebalance"``).
    """

    targets: list["PortfolioTarget"]
    contributions: dict[str, dict[str, float]] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)
    flush_reason: str | None = None


#     ================================
# --> Base PCM
#     ================================

class BasePCM:
    """Shared scaffolding for PCMs — cadence, provenance, orphan-close.

    Args:
        rebalance_every: How often to emit new targets. ``None`` = every
            bar (most responsive, highest churn). For wrappers, pass
            ``None`` since cadence gating belongs to the inner PCM.
    """

    def __init__(self, rebalance_every: timedelta | None = None):
        self._scheduler = RebalanceScheduler(rebalance_every)
        self._provenance = ProvenanceTracker()

    #     ================================
    # --> Event-driven path
    #     ================================

    def create_targets(
        self,
        ctx: "AlgorithmContext",
        insights: list["Insight"],
    ) -> list["PortfolioTarget"]:
        """Default constructor-pattern skeleton.

        Pipeline:
            1. Rebalance gate — return ``[]`` on non-rebalance bars.
            2. Subclass's ``_build`` produces chosen targets +
               contributions + scores.
            3. ``append_close_orphans`` adds zero-targets for held
               symbols not in the new book.
            4. ``ProvenanceTracker.enrich`` stamps ``entry_alphas`` /
               ``exit_reason`` on every target.

        Wrapper PCMs (e.g. ``MultiAlphaBlendPCM``) override this method
        directly because their shape is "transform insights -> delegate
        -> enrich," which doesn't fit the skeleton.
        """
        if not self._scheduler.is_rebalance_bar(ctx.timestamp):
            return []

        result = self._build(ctx, insights)

        full_targets = append_close_orphans(ctx, result.targets)

        return self._provenance.enrich(
            full_targets,
            result.contributions,
            result.scores,
            ctx.portfolio,
            flush_reason=result.flush_reason,
        )

    def _build(
        self,
        ctx: "AlgorithmContext",
        insights: list["Insight"],
    ) -> BuildResult:
        """Constructor-pattern PCMs implement this.

        Returns ``BuildResult(targets, contributions, scores)`` where
        ``targets`` is the *new* book (orphan closes are appended by the
        base). Wrapper PCMs override ``create_targets`` instead and
        leave this raising.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must either implement _build() "
            "(for constructor PCMs) or override create_targets() "
            "directly (for wrapper PCMs).",
        )

    #     ================================
    # --> Vectorized path
    #     ================================

    def build_weights(
        self, scores: dict[str, "pd.DataFrame"],
    ) -> "pd.DataFrame":
        """Vectorized panel-based construction for the vector engine.

        Consumes ``{alpha_name: score_panel}`` and returns a dense
        ``[date x ticker]`` signed weight panel. Subclasses that want
        to support the vectorized engine implement this; subclasses
        that don't can leave it raising.
        """
        raise NotImplementedError(
            f"{type(self).__name__} doesn't support the vectorized "
            "engine. Implement build_weights() to enable it.",
        )
