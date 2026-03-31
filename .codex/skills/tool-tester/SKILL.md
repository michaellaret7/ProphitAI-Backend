---
name: tool-tester
description: >-
  Systematically test tools agent tools for correctness, error handling,
  performance, and output quality. Use when testing tools, validating tool
  outputs, benchmarking tool performance, or auditing tool error handling.
  Triggers on: test tools, benchmark tools, tool QA, tool audit.
---

## Overview

Run comprehensive tests against registered tools agent tools. For each tool,
execute valid variations, bad-arg error cases, measure wall-clock time and token
count, then evaluate output quality (insightfulness, actionability, conciseness).

## Prerequisites

- Python venv with project dependencies + `tiktoken`
- Database running (for screener/info/fundamental tools)
- `.env` loaded (test harness handles this automatically)

## Test Harness

The test harness script lives at `.codex/skills/tool-tester/scripts/test_harness.py`.

**PYTHON executable** (Windows venv):
```
.venv/Scripts/python.exe
```

**Commands:**
```bash
# List all registered tools
PYTHON .codex/skills/tool-tester/scripts/test_harness.py --list

# Show a tool's parameter schema
PYTHON .codex/skills/tool-tester/scripts/test_harness.py --schema ticker_performance

# Run a tool with args (args as JSON string)
PYTHON .codex/skills/tool-tester/scripts/test_harness.py ticker_performance '{"ticker": "AAPL", "years_back": 1}'
```

Replace `PYTHON` with the actual venv python path. Run from the **project root**.

**Output format** (JSON):
```json
{
  "tool": "ticker_performance",
  "args": {"ticker": "AAPL", "years_back": 1},
  "status": "SUCCESS",
  "elapsed_seconds": 2.145,
  "token_count": 312,
  "output_chars": 1580,
  "error": null,
  "output": "success: true\ndata:\n  ticker: AAPL\n  ..."
}
```

Status values: `SUCCESS`, `EXCEPTION` (unhandled crash), `UNKNOWN_TOOL`.

## Workflow

### Step 1: Pick tools to test

Either test **all tools** or a specific subset. Consult `references/test_cases.md`
for pre-defined test cases organized by category:

| Category | Tools | Safe to test? |
|----------|-------|---------------|
| Ticker analysis | ticker_performance, ticker_risk, ticker_factors, ticker_technicals | Yes |
| Fundamentals | get_ticker_fundamental_data, get_analyst_estimates, get_ratios_ttm, get_price_target_data | Yes |
| Info | get_ticker_info, get_etf_info, get_ticker_peers, get_stock_ratings, get_institutional_holders, get_product_segmentation | Yes |
| Portfolio | portfolio_performance, portfolio_risk, portfolio_stress_test, portfolio_factor_exposure, portfolio_classification | Yes |
| Screener | equity_screener, etf_screener | Yes |
| Research | earnings_call_search, credit_research_search, macro_research, economics_research_search, tax_research_search, user_upload_search | Needs vector DB |
| Alpaca | get_asset (safe), others (use fake IDs only) | Read-only safe, no real trades |

### Step 2: Run test cases for each tool

For each tool, run **3 types** of test cases:

**A. Valid args (2-3 variations)**
- Default/minimal args
- Different parameter combinations
- Edge-of-range valid values

**B. Bad args (2-3 variations)**
- Invalid ticker / missing required args
- Out-of-range numeric values (years_back=99, days=0)
- Wrong types (int where str expected)
- Empty strings, empty lists
- Mismatched lengths (portfolio tools: tickers vs weights)

**C. Edge cases (1-2 variations)**
- Single-element portfolios
- ETF tickers in stock tools (and vice versa)
- Very large lookback periods

### Step 3: Record results

After each test run, capture from the JSON output:
- `status` - Did it succeed or crash?
- `elapsed_seconds` - Wall-clock execution time
- `token_count` - Tokens in output (cl100k_base encoding)
- `output_chars` - Raw character count
- `error` - Error message if any

### Step 4: Evaluate each tool

After running all test cases for a tool, write an evaluation covering:

#### Error Handling Quality (1-5)
- 1: Crashes with unhandled exception, no useful message
- 3: Returns error response but message is vague
- 5: Returns clear `success: false` with specific, actionable error message

#### Output Insightfulness (1-5)
- 1: Raw data dump with no structure or context
- 3: Organized data but requires domain knowledge to interpret
- 5: Well-structured output with metrics that directly inform investment decisions

#### Output Actionability (1-5)
- 1: Data that can't be used without significant additional processing
- 3: Useful data but needs cross-referencing with other tools
- 5: Self-contained output that enables immediate decision-making

#### Token Efficiency (1-5)
- 1: Extremely bloated, >2000 tokens for simple data
- 3: Reasonable size, 500-1000 tokens
- 5: Concise, <300 tokens, no wasted space

#### Performance (1-5)
- 1: >30 seconds
- 3: 5-15 seconds
- 5: <3 seconds

### Step 5: Generate summary report

After testing all tools, produce a summary table:

```
| Tool | Valid | Bad-Arg | Time(s) | Tokens | Error Handling | Insightfulness | Actionability | Token Eff. | Perf |
|------|-------|---------|---------|--------|----------------|----------------|---------------|------------|------|
| ticker_performance | PASS | PASS | 2.1 | 312 | 4/5 | 5/5 | 4/5 | 4/5 | 4/5 |
| ...  | ...   | ...     | ...     | ...    | ...            | ...            | ...           | ...        | ...  |
```

Then write a **narrative analysis** covering:
1. **Overall findings** - How robust is the tool suite?
2. **Best tools** - Which tools excel in output quality?
3. **Worst tools** - Which need improvement and why?
4. **Error handling gaps** - Any tools that crash instead of returning error responses?
5. **Token budget concerns** - Any tools producing excessively large outputs?
6. **Performance bottlenecks** - Any tools that are too slow for interactive use?
7. **Recommendations** - Specific improvements ranked by priority

## References

- See `references/test_cases.md` for complete pre-defined test cases per tool
- Tool schemas available via `--schema <tool_name>` flag
- All tools return YAML-formatted responses via `success_response()` / `error_response()`
