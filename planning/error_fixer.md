# Error Report

## Date: 2025-09-19
## Error: get_stock_news() got an unexpected keyword argument 'session'

### Error Context
When the agent calls `fetch_repository_data` tool with `data_type="stock_news"`, it results in:
```
Error calling tool 'fetch_repository_data': get_stock_news() got an unexpected keyword argument 'session' 
(args={'ticker': 'SPTN', 'data_type': 'stock_news'})
```

### Root Cause Analysis
The issue stems from incorrect session management between nested functions that both use the `@with_session` decorator:

1. **`fetch_repository_data`** in `app/core/agentic_framework/base_agent/tool_lib/data/repository.py`:
   - Has `@with_session('market')` decorator
   - Incorrectly includes `session=None` in its function signature
   - The decorator already injects the session via kwargs

2. **`get_stock_news`** in `app/repositories/news_data.py`:
   - Also has `@with_session('market')` decorator
   - Does NOT have `session` in its function signature
   - Retrieves session using `locals().get('session')`

3. When `fetch_repository_data` calls `get_stock_news()`, the session parameter from the outer function is not being passed, but the decorator tries to inject it causing a conflict.

### Solution Plan
1. Remove the `session=None` parameter from `fetch_repository_data` function signature
2. Since the function has `@with_session` decorator, it will handle session injection automatically
3. This ensures clean session management without parameter conflicts

### Implementation
Remove `session=None` from line 10 in `/Users/michaellaret/Desktop/ProphitAI/app/core/agentic_framework/base_agent/tool_lib/data/repository.py`

Change:
```python
def fetch_repository_data(ticker: str, data_type: str, limit: int | None = None, session=None):
```

To:
```python
def fetch_repository_data(ticker: str, data_type: str, limit: int | None = None):
```

This fix maintains the decorator's session management while preventing parameter conflicts with nested functions.

### Status: COMPLETED ✓
The fix has been successfully applied to the codebase. The `session` parameter has been removed from the function signature, allowing the `@with_session` decorator to manage sessions properly without conflicts.