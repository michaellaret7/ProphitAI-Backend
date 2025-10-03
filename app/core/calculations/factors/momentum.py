from __future__ import annotations

from typing import Optional, Tuple, Dict

import numpy as np
import pandas as pd
import statsmodels.api as sm
from datetime import datetime, timedelta, timezone
from app.core.calculations.core.helpers import (
    winsorize_series,
    zscore_series,
    sector_zscore,
    residualize,
    compose_exposure,
)
from app.core.calculations.core.config import DEFAULT_SECTOR_COL, DEFAULT_WINSOR_LIMITS
from app.core.calculations.factors.config import MOMENTUM_WEIGHTS, MOMENTUM_LOOKBACK


class MomentumFactors:
    """Price-based momentum factors operating on simple Series inputs.

    Computes: 1/3/6/12-month returns (with optional 1M skip), % from 52w high,
    SMA ratio (fast/slow), SMA_50, SMA_200, MACD (value/signal), RSI,
    idiosyncratic momentum vs market or sector (optional), volume-adjusted momentum (optional).
    """

    def __init__(
        self,
        price_series: pd.Series,
        volume_series: Optional[pd.Series] = None,
        market_price_series: Optional[pd.Series] = None,
        sector_price_series: Optional[pd.Series] = None,
        dividends_series: Optional[pd.Series] = None,
    ):
        base_prices = price_series.astype(float)
        # Build total return price index if dividends are provided; otherwise use raw prices
        if dividends_series is not None:
            divs = dividends_series.astype(float).reindex(base_prices.index).fillna(0.0)
            price_shift = base_prices.shift(1)
            with np.errstate(divide='ignore', invalid='ignore'):
                total_ret = (base_prices + divs) / price_shift - 1.0
            total_ret = total_ret.replace([np.inf, -np.inf], np.nan).fillna(0.0)
            tr_index = (1.0 + total_ret).cumprod()
            self.prices = tr_index
        else:
            self.prices = base_prices
        self.returns = self.prices.pct_change(fill_method=None).dropna()
        self.volumes = volume_series.astype(float).reindex(self.prices.index) if volume_series is not None else None

        self.market_prices = market_price_series.astype(float).reindex(self.prices.index) if market_price_series is not None else None
        self.market_returns = self.market_prices.pct_change(fill_method=None).dropna() if self.market_prices is not None else None

        self.sector_prices = sector_price_series.astype(float).reindex(self.prices.index) if sector_price_series is not None else None
        self.sector_returns = self.sector_prices.pct_change(fill_method=None).dropna() if self.sector_prices is not None else None

    # ------------------------- helpers ------------------------- #
    @staticmethod
    def _window_return(prices: pd.Series, lookback: int, skip_end: int = 0) -> Optional[float]:
        """Total return over last `lookback` bars ending `skip_end` bars ago.

        Uses price ratio end/start - 1.0; expects adjusted prices if dividends are desired.
        """
        if prices is None or prices.empty:
            return None
        n = len(prices)
        end_idx = n - 1 - int(skip_end)
        start_idx = end_idx - int(lookback)
        if start_idx < 0 or end_idx < 0 or end_idx >= n:
            return None
        start = float(prices.iloc[start_idx])
        end = float(prices.iloc[end_idx])
        if start <= 0.0 or end <= 0.0:
            return None
        return float(end / start - 1.0)

    @staticmethod
    def _log_returns(series: pd.Series) -> pd.Series:
        if series is None or series.empty:
            return pd.Series(dtype=float)
        with np.errstate(divide='ignore', invalid='ignore'):
            lr = np.log(series / series.shift(1))
        return lr.replace([np.inf, -np.inf], np.nan).dropna()

    # ------------------------- returns windows ------------------------- #
    def one_month_return(self) -> Optional[float]:
        return self._window_return(self.prices, lookback=MOMENTUM_LOOKBACK["1M"], skip_end=0)

    def three_month_return(self, skip: int = None) -> Optional[float]:
        if skip is None:
            skip = MOMENTUM_LOOKBACK["SKIP_RECENT"]
        return self._window_return(self.prices, lookback=MOMENTUM_LOOKBACK["3M"], skip_end=skip)

    def six_month_return(self, skip: int = None) -> Optional[float]:
        if skip is None:
            skip = MOMENTUM_LOOKBACK["SKIP_RECENT"]
        return self._window_return(self.prices, lookback=MOMENTUM_LOOKBACK["6M"], skip_end=skip)

    def twelve_month_return_ex1m(self) -> Optional[float]:
        return self._window_return(self.prices, lookback=MOMENTUM_LOOKBACK["12M"], skip_end=MOMENTUM_LOOKBACK["SKIP_RECENT"])

    # Canonical ex-1m windows
    def r12_1(self) -> Optional[float]:
        return self.twelve_month_return_ex1m()

    def r6_1(self) -> Optional[float]:
        return self.six_month_return(skip=MOMENTUM_LOOKBACK["SKIP_RECENT"])

    def r3_1(self) -> Optional[float]:
        return self.three_month_return(skip=MOMENTUM_LOOKBACK["SKIP_RECENT"])

    # ------------------------- 52w high ------------------------- #
    def pct_from_52w_high(self, window: int = None) -> Optional[float]:
        if window is None:
            window = MOMENTUM_LOOKBACK["12M"]
        if len(self.prices) < window:
            return None
        highest = self.prices.iloc[-window:].max()
        curr = self.prices.iloc[-1]
        if highest == 0:
            return None
        return float(curr / highest - 1.0)

    # ------------------------- SMA ratio ------------------------- #
    def sma_ratio(self, fast: int = 50, slow: int = 200, latest_only: bool = True):
        if slow <= fast:
            raise ValueError("slow must be > fast")
        sma_f = self.prices.rolling(fast).mean()
        sma_s = self.prices.rolling(slow).mean()
        ratio = sma_f / sma_s - 1.0
        return ratio.iloc[-1] if latest_only else ratio

    def sma_50(self) -> Optional[float]:
        if len(self.prices) < 50:
            return None
        return float(self.prices.rolling(50).mean().iloc[-1])

    def sma_200(self) -> Optional[float]:
        if len(self.prices) < 200:
            return None
        return float(self.prices.rolling(200).mean().iloc[-1])

    # ------------------------- MACD ------------------------- #
    def macd(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[Optional[float], Optional[float]]:
        if len(self.prices) < slow_period + signal_period:
            return None, None
        ema_fast = self.prices.ewm(span=fast_period, adjust=False).mean()
        ema_slow = self.prices.ewm(span=slow_period, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        return float(macd_line.iloc[-1]), float(signal_line.iloc[-1])

    # ------------------------- RSI ------------------------- #
    def rsi(self, window: int = 14) -> Optional[float]:
        if len(self.prices) < window + 1:
            return None
        delta = self.prices.diff().dropna()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)
        avg_up = up.ewm(com=window - 1, adjust=False).mean()
        avg_down = down.ewm(com=window - 1, adjust=False).mean().replace(0, np.nan)
        if avg_down.isnull().all():
            return 0.0
        rs = avg_up / avg_down
        rsi_series = 100.0 - (100.0 / (1.0 + rs))
        return float(rsi_series.iloc[-1])

    # ------------------------- Idiosyncratic Momentum ------------------------- #
    def idiosyncratic_momentum(self, lookback: int = None) -> Optional[float]:
        if lookback is None:
            lookback = MOMENTUM_LOOKBACK["IDIO_LOOKBACK"]
        if self.market_returns is None:
            return None
        import statsmodels.api as sm
        combined = pd.concat([self.returns, self.market_returns], axis=1, keys=["asset", "market"]).dropna()
        if len(combined) < lookback:
            return None
        y = combined["asset"].iloc[-lookback:]
        x = sm.add_constant(combined["market"].iloc[-lookback:])
        model = sm.OLS(y, x, missing="drop").fit()
        resid = model.resid
        return float((1 + resid).prod() - 1)

    def sector_idiosyncratic_momentum(self, lookback: int = None) -> Optional[float]:
        if lookback is None:
            lookback = MOMENTUM_LOOKBACK["IDIO_LOOKBACK"]
        if self.sector_returns is None:
            return None
        import statsmodels.api as sm
        combined = pd.concat([self.returns, self.sector_returns], axis=1, keys=["asset", "sector"]).dropna()
        if len(combined) < lookback:
            return None
        y = combined["asset"].iloc[-lookback:]
        x = sm.add_constant(combined["sector"].iloc[-lookback:])
        model = sm.OLS(y, x, missing="drop").fit()
        resid = model.resid
        return float((1 + resid).prod() - 1)

    # ------------------------- Residual Momentum (log, ex-1m) ------------------------- #
    def idiosyncratic_momentum_log(self, lookback: int = None, skip_end: int = None) -> Optional[float]:
        """Log-based residual momentum vs market over window excluding last month."""
        if lookback is None:
            lookback = MOMENTUM_LOOKBACK["12M"]
        if skip_end is None:
            skip_end = MOMENTUM_LOOKBACK["SKIP_RECENT"]
        if self.market_prices is None:
            return None
        import statsmodels.api as sm
        lr = self._log_returns(self.prices)
        lm = self._log_returns(self.market_prices)
        df = pd.concat([lr, lm], axis=1, keys=["a", "m"]).dropna()
        if len(df) < lookback + skip_end:
            return None
        window = df.iloc[-(lookback + skip_end): -skip_end]
        X = sm.add_constant(window["m"]).astype(float)
        y = window["a"].astype(float)
        try:
            res = sm.OLS(y, X, missing="drop").fit()
            S = float(res.resid.sum())
            return float(np.expm1(S))
        except Exception:
            return None

    def sector_idiosyncratic_momentum_log(self, lookback: int = None, skip_end: int = None) -> Optional[float]:
        if lookback is None:
            lookback = MOMENTUM_LOOKBACK["12M"]
        if skip_end is None:
            skip_end = MOMENTUM_LOOKBACK["SKIP_RECENT"]
        if self.sector_prices is None:
            return None
        lr = self._log_returns(self.prices)
        ls = self._log_returns(self.sector_prices)
        df = pd.concat([lr, ls], axis=1, keys=["a", "s"]).dropna()
        if len(df) < lookback + skip_end:
            return None
        window = df.iloc[-(lookback + skip_end): -skip_end]
        X = sm.add_constant(window["s"]).astype(float)
        y = window["a"].astype(float)
        try:
            res = sm.OLS(y, X, missing="drop").fit()
            S = float(res.resid.sum())
            return float(np.expm1(S))
        except Exception:
            return None

    # ------------------------- Attributes & composite ------------------------- #
    def compute_attributes(self) -> dict:
        return {
            "r12_1": self.r12_1(),
            "r6_1": self.r6_1(),
            "r3_1": self.r3_1(),
            "idio_mom": self.idiosyncratic_momentum_log(),
        }

    @classmethod
    def compose_momentum_exposure(
        cls,
        df: pd.DataFrame,
        sector_col: str = DEFAULT_SECTOR_COL,
        winsor_limits: tuple[float, float] = DEFAULT_WINSOR_LIMITS,
        weights: Optional[dict] = None,
        output_col: str = "momentum_exposure_raw",
    ) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        cols = ["r12_1", "r6_1", "idio_mom"]
        if not weights:
            weights = MOMENTUM_WEIGHTS
        return compose_exposure(
            df,
            cols=cols,
            weights=weights,
            sector_col=sector_col,
            winsor_limits=winsor_limits,
            output_col=output_col,
        )

    @classmethod
    def orthogonalize_momentum(
        cls,
        df: pd.DataFrame,
        exposure_col: str = "momentum_exposure_raw",
        beta_col: Optional[str] = None,
        size_col: Optional[str] = None,
        output_col: str = "momentum_exposure",
    ) -> pd.DataFrame:
        if df is None or df.empty or exposure_col not in df.columns:
            return df
        if not beta_col or not size_col or beta_col not in df.columns or size_col not in df.columns:
            df[output_col] = zscore_series(df[exposure_col].astype(float))
            return df
        return residualize(df, y_col=exposure_col, x_cols=[beta_col, size_col], out_col=output_col)

    # ------------------------- Microstructure hygiene ------------------------- #
    @staticmethod
    def month_end_rebalance_index(idx: pd.DatetimeIndex, lag_days: int = 1) -> pd.DatetimeIndex:
        """Select last trading day per month, then apply a lag (in trading days)."""
        if idx is None or len(idx) == 0:
            return pd.DatetimeIndex([])
        # Last trading day per month
        s = pd.Series(range(len(idx)), index=idx)
        last_per_month = s.groupby([idx.year, idx.month]).tail(1)
        positions = last_per_month.values + lag_days
        positions = positions[positions < len(idx)]
        return idx[positions]

    @staticmethod
    def apply_microstructure_filters(
        df: pd.DataFrame,
        as_of_date_col: str = "date",
        last_price_date_col: Optional[str] = "last_price_date",
        adtv_col: Optional[str] = "adtv",
        max_stale_days: int = 10,
        min_adtv: Optional[float] = None,
    ) -> pd.DataFrame:
        """Drop stale and illiquid rows if columns exist; otherwise no-op.

        Expects dates in datetime64 for date columns.
        """
        if df is None or df.empty:
            return df
        out = df.copy()
        try:
            if last_price_date_col and last_price_date_col in out.columns and as_of_date_col in out.columns:
                as_of = pd.to_datetime(out[as_of_date_col])
                last_dt = pd.to_datetime(out[last_price_date_col])
                age_days = (as_of - last_dt).dt.days
                out = out[age_days <= max_stale_days]
        except Exception:
            pass
        try:
            if adtv_col and adtv_col in out.columns and min_adtv is not None:
                out = out[out[adtv_col] >= float(min_adtv)]
        except Exception:
            pass
        return out
    
        # ------------------------- Volume-Adjusted Momentum ------------------------- #
    def volume_adjusted_momentum(self, lookback: int = None) -> Optional[float]:
        if lookback is None:
            lookback = MOMENTUM_LOOKBACK["IDIO_LOOKBACK"]
        if self.volumes is None:
            return None
        if len(self.returns) < lookback + 1:
            return None
        window_ret = self.returns.iloc[-lookback:]
        window_vol = self.volumes.loc[window_ret.index]
        total_vol = window_vol.sum()
        if total_vol == 0 or total_vol is None:
            return None
        vw_return = float((window_ret * window_vol).sum() / total_vol)
        return vw_return
    
    def calc_all(self) -> Dict[str, float]:
        """Calculate all momentum factors for the ticker.
        
        Returns:
            Dictionary containing all momentum factor metrics (as decimals).
        """
        round_factor = 4
        results = {
            # Return windows
            "one_month_return": round(self.one_month_return() or np.nan, round_factor),
            "three_month_return": round(self.three_month_return() or np.nan, round_factor),
            "six_month_return": round(self.six_month_return() or np.nan, round_factor),
            "twelve_month_return_ex1m": round(self.twelve_month_return_ex1m() or np.nan, round_factor),
            
            # Canonical ex-1m windows
            "r12_1": round(self.r12_1() or np.nan, round_factor),
            "r6_1": round(self.r6_1() or np.nan, round_factor),
            "r3_1": round(self.r3_1() or np.nan, round_factor),
            
            # Technical indicators
            "pct_from_52w_high": round(self.pct_from_52w_high() or np.nan, round_factor),
            "sma_ratio": round(self.sma_ratio() or np.nan, round_factor),
            "sma_50": round(self.sma_50() or np.nan, round_factor),
            "sma_200": round(self.sma_200() or np.nan, round_factor),
            "rsi": round(self.rsi() or np.nan, round_factor),
            
            # MACD
            "macd_value": np.nan,
            "macd_signal": np.nan,
            
            # Idiosyncratic momentum
            "idio_momentum": round(self.idiosyncratic_momentum() or np.nan, round_factor),
            "sector_idio_momentum": round(self.sector_idiosyncratic_momentum() or np.nan, round_factor),
            "idio_momentum_log": round(self.idiosyncratic_momentum_log() or np.nan, round_factor),
            "sector_idio_momentum_log": round(self.sector_idiosyncratic_momentum_log() or np.nan, round_factor),
            
            # Volume-adjusted
            "volume_adjusted_momentum": round(self.volume_adjusted_momentum() or np.nan, round_factor),
        }
        
        # Handle MACD separately since it returns tuple
        macd_val, macd_sig = self.macd()
        if macd_val is not None:
            results["macd_value"] = round(macd_val, round_factor)
        if macd_sig is not None:
            results["macd_signal"] = round(macd_sig, round_factor)
        
        # Clean up NaN/Inf values
        for key, value in results.items():
            if value is None or np.isinf(value) or (isinstance(value, float) and np.isnan(value)):
                results[key] = np.nan
                
        return results
    
    @classmethod
    def calc_all_bulk(
        cls, 
        tickers: list[str], 
        start_date: datetime,
        end_date: datetime,
        market_ticker: str = "SPY"
    ) -> pd.DataFrame:
        """Calculate all momentum factors for multiple tickers using bulk data fetching.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date for price data
            end_date: End date for price data
            market_ticker: Market benchmark ticker for idiosyncratic calculations
        
        Returns:
            DataFrame with tickers as rows and momentum metrics as columns
        """
        from app.core.calculations.core.data_service import DataService
        from app.db.core.models.market_data_models import Ticker as TickerModel
        from app.db.core.db_config import MarketSession
        
        ds = DataService()
        
        # Simple sector ETF mapping 
        SECTOR_ETF_MAP = {
            'equity_sector_information_technology': 'XLK',
            'equity_sector_financials': 'XLF',
            'equity_sector_health_care': 'XLV',
            'equity_sector_consumer_discretionary': 'XLY',
            'equity_sector_communication_services': 'XLC',
            'equity_sector_industrials': 'XLI',
            'equity_sector_consumer_staples': 'XLP',
            'equity_sector_energy': 'XLE',
            'equity_sector_utilities': 'XLU',
            'equity_sector_real_estate': 'XLRE',
            'equity_sector_materials': 'XLB'
        }
        
        # Get sector for each ticker
        ticker_sectors = {}
        session = MarketSession()
        for ticker in tickers:
            ticker_obj = session.query(TickerModel).filter(TickerModel.ticker == ticker.upper()).first()
            if ticker_obj and ticker_obj.sector:
                ticker_sectors[ticker.upper()] = ticker_obj.sector
        session.close()
        
        # Determine unique sector ETFs needed
        sector_etfs = set()
        for sector in ticker_sectors.values():
            if sector in SECTOR_ETF_MAP:
                sector_etfs.add(SECTOR_ETF_MAP[sector])
        
        # Bulk fetch full price data (includes volume) for all tickers plus market and sector ETFs
        all_tickers = list(tickers) + [market_ticker] + list(sector_etfs)
        
        # Get full price data with volume
        price_data = {}
        volume_data = {}
        for ticker in all_tickers:
            try:
                price_frame = ds.get_price_data(ticker, start_date, end_date).frame
                if price_frame is not None and not price_frame.empty:
                    price_data[ticker] = price_frame['close']
                    if 'volume' in price_frame.columns:
                        volume_data[ticker] = price_frame['volume']
            except Exception:
                pass
        
        # Get market prices
        market_px = price_data.get(market_ticker)
        
        # Calculate momentum factors for each ticker
        all_results = {}
        for ticker in tickers:
            ticker = ticker.upper()
            if ticker in price_data:
                try:
                    px = price_data[ticker]
                    vol = volume_data.get(ticker)  # Get volume if available
                    
                    # Get dividends if available
                    try:
                        divs = ds.get_dividends(ticker, start_date, end_date).series
                        divs = divs.reindex(px.index).fillna(0.0)
                    except Exception:
                        divs = None
                    
                    # Align market series to asset index
                    mkt_aligned = market_px.reindex(px.index) if market_px is not None else None
                    
                    # Get sector ETF price data if available
                    sector_px = None
                    if ticker in ticker_sectors:
                        sector = ticker_sectors[ticker]
                        if sector in SECTOR_ETF_MAP:
                            sector_etf = SECTOR_ETF_MAP[sector]
                            if sector_etf in price_data:
                                sector_px = price_data[sector_etf].reindex(px.index)
                    
                    # Create MomentumFactors instance with volume and sector data
                    mf = cls(px, volume_series=vol, dividends_series=divs, 
                            market_price_series=mkt_aligned, sector_price_series=sector_px)
                    all_results[ticker] = mf.calc_all()
                except Exception as e:
                    print(f"Error calculating momentum factors for {ticker}: {e}")
                    all_results[ticker] = {}
        
        # Convert to DataFrame
        df = pd.DataFrame(all_results).T
        return df


if __name__ == "__main__":
    # Smoke test: compute momentum attributes and composite for a small ticker set
    from app.core.calculations.core.data_service import DataService
    print("[momentum] smoke test starting...")
    try:
        tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "NVDA"]
        ds = DataService()
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=800)
        price_map = ds.get_bulk_close_series(tickers, start, end)
        # Fetch market benchmark (SPY) for idiosyncratic momentum; fallback to equal-weight index
        market_ticker = "SPY"
        try:
            market_map = ds.get_bulk_close_series([market_ticker], start, end)
            market_px = market_map.get(market_ticker)
        except Exception:
            market_px = None
        if market_px is None or market_px.empty:
            # Fallback: build equal-weighted market index from available prices
            try:
                df_px = pd.DataFrame(price_map)
                eq_ret = df_px.pct_change().mean(axis=1).fillna(0.0)
                market_px = (1.0 + eq_ret).cumprod()
            except Exception:
                market_px = None
                
        rows = []
        for tkr, px in price_map.items():
            # Dividends (optional)
            try:
                divs = ds.get_dividends(tkr, start, end).series
                divs = divs.reindex(px.index).fillna(0.0)
            except Exception:
                divs = None
            # Align market series to asset index if available
            mkt_aligned = market_px.reindex(px.index) if market_px is not None else None
            mf = MomentumFactors(px, dividends_series=divs, market_price_series=mkt_aligned)
            attrs = mf.compute_attributes()
            rows.append({"ticker": tkr, **attrs})

        frame = pd.DataFrame(rows)
        # Compose exposure (global z if no sector column)
        frame = MomentumFactors.compose_momentum_exposure(frame)
        frame = MomentumFactors.orthogonalize_momentum(frame)
        cols = ["ticker", "r12_1", "r6_1", "r3_1", "idio_mom", "momentum_exposure_raw", "momentum_exposure"]
        print(frame[cols].to_string(index=False))
    except Exception as e:
        print(f"[momentum] smoke test failed: {e}")




