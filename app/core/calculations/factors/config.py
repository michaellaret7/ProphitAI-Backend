"""Factor-specific configuration constants.

Central configuration for all factor calculations to ensure consistency
across value, growth, momentum, quality, and volatility factors.
"""

from app.core.calculations.core.config import DEFAULT_TRADING_DAYS

# ============ TIME HORIZONS ============
# Momentum lookback periods (in trading days)
MOMENTUM_LOOKBACK = {
    # Raw period lengths
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "12M": 252,
    "SKIP_RECENT": 21,  # Skip most recent month for momentum
    "IDIO_LOOKBACK": 60,  # Idiosyncratic momentum window
    # Academic "X-1" momentum windows (Jegadeesh & Titman, 1993)
    # These are the spans FROM t-X TO t-1 (excluding most recent month)
    # Formula: Price(t-1) / Price(t-X) - 1
    "R12_1_SPAN": 231,  # 252 - 21 = return from t-12 to t-1 (11 months)
    "R6_1_SPAN": 105,   # 126 - 21 = return from t-6 to t-1 (5 months)
    "R3_1_SPAN": 42,    # 63 - 21 = return from t-3 to t-1 (2 months)
}

# Volatility calculation windows (in trading days)
VOLATILITY_WINDOWS = {
    "30D": 30,
    "90D": 90,
    "252D": DEFAULT_TRADING_DAYS,
    "BETA_LOOKBACK": DEFAULT_TRADING_DAYS,
}

# Fundamental data windows
FUNDAMENTAL_WINDOWS = {
    "TTM_QUARTERS": 4,  # Trailing twelve months
    "FORWARD_QUARTERS": 4,  # Forward estimates (FY1)
    "FORWARD_2Y_QUARTERS": 8,  # Forward estimates (FY2)
    "EPS_STABILITY_QUARTERS": 12,  # For earnings stability calc
    "EPS_GROWTH_5YR_QUARTERS": 20,  # 5-year EPS growth
}

# Price data default lookback (for factor_tilt.py)
DEFAULT_PRICE_LOOKBACK = DEFAULT_TRADING_DAYS  # 1 year default

# ============ FACTOR WEIGHTS ============
# Value factor composition weights
VALUE_WEIGHTS = {
    "bp": 0.20,  # Book/Price
    "ep": 0.20,  # Earnings/Price
    "cfp": 0.15,  # Cash Flow/Price
    "fcf_yield": 0.15,  # FCF Yield
    "sales_ev": 0.10,  # Sales/EV
    "ebitda_ev": 0.10,  # EBITDA/EV
    "ebit_ev": 0.05,  # EBIT/EV
    "div_yld": 0.05,  # Dividend Yield
}

# Growth factor composition weights
GROWTH_WEIGHTS = {
    "fwd_eps_g": 0.35,  # Forward EPS growth
    "fwd_2y_cagr": 0.25,  # 2-year forward CAGR
    "sales_yoy": 0.20,  # Sales YoY
    "ocf_yoy": 0.20,  # Operating CF YoY
}

# Momentum factor composition weights
MOMENTUM_WEIGHTS = {
    "r12_1": 0.6,  # 12-month return ex-1m
    "r6_1": 0.2,  # 6-month return ex-1m
    "idio_mom": 0.2,  # Idiosyncratic momentum
}

# Quality factor composition weights
QUALITY_WEIGHTS = {
    "roe": 0.40 * 0.33,
    "roic": 0.40 * 0.33,
    "gp_a": 0.40 * 0.34,  # Gross profit/assets
    "accruals": 0.25 * 0.5,
    "fcf_margin": 0.25 * 0.5,
    "de": 0.25 * 0.4,  # Debt/Equity
    "nd_ebitda": 0.25 * 0.3,  # Net Debt/EBITDA
    "int_cover": 0.25 * 0.3,  # Interest Coverage
    "stab": 0.10,  # Earnings stability
}

# Volatility factor composition weights
VOLATILITY_WEIGHTS = {
    "idio_vol": 0.60,  # Idiosyncratic volatility
    "realized_vol": 0.30,  # Realized volatility
    "downside_dev": 0.10,  # Downside deviation
    "svlr": 0.00,  # Short/long vol ratio (currently unused)
}

# ============ OTHER PARAMETERS ============
# Tax rate for NOPAT calculations
CORPORATE_TAX_RATE = 0.21

# Minimum sample sizes
MIN_SAMPLE_SIZE = 30  # Minimum data points for statistical calculations
PRICE_LOOKBACK_DAYS = 30  # Days to look back for recent prices

# Technical indicators
TECHNICAL_PARAMS = {
    "RSI_WINDOW": 14,
    "MACD_FAST": 12,
    "MACD_SLOW": 26,
    "MACD_SIGNAL": 9,
    "SMA_FAST": 50,
    "SMA_SLOW": 200,
}

# Microstructure filters
MICROSTRUCTURE_PARAMS = {
    "MAX_STALE_DAYS": 10,
    "MIN_ADTV": 1_000_000,  # Minimum average daily trading value
}
