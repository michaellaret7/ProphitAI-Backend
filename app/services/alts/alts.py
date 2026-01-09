from app.repositories.prophit_alts_data import get_fund_final_positions
from app.db.core.db_config import ProphitAltsSession, MarketSession
from app.db.core.models.prophit_alts_models import *
from app.db.core.models.market_data_models import *
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.core.calculations.core.config import DEFAULT_LOOKBACK_3Y
from app.utils.case_conversion import dict_keys_to_camel, list_of_dicts_to_camel, PORTFOLIO_KEY_MAP
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json
from app.utils.time_utils import get_current_utc_time

class ProphitAltsServices:
    """
    Service to fetch price data ONCE and compute all portfolio-derived series/metrics.

    Precomputed attributes (None/empty if data unavailable):
    - positions, weights (signed), tickers
    - returns_data (per-ticker daily returns)
    - portfolio_returns (daily)
    - spy_returns_aligned (daily, aligned to portfolio_returns index)
    - equity_curve, underwater_series
    - rolling_12m_returns_series (daily trailing 12M), monthly_returns_series (month-end)
    - exposures: long_exposure, short_exposure, gross_exposure, net_exposure (decimals)
    """

    def __init__(self, fund_name: str, lookback_days: int = DEFAULT_LOOKBACK_3Y, frequency: str = 'daily'):
        self.fund_name = fund_name
        self.lookback_days = lookback_days
        self.frequency = frequency

        # Defaults
        self.positions: list[dict] = []
        self.weights: Dict[str, float] = {}
        self.tickers: list[str] = []
        self.returns_data: pd.DataFrame = pd.DataFrame()
        self.portfolio_returns: pd.Series = pd.Series(dtype=float)
        self.spy_returns_aligned: pd.Series = pd.Series(dtype=float)
        self.equity_curve: pd.Series = pd.Series(dtype=float)
        self.underwater_series: pd.Series = pd.Series(dtype=float)
        self.rolling_12m_returns_series: pd.Series = pd.Series(dtype=float)
        self.monthly_returns_series: pd.Series = pd.Series(dtype=float)
        self.long_exposure: float = 0.0
        self.short_exposure: float = 0.0
        self.gross_exposure: float = 0.0
        self.net_exposure: float = 0.0

        # Load fund and positions
        session = ProphitAltsSession()
        fund = session.query(Fund).filter(Fund.fund_name == fund_name).first()
        if not fund:
            session.close()
            return
        fund_positions = session.query(FundFinalPosition).filter(FundFinalPosition.fund_id == fund.id).all()
        self.positions = [serialize_sqlalchemy_obj(position) for position in fund_positions]
        session.close()

        if not self.positions:
            return

        # Build signed weights and exposures (decimals)
        long_exposure = 0.0
        short_exposure = 0.0
        for position in self.positions:
            ticker = position['ticker_name']
            allocation = float(position['portfolio_allocation'])
            position_raw = position.get('position', 'LONG')
            if 'SHORT' in str(position_raw).upper():
                self.weights[ticker] = -allocation
                short_exposure += allocation
            else:
                self.weights[ticker] = allocation
                long_exposure += allocation

        self.long_exposure = long_exposure
        self.short_exposure = short_exposure
        self.gross_exposure = long_exposure + short_exposure
        self.net_exposure = long_exposure - short_exposure

        self.tickers = list(self.weights.keys())
        if 'SPY' not in self.tickers:
            self.tickers.append('SPY')

        # Fetch prices ONCE (using UTC time)
        end_date = get_current_utc_time()
        start_date = end_date - timedelta(days=self.lookback_days)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        price_data = fetch_bulk_price_data_for_tickers(
            self.tickers,
            start_date_str,
            end_date_str,
            frequency=self.frequency,
        )

        # Per-ticker daily returns on union-of-dates
        returns_data = pd.DataFrame()
        for ticker in price_data.columns:
            prices = price_data[ticker]
            if not prices.empty:
                series_sorted = prices.sort_index()
                returns_data[ticker] = series_sorted.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
        self.returns_data = returns_data.sort_index()

        if self.returns_data.empty:
            return

        # Compute daily portfolio returns using per-day normalized signed weights
        portfolio_returns_matrix = self.returns_data.reindex(columns=list(self.weights.keys()))
        weights_series = pd.Series(self.weights)
        availability_mask = portfolio_returns_matrix.notna()
        abs_weight_matrix = availability_mask.multiply(weights_series.abs(), axis=1)
        sum_abs_by_day = abs_weight_matrix.sum(axis=1)
        signed_weight_matrix = availability_mask.multiply(weights_series, axis=1)
        normalized_signed_weights = signed_weight_matrix.div(sum_abs_by_day.replace(0, np.nan), axis=0)
        weighted_returns = portfolio_returns_matrix * normalized_signed_weights
        portfolio_returns = weighted_returns.sum(axis=1)
        portfolio_returns = portfolio_returns[sum_abs_by_day > 0].dropna()
        self.portfolio_returns = portfolio_returns

        # Align SPY to portfolio index
        if 'SPY' in self.returns_data.columns:
            self.spy_returns_aligned = self.returns_data['SPY'].reindex(self.portfolio_returns.index)

        # Precompute heavy series
        if not self.portfolio_returns.empty:
            # Equity curve and underwater
            self.equity_curve = (1 + self.portfolio_returns).cumprod()
            hwm = self.equity_curve.cummax()
            self.underwater_series = (self.equity_curve / hwm - 1) * 100

            # Rolling 12M daily returns
            rolling_window_days = 252
            rolling = (
                (1 + self.portfolio_returns)
                .rolling(window=rolling_window_days, min_periods=rolling_window_days)
                .apply(np.prod, raw=True)
                - 1
            )
            rolling = rolling.dropna()
            if len(rolling) > 252:
                rolling = rolling.tail(252)
            self.rolling_12m_returns_series = rolling

            # Monthly return history (month end)
            self.monthly_returns_series = (1 + self.portfolio_returns).resample('ME').prod() - 1

    # ---------- Public accessors (lightweight; return already computed structures) ----------
    def get_metrics(self) -> dict:
        metrics: Dict[str, float | int | list | None] = {}
        if self.portfolio_returns.empty:
            return metrics

        trading_days = 252

        # YTD (using UTC time)
        current_year = get_current_utc_time().year
        ytd_returns = self.portfolio_returns[self.portfolio_returns.index.year == current_year]
        if not ytd_returns.empty:
            ytd_return = (1 + ytd_returns).prod() - 1
            metrics['ytd_return'] = round(ytd_return * 100, 2)
        else:
            metrics['ytd_return'] = 0.0

        # Exposures (convert to pct for display)
        metrics['gross_exposure'] = round(self.gross_exposure * 100, 2)
        metrics['net_exposure'] = round(self.net_exposure * 100, 2)

        # Vol metrics
        annual_volatility = self.portfolio_returns.std() * np.sqrt(trading_days)
        cumulative_return = (1 + self.portfolio_returns).prod() - 1
        n_days = len(self.portfolio_returns)
        years = n_days / trading_days
        if years > 0 and cumulative_return > -1:
            annualized_return = (1 + cumulative_return) ** (1/years) - 1
        else:
            annualized_return = self.portfolio_returns.mean() * trading_days

        risk_free_rate = 0.02
        sharpe_ratio = (annualized_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
        metrics['sharpe_ratio'] = round(sharpe_ratio, 3)

        downside_returns = self.portfolio_returns[self.portfolio_returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(trading_days)
        sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
        metrics['sortino_ratio'] = round(sortino_ratio, 3)

        # Max drawdown
        if not self.equity_curve.empty:
            running_max = self.equity_curve.expanding().max()
            drawdown = (self.equity_curve - running_max) / running_max
            max_drawdown = drawdown.min()
            metrics['max_drawdown'] = round(max_drawdown * 100, 2)
        else:
            metrics['max_drawdown'] = 0.0

        # Beta and captures
        if not self.spy_returns_aligned.empty:
            valid_pairs = self.spy_returns_aligned.notna() & self.portfolio_returns.notna()
            spy_for_calc = self.spy_returns_aligned[valid_pairs]
            port_for_calc = self.portfolio_returns[valid_pairs]
            covariance = port_for_calc.cov(spy_for_calc)
            spy_variance = spy_for_calc.var()
            beta = covariance / spy_variance if spy_variance > 0 else 0
            metrics['beta'] = round(beta, 3)

            up_mask = spy_for_calc > 0
            down_mask = spy_for_calc < 0
            up_capture = None
            down_capture = None
            if up_mask.any():
                spy_up_mean = spy_for_calc[up_mask].mean()
                port_up_mean = port_for_calc[up_mask].mean()
                if spy_up_mean != 0:
                    up_capture = (port_up_mean / spy_up_mean) * 100
            if down_mask.any():
                spy_down_mean = spy_for_calc[down_mask].mean()
                port_down_mean = port_for_calc[down_mask].mean()
                if spy_down_mean != 0:
                    down_capture = (port_down_mean / spy_down_mean) * 100
            metrics['up_capture'] = round(up_capture, 2) if up_capture is not None else None
            metrics['down_capture'] = round(down_capture, 2) if down_capture is not None else None
        else:
            metrics['beta'] = None
            metrics['up_capture'] = None
            metrics['down_capture'] = None

        # VaR (95%)
        var_95 = np.percentile(self.portfolio_returns.dropna(), 5)
        var_95_annual = var_95 * np.sqrt(trading_days)
        metrics['var_95'] = round(var_95_annual * 100, 2)

        # Rolling 12M
        metrics['rolling_12m_returns_daily'] = [
            {'date': idx.strftime('%Y-%m-%d'), 'value': round(val * 100, 2)}
            for idx, val in self.rolling_12m_returns_series.dropna().items()
        ] if not self.rolling_12m_returns_series.empty else []

        # Monthly returns
        metrics['monthly_return_history'] = [
            {'month': idx.strftime('%Y-%m'), 'value': round(val * 100, 2)}
            for idx, val in self.monthly_returns_series.dropna().items()
        ] if not self.monthly_returns_series.empty else []

        # Underwater
        metrics['underwater_daily'] = [
            {'date': idx.strftime('%Y-%m-%d'), 'value': round(val, 2)}
            for idx, val in self.underwater_series.dropna().items()
        ] if not self.underwater_series.empty else []

        # NAV perf (default starting NAV)
        nav_series = 100.0 * (1 + self.portfolio_returns).cumprod()
        metrics['nav_performance_daily'] = [
            {'date': idx.strftime('%Y-%m-%d'), 'value': round(float(val), 2)}
            for idx, val in nav_series.items()
        ]

        # Return distribution histogram
        returns_pct = self.portfolio_returns * 100.0
        counts, bin_edges = np.histogram(returns_pct.dropna().values, bins=50)
        metrics['return_distribution'] = [
            {'bin_start': round(float(bin_edges[i]), 4), 'bin_end': round(float(bin_edges[i + 1]), 4), 'count': int(counts[i])}
            for i in range(len(counts))
        ]

        return metrics

    def get_nav_performance(self, starting_nav: float = 100.0) -> list[dict]:
        if self.portfolio_returns.empty:
            return []
        nav_series = starting_nav * (1 + self.portfolio_returns).cumprod()
        return [
            {'date': idx.strftime('%Y-%m-%d'), 'value': round(float(val), 2)}
            for idx, val in nav_series.items()
        ]

    def get_return_distribution(self, bin_count: int = 50) -> list[dict]:
        if self.portfolio_returns.empty:
            return []
        returns_pct = self.portfolio_returns * 100.0
        counts, bin_edges = np.histogram(returns_pct.dropna().values, bins=bin_count)
        return [
            {'bin_start': round(float(bin_edges[i]), 4), 'bin_end': round(float(bin_edges[i + 1]), 4), 'count': int(counts[i])}
            for i in range(len(counts))
        ]

    def get_rolling_12m_returns_daily(self) -> list[dict]:
        if self.rolling_12m_returns_series.empty:
            return []
        return [
            {'date': idx.strftime('%Y-%m-%d'), 'value': round(val * 100, 2)}
            for idx, val in self.rolling_12m_returns_series.items()
        ]

    def get_monthly_return_history(self) -> list[dict]:
        if self.monthly_returns_series.empty:
            return []
        return [
            {'month': idx.strftime('%Y-%m'), 'value': round(val * 100, 2)}
            for idx, val in self.monthly_returns_series.items()
        ]

    def get_underwater_daily(self) -> list[dict]:
        if self.underwater_series.empty:
            return []
        return [
            {'date': idx.strftime('%Y-%m-%d'), 'value': round(val, 2)}
            for idx, val in self.underwater_series.items()
        ]

    def get_fund_performance_data(self) -> Dict[str, Any]:
        """
        Get formatted fund performance data for API response.

        Returns positions, metrics, and time series data in camelCase format
        ready for ok_envelope. This method consolidates all the business logic
        that was previously in the controller.

        Returns:
            Dict with 'payload', 'counts', and 'updated' keys for ok_envelope

        Raises:
            ValueError: If no positions found for fund
        """
        # Get positions from repository
        positions_raw = get_fund_final_positions(fund_name=self.fund_name)

        if not positions_raw:
            raise ValueError(f"No final positions found for fund: {self.fund_name}")

        # Filter out internal fields not needed in API response
        fields_to_exclude = {"id", "fund_id", "ticker_id", "reasoning", "date_created", "date_updated"}
        positions_filtered = [
            {k: v for k, v in position.items() if k not in fields_to_exclude}
            for position in positions_raw
        ]

        # Round numeric allocation fields and clean position enum values
        for p in positions_filtered:
            # Round allocations
            for key in ('risk_allocation', 'portfolio_allocation'):
                if key in p and p[key] is not None:
                    try:
                        p[key] = round(float(p[key]), 3)
                    except (ValueError, TypeError):
                        pass

            # Clean position enum: "PositionType.SHORT" -> "SHORT"
            if 'position' in p and p['position']:
                position_str = str(p['position'])
                if 'SHORT' in position_str.upper():
                    p['position'] = 'SHORT'
                elif 'LONG' in position_str.upper():
                    p['position'] = 'LONG'

        # Convert positions to camelCase
        positions_camel = list_of_dicts_to_camel(positions_filtered, key_map=PORTFOLIO_KEY_MAP)

        # Get metrics (already computed in __init__)
        metrics = self.get_metrics()

        # Convert metrics to camelCase
        metrics_camel = dict_keys_to_camel(metrics, key_map=PORTFOLIO_KEY_MAP, recursive=True)

        # Extract time-series data from metrics
        series_keys = {
            'navPerformanceDaily',
            'returnDistribution',
            'rolling12mReturnsDaily',
            'monthlyReturnHistory',
            'underwaterDaily',
        }

        series = {}
        for sk in list(series_keys):
            if sk in metrics_camel:
                series[sk] = metrics_camel.pop(sk)

        # Build calculated data items array for counts
        calc_items = []
        if metrics_camel:
            calc_items.append({'type': 'metrics', 'data': dict(metrics_camel)})
        for sk, sv in series.items():
            if isinstance(sv, list):
                calc_items.append({'type': sk, 'data': sv})

        # Extract last date for updated timestamp
        nav_series = series.get('navPerformanceDaily')
        last_date = None
        if isinstance(nav_series, list) and len(nav_series) > 0:
            last_date = nav_series[-1].get('date')

        # Build counts metadata
        counts = {
            'currentItemCount': len(calc_items),
            'itemsPerPage': len(calc_items),
            'startIndex': 1,
            'totalItems': len(calc_items),
        }

        # Build payload
        payload = {
            "metrics": metrics_camel,
            "performanceData": positions_camel,
            **series,
        }

        return {
            'payload': payload,
            'counts': counts,
            'updated': f"{last_date}T00:00:00Z" if last_date else None
        }

def get_portfolio_nav_performance(fund_name: str, starting_nav: float = 100.0) -> str:
    """
    Return daily NAV series for the portfolio as a JSON string list of {date, value}.
    """
    svc = ProphitAltsServices(fund_name)
    result = svc.get_nav_performance(starting_nav) if not svc.portfolio_returns.empty else []
    return json.dumps(result)

def get_portfolio_return_distribution(fund_name: str, bin_count: int = 50) -> str:
    """
    Return a histogram of daily returns (%) as a JSON string list of
    {bin_start, bin_end, count} suitable for frontend charting.
    """
    svc = ProphitAltsServices(fund_name)
    histogram = svc.get_return_distribution(bin_count) if not svc.portfolio_returns.empty else []
    return json.dumps(histogram)

def get_fund_landing_page_metrics(fund_name: str) -> dict:
    """
    Calculate key performance metrics for a fund.
    Returns JSON string of metrics; preserves prior API shape.
    """
    # Validate fund existence for clearer error
    session = ProphitAltsSession()
    fund = session.query(Fund).filter(Fund.fund_name == fund_name).first()
    session.close()
    if not fund:
        return json.dumps({"error": f"Fund '{fund_name}' not found"})

    svc = ProphitAltsServices(fund_name)
    if svc.portfolio_returns.empty:
        return json.dumps({"error": "Insufficient price data"})

    metrics = svc.get_metrics()
    return json.dumps(metrics)


if __name__ == "__main__":
    _metrics_json = get_fund_landing_page_metrics(fund_name="consumer_staples_fund")
    metrics = json.loads(_metrics_json)
