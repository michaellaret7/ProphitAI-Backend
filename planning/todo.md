# Stock Screener Development Plan (Simplified)

## Overview
Build a simple, efficient stock screener as a tool for the agent framework, leveraging existing database and calculation infrastructure.

## Architecture & File Structure (Minimal)

```
app/
├── repositories/
│   └── screener.py                # Main screener implementation
│
├── models/
│   └── screener_models.py        # Screener request/response models
│
└── tests/
    └── test_screener.py          # Screener tests
```

## Implementation Plan

### Phase 1: Core Screener Implementation
Create a single, powerful screener class in `app/repositories/screener.py` that:

- [ ] **1. Basic Structure**
  - [ ] Create `StockScreener` class
  - [ ] Implement efficient SQL query building
  - [ ] Add result caching using existing patterns
  - [ ] Single, clean screening method with tuple-based operators

- [ ] **2. Comprehensive Filter List**
  
  **Fundamental Filters:**
  - [ ] P/E ratio (pe_ratio)
  - [ ] Forward P/E (forward_pe)
  - [ ] PEG ratio (peg_ratio)
  - [ ] P/B ratio (pb_ratio)
  - [ ] P/S ratio (ps_ratio)
  - [ ] Price/Cash Flow (price_to_cash_flow)
  - [ ] Price/FCF (price_to_fcf)
  - [ ] EV/EBITDA (ev_to_ebitda)
  - [ ] EV/Revenue (ev_to_revenue)
  - [ ] Market cap (market_cap)
  - [ ] Enterprise value (enterprise_value)
  - [ ] Revenue (revenue)
  - [ ] Revenue growth YoY (revenue_growth_yoy)
  - [ ] Revenue growth QoQ (revenue_growth_qoq)
  - [ ] Earnings (earnings)
  - [ ] Earnings growth YoY (earnings_growth_yoy)
  - [ ] Earnings growth QoQ (earnings_growth_qoq)
  - [ ] EPS (eps)
  - [ ] EPS growth (eps_growth)
  - [ ] ROE (return_on_equity)
  - [ ] ROA (return_on_assets)
  - [ ] ROIC (return_on_invested_capital)
  - [ ] Gross margin (gross_margin)
  - [ ] Operating margin (operating_margin)
  - [ ] Net margin (net_margin)
  - [ ] FCF margin (fcf_margin)
  - [ ] EBITDA margin (ebitda_margin)
  - [ ] Debt/Equity (debt_to_equity)
  - [ ] Current ratio (current_ratio)
  - [ ] Quick ratio (quick_ratio)
  - [ ] Interest coverage (interest_coverage)
  - [ ] Asset turnover (asset_turnover)
  - [ ] Inventory turnover (inventory_turnover)
  - [ ] Dividend yield (dividend_yield)
  - [ ] Dividend payout ratio (payout_ratio)
  - [ ] Free cash flow (free_cash_flow)
  - [ ] Operating cash flow (operating_cash_flow)
  - [ ] Cash per share (cash_per_share)
  - [ ] Book value per share (book_value_per_share)
  - [ ] Tangible book value (tangible_book_value)
  - [ ] Working capital (working_capital)
  - [ ] Altman Z-Score (altman_z_score)
  - [ ] Piotroski F-Score (piotroski_score)
  
  **Technical Filters:**
  - [ ] Current price (price)
  - [ ] Price change % (1D, 5D, 1M, 3M, 6M, 1Y, YTD)
  - [ ] 52-week high (week_52_high)
  - [ ] 52-week low (week_52_low)
  - [ ] % from 52-week high (percent_from_52w_high)
  - [ ] % from 52-week low (percent_from_52w_low)
  - [ ] Average volume (avg_volume_10d, avg_volume_20d, avg_volume_50d)
  - [ ] Volume (volume)
  - [ ] Volume ratio (volume_ratio)
  - [ ] Dollar volume (dollar_volume)
  - [ ] SMA (sma_20, sma_50, sma_100, sma_200)
  - [ ] EMA (ema_20, ema_50, ema_100, ema_200)
  - [ ] Price vs SMA (price_vs_sma_20, price_vs_sma_50, etc.)
  - [ ] Golden cross (golden_cross)
  - [ ] Death cross (death_cross)
  - [ ] RSI (rsi_14)
  - [ ] MACD (macd_signal)
  - [ ] Stochastic (stochastic_k, stochastic_d)
  - [ ] Bollinger Bands (bb_upper, bb_lower, bb_position)
  - [ ] ATR (atr_14)
  - [ ] Volatility (volatility_30d, volatility_90d, volatility_252d)
  - [ ] Beta (beta)
  - [ ] Correlation to SPY (correlation_spy)
  - [ ] Relative strength vs sector (rs_sector)
  - [ ] Relative strength vs market (rs_market)
  
  **ETF-Specific Filters:**
  - [ ] Expense ratio (expense_ratio)
  - [ ] AUM (assets_under_management)
  - [ ] Holdings count (holdings_count)
  - [ ] Top 10 holdings concentration (top10_concentration)
  - [ ] Inception date (inception_date)
  - [ ] NAV (nav)
  - [ ] Premium/Discount to NAV (nav_premium)
  - [ ] Tracking error (tracking_error)
  - [ ] Yield (distribution_yield)
  
  **Other Filters:**
  - [ ] Sector (sector)
  - [ ] Industry (industry)
  - [ ] Sub-industry (sub_industry)
  - [ ] Exchange (exchange)
  - [ ] Country (country)
  - [ ] Is ETF (is_etf)
  - [ ] Has dividends (has_dividends)
  - [ ] Has options (has_options)
  - [ ] Analyst rating (analyst_rating)
  - [ ] Analyst consensus (analyst_consensus)
  - [ ] Price target (analyst_price_target)
  - [ ] Number of analysts (analyst_count)
  - [ ] Insider ownership % (insider_ownership)
  - [ ] Institutional ownership % (institutional_ownership)
  - [ ] Short interest % (short_interest)
  - [ ] Days to cover (days_to_cover)

- [ ] **3. Single Clean Screening Method with Tuple Operators**
  ```python
  # CHOSEN APPROACH: Tuple-based operators
  
  from app.repositories.screener import StockScreener
  
  screener = StockScreener()
  
  # Tuple format for all comparison operations
  results = screener.screen(
      pe_ratio=(5, 20),           # Between 5 and 20
      market_cap=(1e9, None),      # Greater than 1B (None = no max)
      roe=(0.15, None),            # Greater than 15%
      volume=(None, 10e6),         # Less than 10M (None = no min)
      debt_to_equity=(None, 0.5),  # Less than 0.5
      beta=(0.8, 1.2),            # Between 0.8 and 1.2
      sector="Technology",         # String = exact match
      has_dividends=True,          # Boolean = exact match
      is_etf=False,
      industry=["Software", "Hardware"],  # List = IN operator
      limit=100,
      sort_by=["-market_cap", "pe_ratio"]  # - prefix for DESC
  )
  
  # Operator Logic:
  # (min, max)    -> min <= value <= max (both bounds)
  # (min, None)   -> value >= min (lower bound only)  
  # (None, max)   -> value <= max (upper bound only)
  # "string"      -> value = "string" (exact match)
  # boolean       -> value = boolean (exact match)
  # [list]        -> value IN (list) (any match)
  ```

### Phase 2: Integration & Optimization
- [ ] **4. Performance**
  - [ ] Add database indexes for all filterable columns
  - [ ] Implement smart query building (only JOIN needed tables)
  - [ ] Query result caching with TTL
  - [ ] Batch processing for multiple filters
  - [ ] Lazy loading of additional data
  - [ ] Target <100ms for simple queries

- [ ] **5. Sorting & Output**
  - [ ] Multi-column sorting support (- prefix for DESC)
  - [ ] Customizable output columns  
  - [ ] Result ranking/scoring
  - [ ] Export to DataFrame
  - [ ] JSON serialization

- [ ] **6. Integration**
  - [ ] Add filter models to `app/models/screener_models.py`
  - [ ] Create validation for filter inputs
  - [ ] Integrate with existing DataService
  - [ ] Add to agent tool library

## Screener Class Design

```python
# app/repositories/screener.py

from typing import Dict, List, Optional, Union, Tuple, Any
from app.db.core.db_config import MarketSession
import pandas as pd

class StockScreener:
    """
    Comprehensive stock screener with single, clean API using tuple operators.
    """
    
    def __init__(self):
        self.session = None
        self._cache = {}
    
    def screen(self, 
               limit: int = 100,
               offset: int = 0,
               sort_by: Optional[List[str]] = None,
               columns: Optional[List[str]] = None,
               **filters) -> pd.DataFrame:
        """
        Screen stocks with flexible filtering using tuple-based operators.
        
        Args:
            limit: Maximum number of results
            offset: Skip first N results  
            sort_by: List of columns to sort by (prefix with - for DESC)
            columns: Specific columns to return (None = default columns)
            **filters: Filter criteria as kwargs
        
        Filter formats:
            - Tuple (min, max): Range/comparison filter
                - (5, 20): Between 5 and 20 (inclusive)
                - (10, None): Greater than or equal to 10
                - (None, 50): Less than or equal to 50
            - String: Exact match for text fields
            - Boolean: Exact match for boolean fields
            - List: IN operator for multiple values
        
        Examples:
            pe_ratio=(5, 20)              # 5 <= pe_ratio <= 20
            market_cap=(1e9, None)         # market_cap >= 1B
            roe=(None, 0.5)               # roe <= 50%
            volume=(1e6, 10e6)            # 1M <= volume <= 10M
            sector="Technology"            # sector = "Technology"
            has_dividends=True            # has_dividends = True
            industry=["Software", "SaaS"]  # industry IN ("Software", "SaaS")
            
        Returns:
            DataFrame with screened stocks
        """
        query = self._build_query(filters, sort_by, columns)
        return self._execute_query(query, limit, offset)
    
    def _build_query(self, filters: Dict, sort_by: List[str], columns: List[str]):
        """Build optimized SQL query based on filters."""
        # Determine which tables to JOIN based on filters
        # Build WHERE clauses using tuple logic
        # Add sorting
        # Select only requested columns
        pass
    
    def _parse_filter(self, key: str, value: Any) -> str:
        """
        Parse a single filter into SQL condition.
        
        Tuple logic:
        - (min, max): BETWEEN min AND max
        - (min, None): >= min
        - (None, max): <= max
        """
        if isinstance(value, tuple) and len(value) == 2:
            min_val, max_val = value
            if min_val is not None and max_val is not None:
                return f"{key} BETWEEN {min_val} AND {max_val}"
            elif min_val is not None:
                return f"{key} >= {min_val}"
            elif max_val is not None:
                return f"{key} <= {max_val}"
        elif isinstance(value, list):
            # IN operator for lists
            quoted = [f"'{v}'" if isinstance(v, str) else str(v) for v in value]
            return f"{key} IN ({', '.join(quoted)})"
        elif isinstance(value, bool):
            return f"{key} = {str(value).upper()}"
        elif isinstance(value, str):
            return f"{key} = '{value}'"
        else:
            # Numeric exact match
            return f"{key} = {value}"
    
    def _execute_query(self, query: str, limit: int, offset: int) -> pd.DataFrame:
        """Execute query and return results as DataFrame."""
        with MarketSession() as session:
            df = pd.read_sql(query, session.bind)
            return df
```

## Key Features
1. **Single clean method**: One `screen()` method with consistent tuple operators
2. **Simple operator logic**: 
   - `(min, max)` for ranges
   - `(min, None)` for >= comparisons
   - `(None, max)` for <= comparisons
3. **Comprehensive filters**: 80+ filter options
4. **Smart query building**: Only JOINs required tables
5. **Performance focused**: Optimized SQL with targeted indexing

## Performance Goals
- Simple filters (1-5 criteria): < 50ms
- Medium filters (5-15 criteria): < 150ms
- Complex filters (15+ criteria): < 300ms
- Full market scan: < 500ms

## Database Optimizations
```sql
-- Create targeted indexes for all filter columns
CREATE INDEX idx_tickers_fundamentals ON ticker_universe.tickers(
    market_cap, pe, sector, industry, dollar_volume
);

CREATE INDEX idx_financial_ratios_key_metrics ON fundamental_data.financial_ratios(
    ticker_id, date DESC, 
    priceEarningsRatio, returnOnEquity, debtEquityRatio,
    currentRatio, grossProfitMargin
);

CREATE INDEX idx_price_technical ON price_data.prices(
    ticker_id, datetime DESC, close, volume
);
```

## Success Criteria
- Single intuitive screening method with tuple operators
- 80+ available filters
- Sub-200ms average query time
- Clean, maintainable codebase
- Easy integration with agent framework

---

## Status
**Current Phase**: Planning (Final)
**Next Action**: Awaiting approval to begin implementation
**Estimated Timeline**: 4-5 days for full implementation