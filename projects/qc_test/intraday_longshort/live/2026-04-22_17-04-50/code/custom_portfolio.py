"""Dollar-neutral long/short portfolio construction.

Takes a dict of {symbol: composite_score} and returns target weights:
  * Long the bottom quintile (most oversold composite score)
  * Short the top quintile (most overbought composite score)
  * Equal-weight within each side
  * Dollar-neutral (long $ = short $)
  * Capped by gross_exposure and per-position size
"""


class DollarNeutralLongShortConstruction:
    """Rank-based dollar-neutral portfolio builder."""

    def __init__(
        self,
        gross_exposure: float = 1.8,
        per_position_cap: float = 0.10,
        long_short_quantile: float = 0.2,
    ) -> None:
        self.gross_exposure = gross_exposure
        self.per_position_cap = per_position_cap
        self.quantile = long_short_quantile

    def build(self, scores: dict) -> dict:
        """Return {symbol: target_weight} with longs positive, shorts negative.

        Args:
            scores: mapping of symbol -> composite score (higher = more overbought).
        """
        if not scores:
            return {}

        ranked = sorted(scores.items(), key=lambda kv: kv[1])

        n = len(ranked)
        k = max(1, int(n * self.quantile))

        longs = [sym for sym, _ in ranked[:k]]
        shorts = [sym for sym, _ in ranked[-k:]]

        if not longs or not shorts:
            return {}

        side_budget = self.gross_exposure / 2.0

        long_weight = min(self.per_position_cap, side_budget / len(longs))
        short_weight = -min(self.per_position_cap, side_budget / len(shorts))

        targets: dict = {}

        for sym in longs:
            targets[sym] = long_weight

        for sym in shorts:
            targets[sym] = short_weight

        return targets
