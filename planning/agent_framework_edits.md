### Deterministic Tool-Output Index — Implementation Plan

- **Goal**: Fast, precise retrieval of past tool outputs via deterministic keys (tool + normalized args). No vector fallback in this phase.

### Scope
- Source: `backend/src/agentic_framework/agent_output/agent_messages.json`
- Folder: `backend/testing/tool_lookup/`
- New files:
  - `backend/testing/tool_lookup/tool_index.py` — build/load in-memory index from agent messages
  - `backend/testing/tool_lookup/tool_query.py` — CLI to query by flags and return latest tool output
  - `backend/testing/tool_lookup/tool_store.jsonl` — optional persisted rows (one per tool output)
- Modified files: none (keep `vector_storage/` untouched for this phase)

### Data Model
- Canonical key: `"<tool_name>|ticker=<T>|statement_type=<S>|industry_level=<L>|..."`
  - Normalize: `ticker` uppercase; `statement_type` in {income_statement, balance_sheet, cash_flow}; `industry_level` exact strings
- Row fields per output:
  - `tool_name` (str)
  - `tool_call_id` (str)
  - `args` (dict, raw)
  - `norm` (dict: ticker, statement_type, industry_level, etc.)
  - `timestamp` (from enclosing message block if available; else file order)
  - `text` (raw tool output)

### Build Flow
1. Read `agent_messages.json` and iterate `messages` in order.
2. On assistant with `tool_calls`: parse `[{id,name,args}]`.
3. On subsequent `tool` message: extract `tool_call_id`, map to prior assistant call.
4. Normalize args → `norm` (ticker uppercase; statement aliases → canonical).
5. Compose key from `tool_name + sorted(norm items)`.
6. Append row to in-memory list and optionally write to `tool_store.jsonl`.
7. Build index: `key -> list of rows (sorted by timestamp desc)` and `latest_index[key] -> row`.

### Query Flow (deterministic only)
- Input (flags): `--tool <name> --ticker <T> --statement_type <S> [--industry_level <L>]`
- Normalize flags → build canonical key.
- Lookup `latest_index[key]` → return `text`.
- If partial flags: filter rows by provided norm fields, return latest.
- If no match: return “not found” (no vector fallback in this phase).

### API/CLI
- `tool_query.py`:
  - `python -m backend.testing.tool_lookup.tool_query --tool get_ticker_fundamental_data --ticker BJ --statement_type income_statement`
  - Prints only tool output (`text`).
- `tool_index.py`:
  - `build_tool_index(agent_messages_path) -> (rows, latest_index)`
  - Helpers: `normalize_args(args)`, `canonical_key(tool, norm)`

### Testing
- Unit: parse assistant tool_calls; link to tool; normalize args mapping; key composition.
- E2E: exact key (BJ income_statement) returns expected tool output; partial (ticker only) returns latest for that ticker; not found returns properly.

### Acceptance Criteria
- Deterministic queries by exact key return the latest correct tool output in O(1).
- Partial queries filter correctly and return latest.
- No assistant tool_call blocks are surfaced in deterministic results.
- No vector search dependency in this phase.

### Rollout
- Phase 1 (this task): implement `tool_index.py`, `tool_query.py`, optional `tool_store.jsonl` export in `backend/testing/tool_lookup/`.
- Phase 2 (future): optional integrations or UI hooks; optional vector fallback (out of scope now).

### Risks / Mitigations
- Missing `tool_call_id`: fall back to nearest tool after assistant; mark confidence (log only).
- Argument aliases: maintain small alias map; extendable.
- Large outputs: store raw text; CLI may paginate or truncate view only (full text preserved).
