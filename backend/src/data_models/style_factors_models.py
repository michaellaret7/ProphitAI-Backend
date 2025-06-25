from typing import Optional
from pydantic import BaseModel

class ValueFactorMetrics(BaseModel):
    """Pydantic model for value factor metrics"""
    price_to_book: Optional[float]
    book_to_market: Optional[float]
    trailing_pe: Optional[float]
    forward_pe: Optional[float]
    earnings_yield: Optional[float]
    price_to_sales: Optional[float]
    price_to_cashflow: Optional[float]
    free_cashflow_yield: Optional[float]
    ev_to_ebitda: Optional[float]
    ev_to_ebit: Optional[float]
    dividend_yield: Optional[float]
    peg_ratio: Optional[float]

class QualityFactorMetrics(BaseModel):
    """Pydantic model for quality factor metrics"""
    return_on_equity: Optional[float]
    return_on_assets: Optional[float]
    roic: Optional[float]
    gross_profitability: Optional[float]
    net_margin: Optional[float]
    fcf_margin: Optional[float]
    debt_to_equity: Optional[float]
    net_debt_to_ebitda: Optional[float]
    interest_coverage: Optional[float]
    quick_ratio: Optional[float]
    altman_z_score: Optional[float]
    accruals_ratio: Optional[float]
    earnings_stability: Optional[float]
    piotroski_f_score: Optional[int]
    eps_revision_3m: Optional[float]
    dividend_payout: Optional[float]

class MomentumFactorMetrics(BaseModel):
    """Pydantic model for momentum factor metrics"""
    one_month_return: Optional[float]
    three_month_return: Optional[float]
    six_month_return: Optional[float]
    twelve_month_return_ex1m: Optional[float]
    pct_from_52w_high: Optional[float]
    sma_ratio: Optional[float]
    macd_value: Optional[float]
    macd_signal: Optional[float]
    rsi: Optional[float]
    idiosyncratic_momentum: Optional[float]
    sector_idiosyncratic_momentum: Optional[float]
    volume_adjusted_momentum: Optional[float]

class VolatilityFactorMetrics(BaseModel):
    """Pydantic model for volatility factor metrics"""
    realized_vol_30d: Optional[float]
    realized_vol_90d: Optional[float]
    beta_1yr: Optional[float]
    idiosyncratic_vol: Optional[float]
    downside_dev_30d: Optional[float]
    max_drawdown_1yr: Optional[float]
    atr_price_ratio: Optional[float]
    variance_ratio_3m_12m: Optional[float]
    skewness: Optional[float]
    kurtosis: Optional[float]
    garch_forecast: Optional[float]