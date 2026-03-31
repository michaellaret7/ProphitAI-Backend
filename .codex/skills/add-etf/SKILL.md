---
name: add-etf
description: Add an ETF to the database with proper classification. Handles web research, DB format matching, confirmation, and execution.
---

## Overview

Add a new ETF to the ProphitAI market database. This skill automates classification research (what the ETF tracks, asset class, strategy), matches it to the exact snake_case format used in the DB, and loads all data (prices, holdings, ETF info, dividends).

## Workflow

Follow these steps **in order**. Do NOT skip the confirmation step.

### Step 1: Get the ticker

Ask the user which ETF ticker to add (if not already provided).

### Step 2: Dupe check

Run the embedded helper script to see if the ticker already exists:

```bash
source .venv/bin/activate && python .codex/skills/add-etf/scripts/db_lookup.py check <TICKER>
```

- If `exists: true`, warn the user and show the existing classification. Ask if they want to proceed anyway (partial reload) or abort.

### Step 3: Web research

Use `WebSearch` to research the ETF:
- What index/asset class does it track?
- What is the investment strategy? (e.g., sovereign bonds, corporate bonds, equity index, commodities)
- Who is the issuer? (e.g., iShares, Vanguard, SPDR)

Search query: `"<TICKER> ETF what does it track asset class strategy"`

This determines the appropriate sector/industry/sub-industry classification.

### Step 4: DB query

Pull all distinct ETF classification values currently in the database:

```bash
source .venv/bin/activate && python .codex/skills/add-etf/scripts/db_lookup.py classifications
```

This returns the exact snake_case sectors, industries, and sub_industries used for ETFs in the DB.

### Step 5: Match

Map the research findings to the **exact snake_case values** from the DB query.

**Matching rules:**
- ETF sectors: `etf`, `fixed_income_etfs`, `commodity_etfs`, `cryptocurrency_etfs`, etc.
- Industries/sub-industries: snake_case (e.g., `corporate_bond_etfs`, `abs_and_mbs`, `sovereign`)
- Always use existing DB values when a match exists. Do NOT invent new classifications.
- If no exact match exists, pick the closest existing value and flag it for the user. If the ETF represents a genuinely new category, propose a new snake_case value following the existing naming convention.

Present the mapping to the user:

```
Ticker: TLT
Sector:       etf
Industry:     fixed_income_etfs
Sub-Industry: sovereign
```

### Step 6: Confirm

Ask the user to confirm the ticker and classifications before proceeding. Use `AskUserQuestion` with the mapped values shown clearly.

### Step 7: Execute

After confirmation, run the loader:

```bash
source .venv/bin/activate && python -c "
from prophitai_data.db.add_etf import load_single_etf
load_single_etf(
    '<TICKER>',
    sector='<matched_sector>',
    industry='<matched_industry>',
    sub_industry='<matched_sub_industry>'
)
"
```

## Key References

| File | Purpose |
|------|---------|
| `packages/data/src/prophitai_data/db/add_etf.py` | `OptimizedETFDataLoader` and `load_single_etf()` |
| `packages/data/src/prophitai_data/db/config.py` | `MarketSession` for DB connections |
| `packages/data/src/prophitai_data/db/models/market.py` | `Ticker` model |

## Classification Format Examples

**Sectors:** `etf`, `fixed_income_etfs`, `commodity_etfs`, `cryptocurrency_etfs`

**Industries:** `fixed_income_etfs`, `commodity_etfs`, `equity_etfs`

**Sub-Industries:** `corporate_bond_etfs`, `abs_and_mbs`, `sovereign`, `senior_loans`, `credit`
