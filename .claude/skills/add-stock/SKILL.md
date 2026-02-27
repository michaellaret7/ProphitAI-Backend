---
name: add-stock
description: Add a stock ticker to the database with proper GICS classification. Handles web lookup, DB format matching, confirmation, and execution.
---

## Overview

Add a new stock (equity) ticker to the ProphitAI market database. This skill automates the GICS classification lookup, matches it to the exact snake_case format used in the DB, and loads all data (prices, fundamentals, news, grades, ratings).

## Workflow

Follow these steps **in order**. Do NOT skip the confirmation step.

### Step 1: Get the ticker

Ask the user which stock ticker to add (if not already provided).

### Step 2: Dupe check

Run the embedded helper script to see if the ticker already exists:

```bash
source .venv/bin/activate && python .claude/skills/add-stock/scripts/db_lookup.py check <TICKER>
```

- If `exists: true`, warn the user and show the existing classification. Ask if they want to proceed anyway (partial reload) or abort.

### Step 3: Web lookup

Use `WebSearch` to find the ticker's **exact GICS classification**:
- **Sector** (e.g., Information Technology)
- **Industry Group** (e.g., Semiconductors & Semiconductor Equipment)
- **Industry** (e.g., Semiconductors)
- **Sub-Industry** (e.g., Semiconductors)

Search query: `"<TICKER> GICS sector industry sub-industry classification"`

### Step 4: DB query

Pull all distinct classification values currently in the database:

```bash
source .venv/bin/activate && python .claude/skills/add-stock/scripts/db_lookup.py classifications
```

This returns the exact snake_case sectors, industries, and sub_industries used in the DB.

### Step 5: Match

Map the GICS lookup results to the **exact snake_case values** from the DB query.

**Matching rules:**
- Sector format: `equity_sector_<name>` (e.g., `equity_sector_information_technology`)
- Industry/sub-industry: pure snake_case (e.g., `semiconductors_and_semiconductor_equipment`)
- Always use existing DB values when a match exists. Do NOT invent new classifications.
- If no exact match exists, pick the closest existing value and flag it for the user.

Present the mapping to the user:

```
Ticker: NVDA
Sector:       equity_sector_information_technology
Industry:     semiconductors_and_semiconductor_equipment
Sub-Industry: semiconductors
```

### Step 6: Confirm

Ask the user to confirm the ticker and classifications before proceeding. Use `AskUserQuestion` with the mapped values shown clearly.

### Step 7: Execute

After confirmation, run the loader:

```bash
source .venv/bin/activate && python -c "
from app.db.core.add_ticker import load_single_ticker
load_single_ticker(
    '<TICKER>',
    sector='<matched_sector>',
    industry='<matched_industry>',
    sub_industry='<matched_sub_industry>'
)
"
```

**Important:** The function is `load_single_ticker` from `app.db.core.add_ticker`, NOT `load_single_stock`.

## Key References

| File | Purpose |
|------|---------|
| `app/db/core/add_ticker.py` | `OptimizedTickerDataLoader` and `load_single_ticker()` |
| `app/db/core/db_config.py` | `MarketSession` for DB connections |
| `app/db/core/models/market_data_models.py` | `Ticker` model |

## Classification Format Examples

**Sectors:** `equity_sector_information_technology`, `equity_sector_financials`, `equity_sector_health_care`, `equity_sector_consumer_discretionary`, `equity_sector_industrials`

**Industries:** `semiconductors_and_semiconductor_equipment`, `software`, `capital_markets`, `pharmaceuticals`

**Sub-Industries:** `semiconductors`, `application_software`, `asset_management_and_custody_banks`
