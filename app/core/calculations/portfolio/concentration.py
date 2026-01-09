from app.db.core.models.market_data_models import *
from app.db.core.db_config import *
import pandas as pd
from datetime import datetime
from app.utils.time_utils import get_current_utc_time
from app.core.calculations.risk.calculator import RiskCalculator
from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.core.calculations.core.config import DEFAULT_CONFIDENCE
from app.core.calculations.returns.calculator import ReturnsCalculator
from datetime import timedelta
from app.core.calculations.core.helpers import build_returns_df_for_dates
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)


class PortfolioConcentration:
    def __init__(self, portfolio_dict: dict, start_date: datetime | None = None, end_date: datetime | None = None, confidence: float = DEFAULT_CONFIDENCE):
        self.portfolio_dict = portfolio_dict or {}
        self.tickers = list(self.portfolio_dict.keys())
        self.confidence = confidence
        self.end_date = end_date or get_current_utc_time()
        self.start_date = start_date or (self.end_date - timedelta(days=365))

        session = MarketSession()
        try:
            rows = session.query(Ticker).filter(Ticker.ticker.in_(self.tickers)).all()
        finally:
            session.close()
            
        self._ticker_rows = rows
        self._ticker_to_sector = {row.ticker: row.sector for row in rows}
        self._ticker_to_industry = {row.ticker: getattr(row, 'industry', None) for row in rows}
        self._ticker_to_sub_industry = {row.ticker: getattr(row, 'sub_industry', None) for row in rows}

    # ----------------------------- helpers ----------------------------- #
    def _weights_for(self, columns: list[str] | pd.Index) -> pd.Series:
        weights = pd.Series({t: self.portfolio_dict.get(t, {}).get('allocation', 0.0) for t in columns})
        total = float(weights.sum()) if not weights.empty else 0.0
        return weights / total if total > 0 else weights

    def _var_grouped(self, label_map: dict[str, str | None]) -> dict:
        returns_df = build_returns_df_for_dates(
            self.tickers,
            self.start_date,
            self.end_date,
            include_dividends=False,
            drop_rows='any',
        )
        if returns_df.empty:
            return {}
        weights = self._weights_for(returns_df.columns)
        if weights.empty or float(weights.sum()) == 0.0:
            return {}
        cov = RiskCalculator.covariance_matrix(returns_df, annualize=False)
        if cov.empty:
            return {}
        _, component_var = RiskCalculator.marginal_var(weights, cov, confidence=self.confidence)
        if component_var.empty:
            return {}
        group_index = pd.Series({t: (label_map.get(t) or 'Unknown') for t in component_var.index})
        grouped = component_var.groupby(group_index).sum()
        return {k: round(float(v), 5) for k, v in grouped.items()}

    # ------------------------------ APIs ------------------------------- #
    def sector_concentration(self) -> dict:
        out = {}
        for row in self._ticker_rows:
            alloc = self.portfolio_dict.get(row.ticker, {}).get('allocation', 0.0)
            out[row.sector] = out.get(row.sector, 0.0) + alloc
        return out

    def industry_concentration(self) -> dict:
        out = {}
        for row in self._ticker_rows:
            key = getattr(row, 'industry', None) or 'Unknown'
            alloc = self.portfolio_dict.get(row.ticker, {}).get('allocation', 0.0)
            out[key] = out.get(key, 0.0) + alloc
        return out

    def sub_industry_concentration(self) -> dict:
        out = {}
        for row in self._ticker_rows:
            key = getattr(row, 'sub_industry', None) or 'Unknown'
            alloc = self.portfolio_dict.get(row.ticker, {}).get('allocation', 0.0)
            out[key] = out.get(key, 0.0) + alloc
        return out

    def sector_var(self) -> dict:
        return self._var_grouped(self._ticker_to_sector)

    def industry_var(self) -> dict:
        return self._var_grouped(self._ticker_to_industry)

    def sub_industry_var(self) -> dict:
        return self._var_grouped(self._ticker_to_sub_industry)

    def portfolio_var(self) -> float:
        """Compute 1-day portfolio VaR (positive magnitude) using parametric method.

        Aligns with group VaR logic by leveraging RiskCalculator.marginal_var and
        summing component contributions.
        """
        returns_df = build_returns_df_for_dates(
            self.tickers,
            self.start_date,
            self.end_date,
            include_dividends=False,
            drop_rows='any',
        )
        if returns_df.empty:
            return float('nan')
        weights = self._weights_for(returns_df.columns)
        if weights.empty or float(weights.sum()) == 0.0:
            return float('nan')
        cov = RiskCalculator.covariance_matrix(returns_df, annualize=False)
        if cov.empty:
            return float('nan')
        _, component_var = RiskCalculator.marginal_var(weights, cov, confidence=self.confidence)
        if component_var.empty:
            return float('nan')
        return round(float(component_var.sum()), 5)

    def net_exposure(self) -> float:
        """Calculate net exposure (long positions - short positions)."""
        long_total = 0.0
        short_total = 0.0
        
        for ticker, config in self.portfolio_dict.items():
            allocation = config.get('allocation', 0.0)
            position = config.get('position', 'long')
            
            if position == 'long':
                long_total += allocation
            elif position == 'short':
                short_total += allocation
                
        return round(float(long_total - short_total), 2)

    def gross_exposure(self) -> float:
        """Calculate gross exposure (sum of absolute values of all positions)."""
        total = 0.0
        
        for ticker, config in self.portfolio_dict.items():
            allocation = config.get('allocation', 0.0)
            total += abs(allocation)
            
        return round(float(total), 2)

    def long_exposure(self) -> float:
        """Calculate total long exposure."""
        long_total = 0.0
        
        for ticker, config in self.portfolio_dict.items():
            allocation = config.get('allocation', 0.0)
            position = config.get('position', 'long')
            
            if position == 'long':
                long_total += allocation
                
        return round(float(long_total), 2)

    def short_exposure(self) -> float:
        """Calculate total short exposure."""
        short_total = 0.0
        
        for ticker, config in self.portfolio_dict.items():
            allocation = config.get('allocation', 0.0)
            position = config.get('position', 'long')
            
            if position == 'short':
                short_total += allocation
                
        return round(float(short_total), 2)

