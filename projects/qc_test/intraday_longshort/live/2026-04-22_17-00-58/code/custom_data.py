"""Custom PythonData: 15-minute OHLCV bars sourced from ProphitAI's market_data DB.

CSVs are written by `scripts/export_data.py` to
`data/alternative/prophitai/bars_15min/<TICKER>.csv` with schema:

    date,time,open,high,low,close,volume

where `date` is YYYY-MM-DD and `time` is HH:MM:SS at the bar's START
(e.g. 09:30:00 for the 09:30-09:45 bar). Lean streams these as
Resolution.MINUTE subscriptions — bars simply arrive every 15 minutes.
"""
from datetime import datetime, timedelta

from AlgorithmImports import (
    FileFormat,
    PythonData,
    SubscriptionDataSource,
    SubscriptionTransportMedium,
)


#     ================================
# --> Bar class
#     ================================

class ProphitAI15MinBar(PythonData):
    """One 15-min OHLCV bar for a single ticker."""

    def get_source(self, config, date, is_live_mode):
        path = f"/Lean/Data/alternative/prophitai/bars_15min/{config.Symbol.Value}.csv"

        return SubscriptionDataSource(
            path,
            SubscriptionTransportMedium.LocalFile,
            FileFormat.Csv,
        )

    def reader(self, config, line, date, is_live_mode):
        if not line or line[0].isalpha():
            return None

        parts = line.split(",")

        if len(parts) < 7:
            return None

        bar = ProphitAI15MinBar()
        bar.Symbol = config.Symbol

        start = datetime.strptime(f"{parts[0]} {parts[1]}", "%Y-%m-%d %H:%M:%S")

        # Reason: EndTime marks when the bar becomes available to the strategy.
        # We set it to start + 15min so Lean emits the bar at the bar's close.
        bar.Time = start
        bar.EndTime = start + timedelta(minutes=15)

        bar["open"] = float(parts[2])
        bar["high"] = float(parts[3])
        bar["low"] = float(parts[4])
        bar["close"] = float(parts[5])
        bar["volume"] = float(parts[6])

        bar.Value = float(parts[5])

        return bar
