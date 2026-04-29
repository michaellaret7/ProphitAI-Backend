"""Construction-stage helpers, split by paradigm.

``event``  — utilities for the bar-driven stage
            (``RebalanceScheduler``, ``weight_to_shares``,
            ``append_close_orphans``).

``vector`` — utilities for the vectorized stage
            (``apply_cadence``, ``zscore_rowwise``,
            ``rank_to_long_short_weights``).
"""
