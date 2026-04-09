"""Deterministic testing infrastructure for composable trading strategies.

Usage — a strategy repo writes ONE test file::

    from prophitai_algo_trading.testing import (
        StrategyTestManifest,
        IndicatorSuiteContract,
        SignalModelContract,
        ConfigContract,
        StrategyContract,
        LeakageContract,
    )

    class TestMyStrategy(
        IndicatorSuiteContract,
        SignalModelContract,
        ConfigContract,
        StrategyContract,
        LeakageContract,
    ):
        manifest = StrategyTestManifest(
            name="MyStrategy",
            build_strategy=lambda: MyStrategy(MyConfig()),
            config_class=MyConfig,
            min_warmup_bars=50,
        )

Pytest discovers all ``test_*`` methods from the inherited mixins.
"""

from prophitai_algo_trading.testing.contracts import (
    ConfigContract,
    IndicatorSuiteContract,
    LeakageContract,
    RiskControlContract,
    SignalModelContract,
    StrategyContract,
)
from prophitai_algo_trading.testing.fixtures import (
    OHLCV_COLS,
    downtrend,
    flat,
    gap_down,
    gap_up,
    make_ohlcv,
    mean_reverting,
    uptrend,
    volatile_breakout,
)
from prophitai_algo_trading.testing.manifest import StrategyTestManifest

__all__ = [
    # Manifest
    "StrategyTestManifest",
    # Fixtures
    "OHLCV_COLS",
    "downtrend",
    "flat",
    "gap_down",
    "gap_up",
    "make_ohlcv",
    "mean_reverting",
    "uptrend",
    "volatile_breakout",
    # Contracts
    "ConfigContract",
    "IndicatorSuiteContract",
    "LeakageContract",
    "RiskControlContract",
    "SignalModelContract",
    "StrategyContract",
]
