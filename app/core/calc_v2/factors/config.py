"""Constants for factor calculations."""

from app.core.calc_v2.config import TRADING_DAYS

# ================================
# --> Momentum lookbacks (trading days)
# ================================
SKIP_RECENT = 21            # Skip last month (Jegadeesh & Titman convention)
R12_1_SPAN = TRADING_DAYS - SKIP_RECENT   # ~231 days
R6_1_SPAN = 126 - SKIP_RECENT             # ~105 days
R3_1_SPAN = 63 - SKIP_RECENT              # ~42 days
HIGH_52W_WINDOW = TRADING_DAYS             # 252 days

# ================================
# --> Volatility windows
# ================================
VOL_1Y_WINDOW = TRADING_DAYS    # 252
VOL_3M_WINDOW = 63
BETA_LOOKBACK = TRADING_DAYS    # 252
MIN_OBSERVATIONS = 30

# ================================
# --> Fundamental constants
# ================================
CORPORATE_TAX_RATE = 0.21
