# Missing FMP Endpoints Analysis

## Currently Implemented in pull_fmp_data.py (43 endpoints)
1. analyst-estimates
2. earnings-surprises
3. rating
4. cash-flow-statement
5. balance-sheet-statement
6. income-statement
7. ratios
8. key-metrics
9. financial-scores
10. revenue-product-segmentation
11. revenue-geographic-segmentation
12. etf/holdings
13. etf/info
14. etf/country-weightings
15. dividends
16. news/press-releases
17. news/stock
18. news/general-latest
19. fmp-articles
20. earning-call-transcript
21. ratings-historical
22. price-target-summary
23. price-target-news
24. grades
25. grades-historical
26. grades-news
27. historical-chart/15min
28. historical-price-full
29. quote
30. batch-quote
31. profile
32. search-isin
33. company-notes
34. stock-peers
35. esg-disclosures
36. institutional-ownership/extract-analytics/holder
37. institutional-ownership/symbol-positions-summary
38. historical-sector-performance
39. historical-industry-performance
40. historical-sector-pe
41. historical-industry-pe
42. mergers-acquisitions-latest
43. mergers-acquisitions-search

---

## Missing Endpoints by Category

### Company Information (11 missing)
- /profile-cik
- /delisted-companies
- /employee-count
- /historical-employee-count
- /market-capitalization
- /market-capitalization-batch
- /historical-market-capitalization
- /shares-float
- /shares-float-all
- /key-executives
- /governance-executive-compensation
- /executive-compensation-benchmark

### Quote - Exchange & Asset Lists (7 missing)
- /batch-exchange-quote
- /batch-mutualfund-quotes
- /batch-etf-quotes
- /batch-commodity-quotes
- /batch-crypto-quotes
- /batch-forex-quotes
- /batch-index-quotes

### Financial Statements & Ratios (18 missing)
- /latest-financial-statements
- /income-statement-ttm
- /balance-sheet-statement-ttm
- /cash-flow-statement-ttm
- /key-metrics-ttm
- /ratios-ttm
- /owner-earnings
- /enterprise-values
- /income-statement-growth
- /balance-sheet-statement-growth
- /cash-flow-statement-growth
- /financial-growth

### Economics (4 missing)
- /treasury-rates
- /economic-indicators
- /economic-calendar
- /market-risk-premium

### Earnings, Dividends & Splits (7 missing)
- /dividends-calendar
- /earnings
- /earnings-calendar
- /ipos-calendar
- /ipos-disclosure
- /ipos-prospectus
- /splits
- /splits-calendar

### Earnings Transcript (3 missing)
- /earning-call-transcript-latest
- /earning-call-transcript-dates
- /earnings-transcript-list

### News (5 missing)
- /news/press-releases-latest
- /news/stock-latest
- /news/crypto-latest
- /news/forex-latest
- /news/crypto
- /news/forex

### Form 13F / Institutional Ownership (5 missing)
- /institutional-ownership/latest
- /institutional-ownership/extract
- /institutional-ownership/dates
- /institutional-ownership/holder-performance-summary
- /institutional-ownership/holder-industry-breakdown
- /institutional-ownership/industry-summary

### Analyst (3 missing)
- /ratings-snapshot
- /price-target-consensus
- /grades-consensus

### Technical Indicators (9 missing)
- /technical-indicators/sma
- /technical-indicators/ema
- /technical-indicators/wma
- /technical-indicators/dema
- /technical-indicators/tema
- /technical-indicators/rsi
- /technical-indicators/standarddeviation
- /technical-indicators/williams
- /technical-indicators/adx

### ETF & Mutual Funds (5 missing)
- /etf/asset-exposure
- /etf/sector-weightings
- /funds/disclosure-holders-latest
- /funds/disclosure
- /funds/disclosure-holders-search
- /funds/disclosure-dates

### SEC Filings & Industry Classification (12 missing)
- /sec-filings-8k
- /sec-filings-financials
- /sec-filings-search/form-type
- /sec-filings-search/symbol
- /sec-filings-search/cik
- /sec-filings-company-search/name
- /sec-filings-company-search/symbol
- /sec-filings-company-search/cik
- /sec-profile
- /standard-industrial-classification-list
- /industry-classification-search
- /all-industry-classification

### Insider Trades (6 missing)
- /insider-trading/latest
- /insider-trading/search
- /insider-trading/reporting-name
- /insider-trading-transaction-type
- /insider-trading/statistics
- /acquisition-of-beneficial-ownership


### Market Hours (3 missing)
- /exchange-market-hours
- /holidays-by-exchange
- /all-exchange-market-hours

### Commodity (1 missing)
- /commodities-list

### Discounted Cash Flow (4 missing)
- /discounted-cash-flow
- /levered-discounted-cash-flow
- /custom-discounted-cash-flow
- /custom-levered-discounted-cash-flow

### Forex (1 missing)
- /forex-list

### Crypto (1 missing)
- /cryptocurrency-list

### Senate & House Trading (6 missing)
- /senate-latest
- /house-latest
- /senate-trades
- /senate-trades-by-name
- /house-trades
- /house-trades-by-name

### ESG (2 missing)
- /esg-ratings
- /esg-benchmark

### Commitment Of Traders (3 missing)
- /commitment-of-traders-report
- /commitment-of-traders-analysis
- /commitment-of-traders-list

### Fundraisers & Crowdfunding (6 missing)
- /crowdfunding-offerings-latest
- /crowdfunding-offerings-search
- /crowdfunding-offerings
- /fundraising-latest
- /fundraising-search
- /fundraising

### Bulk Endpoints (17 missing)
- /profile-bulk
- /rating-bulk
- /dcf-bulk
- /scores-bulk
- /price-target-summary-bulk
- /etf-holder-bulk
- /upgrades-downgrades-consensus-bulk
- /key-metrics-ttm-bulk
- /ratios-ttm-bulk
- /peers-bulk
- /earnings-surprises-bulk
- /income-statement-bulk
- /income-statement-growth-bulk
- /balance-sheet-statement-bulk
- /balance-sheet-statement-growth-bulk
- /cash-flow-statement-bulk
- /cash-flow-statement-growth-bulk
- /eod-bulk

