# Memory Store Structure Issue Analysis

## Issue Summary
The `beverages_memory.json` file has a different structure than expected by the `semantic_memory.py` loader, resulting in 0 memories being loaded despite the file being read successfully.

## Root Cause
The `semantic_memory.py` code expects one of two JSON structures, but `beverages_memory.json` doesn't match either.

### Expected Structures
The code in `semantic_memory.py` (lines 46-56) expects:

1. **Primary schema:**
```json
{
  "memories": {
    "<category>": [
      { "title": "...", "content": "...", ... }
    ]
  }
}
```

2. **Alternate schema (like cro_memory.json):**
```json
{
  "current_date": "2025-09-05",
  "<category>": [
    { "title": "...", "content": "...", ... }
  ]
}
```

### Actual Structure Issues

**beverages_memory.json structure:**
```json
{
  "agent_memory": {
    "domain": "...",
    "purpose": "...", 
    "sections": [
      {
        "id": 1,
        "topic": "...",
        "context": "...",
        ...
      }
    ]
  }
}
```

**Problems:**
1. Root key is `"agent_memory"` instead of `"memories"` or direct category names
2. Memory items are nested inside `"agent_memory" > "sections"` instead of being at the top level or under `"memories"`
3. Field naming mismatch:
   - Uses `"topic"` instead of `"title"`
   - Uses `"context"` instead of `"content"`
   - Missing `"application"` field (has different fields like `"investment_insight"`, `"additional_notes"`, etc.)
4. No `"current_date"` field at root level (has `"last_updated"` inside `"agent_memory"`)

## Why CRO Memory Works
The `cro_memory.json` follows the alternate schema:
- Has categories directly at root level (`"risk_management"` is a list)
- Each item has standard fields: `"title"`, `"content"`, `"suggested_tools"`, `"application"`
- Has `"current_date"` at root level

---

# Proposed Unified Memory Structure

## Recommended Standard Structure

```json
{
  "agent_memory": {
    "type": "Semantic",
    "agent": "beverages_industry",
    "domain": "Beverages industry stock picking",
    "purpose": "Nuanced concepts for portfolio construction/stock picking",
    "last_updated": "2025-09-05",
    "memories": {
      "tickers": ["IBG", "BF/B", "VINE", "BLNE", "TAP", "MNST", "SAM", "CCEP", "PRMB", "CASK", "ZVIA", "WVVI", "COKE", "MGPI", "STZ", "KO", "COCO", "PEP", "SBEV", "FIZZ", "CELH", "KDP"],
      "category_name": [
        {
          "existing_field_1": "existing_value_1",
          "existing_field_2": "existing_value_2"
        }
      ]
    }
  }
}
```

## Benefits of This Structure

1. **Clear Agent Identification**
   - `type` field specifies the memory type (Semantic, Episodic, etc.)
   - `agent` field clearly identifies which agent these memories belong to
   - Domain and purpose fields provide context immediately after agent

2. **Preserved Original Content**
   - All original memory fields remain unchanged
   - No data loss during migration
   - Existing field names and structures maintained

3. **Consistent Root Structure**
   - Always starts with `agent_memory`
   - Always has `type`, `agent`, `domain`, `purpose`, `last_updated`
   - `memories` dict always contains the actual memory content

4. **Tickers First in Memories**
   - When applicable, tickers list appears first in memories dict
   - Easy to find and reference
   - Clear organization of data

## Migration Completed

### ✅ Phase 1: Updated semantic_memory.py (COMPLETE)
- Removed ALL backward compatibility code
- Now ONLY supports the unified structure
- Will raise error if memory file doesn't have 'agent_memory' root key

### ✅ Phase 2: Migration Scripts (COMPLETE)
- Converted `cro_memory.json` to new unified format
- Converted `beverages_memory.json` to new unified format
- Both files now follow the standard structure

### ✅ Phase 3: Update All Memory Files (COMPLETE)
- All memory files converted to new format
- semantic_memory.py now enforces unified structure
- Date update functions work with new format only

### Final Implementation Status
**The new unified memory structure is now the single source of truth:**
- No backward compatibility code remains
- All memory files must follow the unified structure
- `_load_memories()` requires 'agent_memory' root key
- `_save_memories()` only saves in unified format
- `_update_current_date_in_memory()` only updates new format
- `get_current_date()` only reads from new format

## Example Conversions

### Converting beverages_memory.json (keep all original content):
```json
{
  "agent_memory": {
    "type": "Semantic",
    "agent": "beverages_industry",
    "domain": "Beverages industry stock picking",
    "purpose": "Nuanced concepts for portfolio construction/stock picking",
    "last_updated": "2025-09-05",
    "memories": {
      "tickers": ["IBG", "BF/B", "VINE", "BLNE", "TAP", "MNST", "SAM", "CCEP", "PRMB", "CASK", "ZVIA", "WVVI", "COKE", "MGPI", "STZ", "KO", "COCO", "PEP", "SBEV", "FIZZ", "CELH", "KDP"],
      "sections": [
        {
          "id": 1,
          "topic": "Shelf Space Dynamics & Distribution Economics",
          "context": "Unlike many other consumer goods, shelf space in beverages is extraordinarily valuable and finite...",
          "investment_insight": "Key Investment Insight: Companies with strong distributor relationships...",
          "additional_notes": "The 'fair share +2 facings' strategy has proven highly effective...",
          "metrics_raw": [...],
          "metrics_structured": {
            "slotting_fee_regional_low_usd": 250,
            "slotting_fee_regional_high_usd": 1000
          }
        },
        {
          "id": 2,
          "topic": "Seasonality & Consumption Pattern Analytics",
          "context": "Beverage consumption exhibits extreme seasonality...",
          "investment_angle": "Investment Angle: Track companies' ability to capitalize...",
          "additional_notes": "Seasonal flavors like pumpkin and peppermint...",
          "metrics_raw": [...],
          "metrics_structured": {
            "peak_months_current": ["February", "May", "June"],
            "seasonal_flavor_growth_pct_min": 25
          }
        }
        // ... all other sections with their original fields unchanged
      ]
    }
  }
}
```

### Converting cro_memory.json (preserve all original fields):
```json
{
  "agent_memory": {
    "type": "Semantic",
    "agent": "cro",
    "domain": "Risk Management",
    "purpose": "Risk management principles and tools",
    "current_date": "2025-09-05",
    "memories": {
      "risk_management": [
        {
          "title": "Covariance Matrix for Portfolio Risk",
          "content": "The covariance matrix quantifies joint variability between assets and is the foundation for portfolio variance, marginal risk contributions, and risk budgeting. Because daily returns are small, values are small but critical; use it to measure total volatility, tracking error, and how each position contributes to risk.",
          "suggested_tools": ["calculate_covariance_matrix"],
          "application": "Compute daily-return covariance and use it to estimate portfolio variance and marginal risk; prioritize reallocations that reduce outsized risk contributors."
        },
        {
          "title": "Correlation Matrix for Diversification",
          "content": "The correlation matrix normalizes co-movement to the -1 to +1 scale, revealing clusters and hidden concentration. It is position-agnostic (long/short does not change correlation), and helps ensure true diversification across names, factors, and industries.",
          "suggested_tools": ["calculate_correlation_matrix"],
          "application": "Review correlations and remove or downsize highly correlated names; prefer complementary exposures with low or negative correlation."
        },
        {
          "title": "Stress Tests and What to Watch",
          "content": "Stress tests expose non-linear and regime risks that variance-based metrics miss. Focus on path-dependent drawdowns, peak-to-trough loss, downside/upside capture, factor and sector tilts, and sensitivity to market shocks.",
          "suggested_tools": ["stress_test"],
          "application": "Run baseline and severe scenarios; reject portfolios with unacceptable drawdowns or excessive downside capture, and adjust hedges or sizing accordingly."
        },
        {
          "title": "General Risk Management Principles",
          "content": "Size by risk not just conviction, cap single-name and sector exposure, balance gross/net exposure, maintain hedges, monitor regimes, and rebalance when exposures drift. Use data-driven checks before approvals.",
          "suggested_tools": ["calculate_correlation_matrix", "calculate_covariance_matrix"],
          "application": "Set risk limits, review metrics regularly, and rebalance to keep exposures and risk contributions within bounds."
        }
      ]
    }
  }
}
```
