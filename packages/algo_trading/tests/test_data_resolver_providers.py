"""Real-data smoke test for the three new DataResolver providers.

Builds a throwaway indicator suite with one probe indicator per new kind
(``equity_price``, ``ticker_meta``, ``universe_returns``), runs
``load_strategy_data`` against real database prices for AAPL and MSFT, and
asserts each ticker's ``df.attrs`` is populated with the expected shape.

Run directly: ``python packages/algo_trading/tests/test_data_resolver_providers.py``
"""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.data.resolver import load_strategy_data
from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_algo_trading.indicators.data_requirements import DataRequirement
from prophitai_algo_trading.indicators.pipeline import BaseIndicatorSuite
from prophitai_algo_trading.indicators.specs import IndicatorSpec


# ================================
# --> Probe indicators
# ================================


class _EquityPriceProbe(BaseIndicator):
    data_requirements = (
        DataRequirement(
            kind="equity_price",
            attrs_key="spy",
            scope="shared",
            params={"symbol": "SPY"},
        ),
    )

    def calculate(self) -> pd.DataFrame:
        return self.df


class _TickerMetaProbe(BaseIndicator):
    data_requirements = (
        DataRequirement(
            kind="ticker_meta",
            attrs_key="ticker_meta",
            scope="per_ticker",
        ),
    )

    def calculate(self) -> pd.DataFrame:
        return self.df


class _UniverseReturnsProbe(BaseIndicator):
    data_requirements = (
        DataRequirement(
            kind="universe_returns",
            attrs_key="universe_returns",
            scope="shared",
            params={"return_type": "pct"},
        ),
    )

    def calculate(self) -> pd.DataFrame:
        return self.df


class _ProbeSuite(BaseIndicatorSuite):
    def indicator_specs(self):
        return [
            IndicatorSpec(indicator=_EquityPriceProbe, params={}, scope="per_ticker"),
            IndicatorSpec(indicator=_TickerMetaProbe, params={}, scope="per_ticker"),
            IndicatorSpec(indicator=_UniverseReturnsProbe, params={}, scope="per_ticker"),
        ]


# ================================
# --> Test runner
# ================================


def run() -> None:
    tickers = ["AAPL", "MSFT"]
    data = load_strategy_data(
        tickers,
        "2024-01-01",
        "2024-06-01",
        indicator_suite=_ProbeSuite(),
    )

    assert set(data.keys()) == set(tickers), f"missing tickers in data dict: {set(data.keys())}"

    for ticker, df in data.items():
        spy = df.attrs.get("spy")
        assert isinstance(spy, pd.Series), f"{ticker}: df.attrs['spy'] not a Series (got {type(spy)})"
        assert len(spy) > 50, f"{ticker}: SPY series too short ({len(spy)} points)"

        meta = df.attrs.get("ticker_meta")
        assert isinstance(meta, dict), f"{ticker}: df.attrs['ticker_meta'] not a dict (got {type(meta)})"
        assert meta.get("symbol") == ticker, f"{ticker}: symbol mismatch in {meta}"
        assert meta.get("sector"), f"{ticker}: empty sector in {meta}"
        assert "industry" in meta, f"{ticker}: missing industry key in {meta}"

        returns = df.attrs.get("universe_returns")
        assert isinstance(returns, pd.DataFrame), (
            f"{ticker}: df.attrs['universe_returns'] not a DataFrame (got {type(returns)})"
        )
        assert set(returns.columns) >= set(tickers), (
            f"{ticker}: universe_returns missing columns; got {list(returns.columns)}"
        )
        assert len(returns) > 50, f"{ticker}: universe_returns too short ({len(returns)} rows)"

    print("OK")
    for ticker, df in data.items():
        print(f"  {ticker}: attrs={sorted(df.attrs.keys())}")


if __name__ == "__main__":
    run()
