"""Super-simple event backtest using advanced rules and sizing."""

from datetime import datetime

from prophitai_algo_trading.data.repository.price_data import get_price_data_df
from prophitai_algo_trading.engines.backtest.event_driven import BacktestEngine
from prophitai_algo_trading.rules import (
    QualityGateRule,
)
from prophitai_algo_trading.sizing import ATRRiskSizer, DrawdownScaledSizer
from prophitai_algo_trading.strategies.orb_breakout import ORBBreakout

TICKERS = ["AAPL", "NVDA", "MSFT", "GOOGL", "JPM", "XOM", "PG", "UNH", "HD", "CAT"]
START = datetime(2025, 1, 1)
END = datetime(2026, 3, 1)

def main() -> None:
    print("Fetching data...")
    data = {}
    for t in TICKERS:
        df = get_price_data_df(t, START, END, "15min")
        if not df.empty:
            data[t] = df
            print(f"  {t}: {len(df)} bars")

    sizer = DrawdownScaledSizer(
        base_sizer=ATRRiskSizer(
            risk_pct=0.008,
            atr_multiple=1.0,
            max_pct_equity=0.15,
        ),
        soft_drawdown=0.05,
        hard_drawdown=0.15,
        min_scale=0.35,
    )

    engine = BacktestEngine(
        strategy=ORBBreakout(),
        initial_capital=100_000,
        sizer=sizer,
        max_positions=min(5, len(data)),
        rules=[
            QualityGateRule(
                min_score_percentile=0.35,
                min_volume_ratio=1.1,
                stop_loss_pct=0.025,
                trail_after_profit_pct=0.015,
                trailing_stop_pct=0.03,
                max_bars_in_trade=26,
                cooldown_bars_after_exit=4,
            ),
        ],
    )

    result = engine.run(data, verbose=True)

    print("\n=== METRICS ===")
    for k, v in result.metrics.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
