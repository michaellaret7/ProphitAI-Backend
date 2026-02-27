"""Shared constants for calculations."""

TRADING_DAYS = 252

DEFAULT_RF_ANNUAL = 0.045  # 10-Year UST yield (~4.5%)

# Reason: constant universe ensures all portfolios are z-scored against the
# same broad, diversified reference population (55 tickers, all 11 GICS sectors).
# Structure: 3 large-cap, 1 mid-cap, 1 small-cap per sector for cap-size diversity.
UNIVERSE_TICKERS: list[str] = [
    # Information Technology          | Large: AAPL, MSFT, NVDA | Mid: FFIV | Small: POWI
    'AAPL', 'MSFT', 'NVDA', 'FFIV', 'POWI',
    # Health Care                     | Large: JNJ, UNH, LLY   | Mid: HOLX | Small: INSP
    'JNJ', 'UNH', 'LLY', 'HOLX', 'INSP',
    # Financials                      | Large: JPM, BAC, GS     | Mid: CBOE | Small: HOMB
    'JPM', 'BAC', 'GS', 'CBOE', 'HOMB',
    # Consumer Discretionary          | Large: AMZN, TSLA, HD   | Mid: DECK | Small: FOXF
    'AMZN', 'TSLA', 'HD', 'DECK', 'FOXF',
    # Consumer Staples                | Large: PG, KO, WMT      | Mid: CHD  | Small: IPAR
    'PG', 'KO', 'WMT', 'CHD', 'IPAR',
    # Energy                          | Large: XOM, CVX, COP    | Mid: DVN  | Small: MTDR
    'XOM', 'CVX', 'COP', 'DVN', 'MTDR',
    # Industrials                     | Large: CAT, HON, GE     | Mid: XYL  | Small: AAON
    'CAT', 'HON', 'GE', 'XYL', 'AAON',
    # Communication Services          | Large: GOOG, META, NFLX | Mid: MTCH | Small: YELP
    'GOOG', 'META', 'NFLX', 'MTCH', 'YELP',
    # Utilities                       | Large: NEE, DUK, SO     | Mid: ATO  | Small: NWE
    'NEE', 'DUK', 'SO', 'ATO', 'NWE',
    # Real Estate                     | Large: AMT, PLD, SPG    | Mid: KIM  | Small: NHI
    'AMT', 'PLD', 'SPG', 'KIM', 'NHI',
    # Materials                       | Large: LIN, APD, SHW    | Mid: RPM  | Small: UFPI
    'LIN', 'APD', 'SHW', 'RPM', 'UFPI',
]
