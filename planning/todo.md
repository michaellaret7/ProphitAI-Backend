# Portfolio Dictionary Normalization Task

## Instances Found Where Portfolio Dictionaries Are Used As Input Arguments

### Target Format: 
```json
{
  "ticker": {
    "allocation": float,
    "position": "long"/"short"
  }
}
```

### Files to Update:

1. **backend/src/stress_test/engine.py**
   - `run_stress_test_engine(portfolio_dict: dict, etf_shocks: dict, pre_calculated_betas: dict = None)`
   - Current format: `{ticker: {'conviction': float, 'position': str}}`

2. **backend/src/stress_test/runner.py**
   - `__init__(self, portfolio_dict: dict)`
   - Current format: `{ticker: {'conviction': float, 'position': str}}`

3. **backend/src/stress_test/performance_analysis.py**
   - `contribution_analysis(scenario_results, portfolio_dict=None)`
   - `performance_analysis(scenario_results, portfolio_dict=None)`
   - Current format: `{ticker: {'conviction': float, 'position': str}}`

4. **backend/src/stress_test/pairwise_corr_analysis.py**
   - `run_pairwise_correlation_analysis(portfolio_dict: dict)`
   - Current format: Dictionary with tickers as keys

5. **backend/src/prophit_alts/consumer_staples_fund/build_portfolio/cio/tools.py**
   - `correlation_matrix(portfolio_dict: dict, lookback_days: int = 252)`
   - `exposure_calculator(portfolio_dict: dict, exposure_type: str)`
   - `industry_concentration(portfolio_dict: dict, industry_level: str)`
   - `VaR_calculator(portfolio_dict: dict, level: str)`
   - `factor_tilts_for_portfolio(portfolio_dict: dict, factors: str)`
   - Current format: Various formats

6. **backend/src/prophit_alts/consumer_staples_fund/build_portfolio/cro/tools.py**
   - `calculate_correlation_matrix(portfolio_dict: dict = None)`
   - `calculate_covariance_matrix(portfolio_dict: dict = None)`
   - `vol_es(portfolio_dict: dict = None, horizon_days: int = 1, conf: float = 0.99, method: str = 'param')`
   - `risk_contribution(portfolio_dict: dict = None, metric: str = 'vol')`
   - `drawdown_profile(portfolio_dict: dict = None)`
   - Current format: Various formats

7. **backend/src/calculations/trade_entry.py**
   - `get_entry_prices(portfolio: Dict[str, Tuple[float, str]], debug: bool = False)`
   - Current format: `{ticker: (weight, position_type)}`

8. **backend/src/calculations/performance_calculations/portfolio_performance_calculations.py**
   - `get_upside_downside_ratios(portfolio_dict: dict)`
   - Current format: `{ticker: {'conviction': float, 'position': str}}`
   - `__init__(self, tickers_weights: Dict[str, float], start_date: str, end_date: str)`
   - Current format: `{ticker: weight}`

9. **backend/src/calculations/returns_calculations/portfolio_returns_calculations.py**
   - `__init__(self, tickers_weights: Dict[str, float], start_date: str, end_date: str)`
   - Current format: `{ticker: weight}` (signed weights for long/short)

10. **backend/src/utils/validation_utils.py**
    - `validate_portfolio_dict(portfolio_dict: dict)`
    - Current format: Various formats

11. **backend/src/prophit_alts/consumer_staples_fund/build_portfolio/cio/tool_registry.py**
    - Multiple lambda functions that accept `portfolio_dict` parameter
    - Current format: Various formats

### Note:
Some instances use different field names like 'conviction' instead of 'allocation', and some use tuple formats instead of dictionaries. All need to be normalized to the target format.
