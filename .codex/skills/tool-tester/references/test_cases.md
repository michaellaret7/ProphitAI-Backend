# Test Cases for tools

Pre-defined test cases organized by category. Each tool has **valid**, **bad-arg**, and **edge-case** variations.

Run via:
```bash
PYTHON test_harness.py <tool_name> '<args_json>'
```

---

## 1. Ticker Analysis Tools

### ticker_performance
| Label | Args | Expect |
|-------|------|--------|
| valid-basic | `{"ticker": "AAPL", "years_back": 1}` | Success with ~15 metrics |
| valid-max-range | `{"ticker": "MSFT", "years_back": 5}` | Success, includes momentum_3yr |
| valid-etf | `{"ticker": "SPY", "years_back": 2}` | Success (benchmark vs itself) |
| bad-ticker | `{"ticker": "ZZZZXYZ123"}` | Graceful error (no price data) |
| bad-empty | `{"ticker": ""}` | Graceful error |
| bad-years-high | `{"ticker": "AAPL", "years_back": 99}` | Error or constraint rejection |
| bad-years-zero | `{"ticker": "AAPL", "years_back": 0}` | Error or constraint rejection |
| bad-missing-arg | `{}` | TypeError (missing required ticker) |
| bad-wrong-type | `{"ticker": 12345}` | Error (int instead of str) |

### ticker_risk
| Label | Args | Expect |
|-------|------|--------|
| valid-basic | `{"ticker": "TSLA", "years_back": 1}` | Success with risk metrics |
| valid-stable | `{"ticker": "KO", "years_back": 3}` | Lower vol than TSLA |
| bad-ticker | `{"ticker": "NOTREAL"}` | Graceful error |
| bad-negative-years | `{"ticker": "AAPL", "years_back": -1}` | Error |

### ticker_factors
| Label | Args | Expect |
|-------|------|--------|
| valid-all | `{"ticker": "NVDA", "category": "all", "years_back": 2}` | All 6 factor categories |
| valid-single | `{"ticker": "JPM", "category": "value", "years_back": 1}` | Only value factors |
| valid-momentum | `{"ticker": "AAPL", "category": "momentum"}` | Momentum factors only |
| bad-category | `{"ticker": "AAPL", "category": "nonexistent"}` | Error (invalid literal) |
| bad-ticker | `{"ticker": "FAKE123", "category": "all"}` | Graceful error |

### ticker_technicals
| Label | Args | Expect |
|-------|------|--------|
| valid-trend | `{"ticker": "AAPL", "category": "trend", "days": 20}` | SMA, EMA series |
| valid-momentum | `{"ticker": "GOOGL", "category": "momentum", "days": 10}` | RSI, MACD series |
| valid-min-days | `{"ticker": "MSFT", "category": "volatility", "days": 1}` | 1 data point |
| bad-category | `{"ticker": "AAPL", "category": "fake"}` | Error |
| bad-days-high | `{"ticker": "AAPL", "category": "trend", "days": 999}` | Constraint error |
| bad-missing-cat | `{"ticker": "AAPL"}` | TypeError (category is required) |

---

## 2. Fundamental Data Tools

### get_ticker_fundamental_data
| Label | Args | Expect |
|-------|------|--------|
| valid-income | `{"ticker": "AAPL", "statement_type": "income_statement", "quarters_back": 4}` | 4 quarters of income data |
| valid-balance | `{"ticker": "MSFT", "statement_type": "balance_sheet", "quarters_back": 2}` | Balance sheet data |
| valid-cashflow | `{"ticker": "GOOGL", "statement_type": "cash_flow"}` | Default 2 quarters |
| valid-ratios | `{"ticker": "JPM", "statement_type": "financial_ratios", "quarters_back": 8}` | Financial ratios |
| bad-statement | `{"ticker": "AAPL", "statement_type": "fake_statement"}` | Error |
| bad-quarters | `{"ticker": "AAPL", "statement_type": "income_statement", "quarters_back": 100}` | Constraint error |

### get_analyst_estimates
| Label | Args | Expect |
|-------|------|--------|
| valid-default | `{"ticker": "AAPL"}` | 4 quarters, all outlook |
| valid-annual | `{"ticker": "MSFT", "period": "annual", "periods_back": 3}` | Annual estimates |
| valid-future | `{"ticker": "NVDA", "outlook": "future_estimates"}` | Forward estimates only |
| bad-ticker | `{"ticker": "ZZZFAKE"}` | Graceful error or empty |

### get_ratios_ttm
| Label | Args | Expect |
|-------|------|--------|
| valid | `{"ticker": "AAPL"}` | TTM ratios dict |
| valid-bank | `{"ticker": "JPM"}` | Bank-specific ratios |
| bad-ticker | `{"ticker": "NOTREAL123"}` | Graceful error |

### get_price_target_data
| Label | Args | Expect |
|-------|------|--------|
| valid-consensus | `{"ticker": "AAPL", "data_type": "consensus"}` | Price target consensus |
| valid-both | `{"ticker": "TSLA", "data_type": "both"}` | Consensus + summary |
| bad-type | `{"ticker": "AAPL", "data_type": "invalid"}` | Error |

---

## 3. Ticker Info Tools

### get_ticker_info
| Label | Args | Expect |
|-------|------|--------|
| valid | `{"ticker": "AAPL"}` | Company metadata |
| valid-small | `{"ticker": "PLTR"}` | Smaller company |
| bad-ticker | `{"ticker": "ZZZNOTREAL"}` | Graceful error |

### get_etf_info
| Label | Args | Expect |
|-------|------|--------|
| valid-spy | `{"ticker": "SPY"}` | ETF metadata |
| valid-bond | `{"ticker": "TLT"}` | Bond ETF |
| bad-stock-not-etf | `{"ticker": "AAPL"}` | Error or empty (not an ETF) |

### get_ticker_peers
| Label | Args | Expect |
|-------|------|--------|
| valid | `{"ticker": "AAPL"}` | List of peer companies |
| valid-bank | `{"ticker": "JPM"}` | Financial peers |
| bad-ticker | `{"ticker": "FAKEXYZ"}` | Graceful error or empty |

### get_stock_ratings
| Label | Args | Expect |
|-------|------|--------|
| valid-single | `{"tickers": ["AAPL"]}` | Summary ratings |
| valid-multi | `{"tickers": ["AAPL", "MSFT", "GOOGL"], "data_type": "all"}` | All data types |
| valid-scores | `{"tickers": ["NVDA"], "data_type": "scores"}` | Quality scores |
| bad-empty-list | `{"tickers": []}` | Graceful error or empty |
| bad-many-days | `{"tickers": ["AAPL"], "days_back": 9999}` | Constraint error |

### get_institutional_holders
| Label | Args | Expect |
|-------|------|--------|
| valid | `{"ticker": "AAPL", "year": 2025, "quarter": 3}` | Institutional holders |
| valid-small | `{"ticker": "AAPL", "year": 2024, "quarter": 1, "row_limit": 10}` | Limited results |
| bad-future | `{"ticker": "AAPL", "year": 2030, "quarter": 4}` | Empty or error |
| bad-quarter | `{"ticker": "AAPL", "year": 2025, "quarter": 5}` | Constraint error |

### get_product_segmentation
| Label | Args | Expect |
|-------|------|--------|
| valid | `{"ticker": "AAPL"}` | Product revenue segments |
| valid-diverse | `{"ticker": "JNJ"}` | Diversified segments |
| bad-ticker | `{"ticker": "NOTREAL"}` | Graceful error |

---

## 4. Portfolio Tools

### portfolio_performance
| Label | Args | Expect |
|-------|------|--------|
| valid-3stock | `{"tickers": ["AAPL", "MSFT", "GOOGL"], "weights": [0.40, 0.35, 0.25]}` | Performance metrics |
| valid-5stock | `{"tickers": ["SPY", "TLT", "GLD", "VNQ", "EEM"], "weights": [0.30, 0.25, 0.15, 0.15, 0.15], "years_back": 3}` | Diversified portfolio |
| bad-mismatch | `{"tickers": ["AAPL"], "weights": [0.5, 0.5]}` | Error (length mismatch) |
| bad-empty | `{"tickers": [], "weights": []}` | Error |

### portfolio_risk
| Label | Args | Expect |
|-------|------|--------|
| valid | `{"tickers": ["AAPL", "MSFT", "JPM"], "weights": [0.40, 0.30, 0.30], "years_back": 2}` | Risk metrics |
| valid-concentrated | `{"tickers": ["TSLA"], "weights": [1.0]}` | Single stock risk |
| bad-mismatch | `{"tickers": ["AAPL", "MSFT"], "weights": [0.5]}` | Error |

### portfolio_stress_test
| Label | Args | Expect |
|-------|------|--------|
| valid-basic | `{"tickers": ["AAPL", "MSFT", "GOOGL"], "weights": [0.40, 0.35, 0.25], "shocks": {"SPY": -0.05, "TLT": 0.10}}` | Stress results |
| valid-complex | `{"tickers": ["AAPL", "TSLA", "JPM", "XOM"], "weights": [0.30, 0.20, 0.25, 0.25], "shocks": {"SPY": -0.10, "TLT": 0.15, "GLD": 0.05, "XLE": -0.08}, "years_back": 3}` | Multi-factor stress |
| bad-empty-shocks | `{"tickers": ["AAPL"], "weights": [1.0], "shocks": {}}` | Error (empty shocks) |
| bad-mismatch | `{"tickers": ["AAPL"], "weights": [0.5, 0.5], "shocks": {"SPY": -0.05}}` | Error |

### portfolio_factor_exposure
| Label | Args | Expect |
|-------|------|--------|
| valid | `{"tickers": ["AAPL", "MSFT", "JPM"], "weights": [0.40, 0.30, 0.30]}` | Factor z-scores and tilt summary |
| valid-tech-heavy | `{"tickers": ["NVDA", "AAPL", "MSFT", "GOOGL"], "weights": [0.30, 0.25, 0.25, 0.20], "years_back": 3}` | Tech-heavy factor profile |
| bad-mismatch | `{"tickers": ["AAPL"], "weights": []}` | Error |

### portfolio_classification
| Label | Args | Expect |
|-------|------|--------|
| valid | `{"tickers": ["AAPL", "JPM", "XOM", "JNJ"], "weights": [0.25, 0.25, 0.25, 0.25]}` | Sector/industry breakdown |
| valid-concentrated | `{"tickers": ["NVDA", "AAPL", "MSFT"], "weights": [0.50, 0.30, 0.20]}` | Tech concentration |
| bad-empty | `{"tickers": [], "weights": []}` | Error |

---

## 5. Screener Tools

### equity_screener
| Label | Args | Expect |
|-------|------|--------|
| valid-value | `{"pe_ratio_ttm": [null, 15], "dividend_yield_ttm": [0.03, null]}` | Value stocks |
| valid-growth | `{"revenue_growth_ttm": [0.20, null], "market_cap": [10000000000, null]}` | Large-cap growth |
| valid-minimal | `{}` | All equities (or default filter) |
| bad-range | `{"pe_ratio_ttm": "not_a_list"}` | Error |

### etf_screener
| Label | Args | Expect |
|-------|------|--------|
| valid-low-cost | `{"expense_ratio": [null, 0.001]}` | Low-cost ETFs |
| valid-minimal | `{}` | All ETFs |

---

## 6. Research Tools

> Note: Research tools depend on vector database availability. They may fail
> if the Qdrant/embedding service is not running. Test error handling in that case.

### earnings_call_search
| Label | Args | Expect |
|-------|------|--------|
| valid-basic | `{"query": "revenue growth and margin expansion guidance"}` | Top 5 results |
| valid-filtered | `{"query": "AI spending capex", "ticker": "MSFT", "fiscal_year": 2025, "top_k": 3}` | Filtered results |
| valid-multi | `{"query": "tariff impact on supply chain", "tickers": ["AAPL", "TSLA"]}` | Multi-ticker |
| bad-empty-query | `{"query": ""}` | Graceful error |

### credit_research_search
| Label | Args | Expect |
|-------|------|--------|
| valid | `{"query": "high yield spreads credit default risk", "top_k": 5}` | Credit research |
| bad-empty | `{"query": ""}` | Graceful error |

### macro_research
| Label | Args | Expect |
|-------|------|--------|
| valid | `{"query": "federal reserve interest rate outlook inflation", "top_k": 5}` | Macro research |
| valid-provider | `{"query": "GDP growth forecast", "research_provider": "JPMorgan"}` | Provider filter |
| bad-empty | `{"query": ""}` | Graceful error |

### economics_research_search
| Label | Args | Expect |
|-------|------|--------|
| valid | `{"query": "unemployment rate labor market trends"}` | Economics results |

### tax_research_search
| Label | Args | Expect |
|-------|------|--------|
| valid | `{"query": "capital gains tax loss harvesting rules"}` | Tax research |

### user_upload_search
| Label | Args | Expect |
|-------|------|--------|
| valid | `{"query": "portfolio allocation strategy"}` | User doc results |

---

## 7. Alpaca Broker Tools

> CAUTION: These interact with real broker APIs. Only test error handling
> with clearly invalid account IDs. Do NOT submit real trades during testing.

### get_asset (safe - read-only, no account needed)
| Label | Args | Expect |
|-------|------|--------|
| valid-stock | `{"symbol": "AAPL"}` | Asset details |
| valid-crypto | `{"symbol": "BTC/USD"}` | Crypto asset |
| bad-symbol | `{"symbol": "ZZZNOTREAL999"}` | Graceful error |

### account_info (use fake account_id for error testing)
| Label | Args | Expect |
|-------|------|--------|
| bad-fake-id | `{"account_id": "00000000-0000-0000-0000-000000000000"}` | API error |
| bad-missing | `{}` | TypeError |

### account_activities
| Label | Args | Expect |
|-------|------|--------|
| bad-fake-id | `{"account_id": "00000000-0000-0000-0000-000000000000", "activity_type": "FILL"}` | API error |
| bad-activity | `{"account_id": "fake", "activity_type": "INVALID"}` | Constraint error |

### submit_trade (DO NOT test with valid accounts)
| Label | Args | Expect |
|-------|------|--------|
| bad-fake | `{"account_id": "fake", "symbol": "AAPL", "side": "buy", "qty": 1}` | API error |
| bad-no-qty | `{"account_id": "fake", "symbol": "AAPL", "side": "buy"}` | Error (no qty or notional) |
| bad-side | `{"account_id": "fake", "symbol": "AAPL", "side": "invalid", "qty": 1}` | Constraint error |
