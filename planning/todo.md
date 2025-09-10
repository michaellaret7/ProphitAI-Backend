## Task: Convert CIO agent to use CIO prompts (no semantic memory)

### Goal
Update `backend/src/prophit_alts/consumer_staples_fund/build_portfolio/cio/agent.py` to define a CIO agent that:
- Uses `cio_system_prompt` and `cio_user_prompt` from `prompts/cio_agent_prompts.py`.
- Registers CIO tools via `register_cio_tools(self)`.
- Does not use semantic memory for now.

### TODO
- [ ] Create `CIOAgent` class using `cio_system_prompt` and `cio_user_prompt`.
- [ ] Replace industry-specific imports; call `register_cio_tools(self)`.
- [ ] Disable semantic memory by overriding `_initialize_semantic_memory` as a no-op.
- [ ] Keep `run()` minimal: strip `"Final Answer:"` if present and return the JSON array as-is.

### Review (to be completed after implementation)
- High-level summary of edits and any behavior changes.
