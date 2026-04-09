"""Contract test mixins for composable trading strategies.

Inherit from these classes in your test file and set a ``manifest``
class attribute.  Pytest collects all ``test_*`` methods automatically.
"""

from prophitai_algo_trading.testing.contracts.config import ConfigContract
from prophitai_algo_trading.testing.contracts.constants import SIGNAL_KEYS
from prophitai_algo_trading.testing.contracts.indicators import IndicatorSuiteContract
from prophitai_algo_trading.testing.contracts.leakage import LeakageContract
from prophitai_algo_trading.testing.contracts.risk import RiskControlContract
from prophitai_algo_trading.testing.contracts.signals import SignalModelContract
from prophitai_algo_trading.testing.contracts.strategy import StrategyContract

__all__ = [
    "SIGNAL_KEYS",
    "ConfigContract",
    "IndicatorSuiteContract",
    "LeakageContract",
    "RiskControlContract",
    "SignalModelContract",
    "StrategyContract",
]
