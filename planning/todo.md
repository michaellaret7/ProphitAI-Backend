## Task: Add simple episodic memory to agent (CIO flow first)

### Objectives
- Provide a minimal, append-focused episodic memory the agent can write to and read from during runs.
- Reset episodic memory to blank on agent initialization each session.
- Automatically store portfolio V1/V2/V3 submissions and key analytics snapshots (performance, VaR) for the CIO process.
- Expose simple tools so the agent can remember and recall arbitrary events it deems useful.

### File type (answer)
- Start with JSON (array of objects) for simplicity and readability. It’s sufficient at current scale and avoids extra dependencies.
- Note: If writes become frequent or the file grows large, switch to JSONL (one JSON object per line) to enable safe append semantics without full-file rewrites. For heavy semantic retrieval later, consider a vector DB.

### Design (minimal)
- Location: reuse `backend/src/agentic_framework/base_agent/memory/memory_store/episodic_memory.json` (blanked at startup).
- Add `EpisodicMemory` in `backend/src/agentic_framework/base_agent/memory/episodic_memory.py`:
  - Data shape per entry: `{ timestamp, title, event, context, outcome, tags, meta }` (require `timestamp`, `title`, `event`).
  - API:
    - `reset()` → create/overwrite file with `[]`.
    - `append(title: str, event: str, context: dict = None, outcome: dict|str = None, tags: list[str] = None, meta: dict = None)`.
    - `recall(query: str = None, tags: list[str] = None, since: str = None, limit: int = 20)` → naive keyword/tag/time filter.
    - `get_latest(tag_or_event: str)` → convenience for most recent matching entry.
    - `summarize_older(cutoff_n: int = 300)` (simple heuristic summarization for oldest entries beyond cutoff).

### Integration points
- `BaseAgent.__init__`:
  - Instantiate `self.episodic = EpisodicMemory(path=episodic_path, reset_on_init=True)`.
  - Register two optional base tools:
    - `episodic_remember(title, event, context?, outcome?, tags?, meta?)` → calls `append()`.
    - `episodic_recall(query?, tags?, since?, limit?)` → calls `recall()`.
- Event wiring (no invasive changes):
  - In existing event handler for tool executions, detect key CIO milestones and persist:
    - When `add_task_evidence` contains "Portfolio V1 dictionary output" → remember `{event: "portfolio_version_published", context: {version:"v1", dict}, tags:["cio","portfolio"]}`.
    - Similarly for V2/V3 messages.
    - After `calculate_portfolio_past_performance` → remember performance snapshot `{event:"performance_metrics"}`.
    - After `VaR_calculator` (portfolio / industry) → remember VaR snapshot `{event:"var_snapshot"}`.
- Retrieval usage during CIO flow:
  - Before constructing V2, load latest V1 entry via `get_latest("portfolio_version_published")`.
  - Before constructing V3, load latest V2 entry.
  - Agent may also call `episodic_recall` by keywords (e.g., "beta", "Sharpe") if needed.

### Non-goals (keep simple)
- No cross-run persistence beyond a session (we reset at init as requested).
- No embeddings/vector DB in this phase.
- No encryption or ACLs in this phase (add later if needed).

### TODO
1) Implement `EpisodicMemory` class in `memory/episodic_memory.py` with methods: `reset`, `append(title, event, ...)`, `recall`, `get_latest`, `summarize_older`.
2) Wire into `BaseAgent.__init__`: construct `self.episodic` with `reset_on_init=True` and keep path under `memory_store/episodic_memory.json`.
3) Add optional tools `episodic_remember` and `episodic_recall` to base tool registry (simple JSON schemas).
4) Extend tool execution handler to auto-log CIO milestones (Portfolio V1/V2/V3 outputs, performance, VaR) using `self.episodic.append(...)`.
5) In CIO flow, before building V2/V3, query `self.episodic.get_latest("portfolio_version_published")` to retrieve last submission for context.
6) Smoke-test locally by running CIO flow end-to-end; verify entries appear and can be recalled.

### Review (after implementation)
- Summarize edits to `episodic_memory.py`, `base_agent/agent.py` (init + event hook + tool registry), and any CIO-specific glue.
- Confirm: memory resets on init, V1/V2/V3 and analytics snapshots are recorded, recall works, and no unrelated behavior changed.
