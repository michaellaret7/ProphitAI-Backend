# Optimization Streaming + Final Payload

### Approach

- Use existing WebSocket (`/api/ws/agents/{run_id}`) to stream progress.
- When the agent finishes, send one final WebSocket message `{ type: "completed", payload: <result> }` with the full result from `BaseAgent.run()`.
- Persist the same final result in Redis for reliability, and expose `GET /api/agents/optimizer/runs/{run_id}/result` so the frontend can fetch if the socket drops.

### Message Contract (WebSocket)

- Progress events (already in place):
- `{"type":"evidence","arguments":"..."}`
- `{"type":"task_state","arguments":"{...}"}`
- Final event (new):
- `{"type":"completed","payload": { "final_text": "...", "plan_execution": { ... }, "trace": [ ... ], "iterations": N, "stopped_reason": "...", "total_tokens": N }}`

### Persistence (Redis)

- Key: `agents:optimizer:{run_id}:result`
- TTL: 86400 seconds (24h)

### API Changes (Backend)

- Edit `app/services/agent_runs.py` to capture the agent result and broadcast/persist it:
- After `result = await asyncio.to_thread(agent.run)`:
- `await ws_manager.send(run_id, {"type":"completed","payload": result})`
- `await cache.set(f"agents:optimizer:{run_id}:result", result, ttl=86400)`
- Extend `app/api/routes/agent_runs_router.py`:
- Add `GET /agents/optimizer/runs/{run_id}/result` → returns cached result or 404/processing.
- Include the router in `main.py` if not already: `app.include_router(agent_runs_router, prefix="/api")`.

### Endpoint Shapes

- POST `/api/agents/optimizer/runs` → `{ "run_id": "<uuid>" }`
- GET `/api/agents/optimizer/runs/{run_id}/result` → standard envelope with `payload: <result>` if present.

### Frontend Flow (minimal example)

1) `POST /api/agents/optimizer/runs` → get `run_id`.
2) Open WS to `/api/ws/agents/{run_id}`.
3) Switch on `type`: render `evidence` and `task_state`; on `completed`, render final payload and close WS.
4) If WS drops, poll `GET /api/agents/optimizer/runs/{run_id}/result`.

### Notes

- Keeps business logic in the app layer and avoids API versioning, as preferred.
- No schema changes required; final payload mirrors `BaseAgent.run()` output.