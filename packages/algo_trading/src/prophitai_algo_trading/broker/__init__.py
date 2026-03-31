"""Broker integrations for order execution."""

__all__: list[str] = []

try:
    from prophitai_algo_trading.broker.alpaca import Alpaca
except ModuleNotFoundError:
    Alpaca = None  # type: ignore[assignment]
else:
    __all__.append("Alpaca")
