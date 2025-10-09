# Frontend Plan: Optimizer Run (start → stream → complete)

## API Contract (what the FE consumes)

- POST `http://localhost:8000/api/agents/optimizer/runs` → `{ run_id: string }`
- WS `ws://localhost:8000/api/ws/agents/{run_id}` emits messages:
  - `{"type":"evidence","arguments":"{...json...}"}` → `arguments` is a JSON string
  - `{"type":"task_state","arguments":"{...json...}"}` → JSON string of `{ tasks: Array<{id, description, status, subtasks[]}> }`
  - `{"type":"completed","payload": {...} }`
  - `{"type":"error","error": "..." }`
- GET `http://localhost:8000/api/agents/optimizer/runs/{run_id}/result` → `{ payload: {...} }` (404 until ready; cached 24h)

Code that signals completion and caching:

```24:31:/Users/michaellaret/Desktop/ProphitAI/app/services/agent_runs.py
        result = await asyncio.to_thread(agent.run)
        serializable_result = json.loads(json.dumps(result, default=str))

        await ws_manager.send(run_id, {"type": "completed", "payload": serializable_result})
        await cache.set(cache_key, serializable_result, ttl=RESULT_CACHE_TTL)
```

## Frontend Architecture (suggested, minimal)

- `lib/api.ts`: small REST helpers (create run, get result)
- `lib/ws.ts`: WebSocket connect util with auto-retry
- `hooks/useOptimizerRun.ts`: orchestrates lifecycle (create → ws → complete → cache)
- `pages/Optimizer.tsx`: page container with UI state machine
- `components/`:
  - `OptimizeButton.tsx`
  - `EvidenceStream.tsx` (renders incremental evidence)
  - `TaskProgress.tsx` (renders structured plan state)
  - `FinalResult.tsx` (renders payload)

## State Machine (client)

- `idle` → click Optimize → `starting`
- `starting` → POST gets `run_id` → `streaming`
- `streaming` → render `evidence` + `task_state` until `completed`
- `completed` → show final `payload`; optionally close WS; allow re-open to re-run
- `error` → show message; allow retry
- Refresh/Deep-link: if URL has `?run=<id>`, skip POST; connect WS and/or GET

## Types (keep explicit)

```ts
export type EvidenceMsg = { type: 'evidence'; arguments: string }; // parse JSON
export type TaskStateMsg = { type: 'task_state'; arguments: string }; // parse JSON
export type CompletedMsg = { type: 'completed'; payload: unknown };
export type ErrorMsg = { type: 'error'; error: string };
export type AgentMsg = EvidenceMsg | TaskStateMsg | CompletedMsg | ErrorMsg;
```

## Implementation Steps

1) API base config

- `API_BASE=http://localhost:8000` (dev)
- Build `api.ts`:
```ts
export async function createRun() { const r = await fetch(`${API_BASE}/api/agents/optimizer/runs`, { method: 'POST' }); return r.json(); }
export async function getResult(runId: string) { const r = await fetch(`${API_BASE}/api/agents/optimizer/runs/${runId}/result`); if (!r.ok) throw new Error('not-ready'); return r.json(); }
```


2) WebSocket utility

- Build `connectAgentWS(runId, onMessage)` that:
  - opens `new WebSocket(`${WS_BASE}/api/ws/agents/${runId}`)`
  - parses `evt.data` to `AgentMsg`
  - handles `close` with backoff if not `completed`

3) Orchestrating hook `useOptimizerRun`

- Exposes `{ state, runId, start, stop, evidence[], taskState, result, error }`
- `start`: POST → set `runId` → open WS; push `evidence` and `taskState` as they arrive
- On `completed`: set `result`, set state to `completed`, close WS
- On error: set `error`, state `error`
- Fallback polling: if WS closes unexpectedly and `state !== completed`, try GET (if 200 → complete; else retry WS)
- Persist `runId` in URL `?run=` so refreshs can resume

4) Page and UI

- `Optimizer.tsx`:
  - `OptimizeButton` disabled when `starting|streaming`
  - `EvidenceStream` renders incremental items
  - `TaskProgress` renders parsed `task_state`
  - `FinalResult` shown when `completed`
  - Error banner on `error`

5) Edge cases

- POST fails → show toast; remain `idle`
- WS opens but no traffic yet → show spinner
- WS drops mid-run → show reconnecting; apply backoff; poll GET for completion
- `getResult` 404 → still running, keep streaming/reconnecting
- Page reload with `run` param → resume streaming, otherwise fetch `GET` to show final payload quickly

6) Styling/UX (minimal)

- Compact cards for Evidence and Task Progress
- Sticky footer with “Stop streaming” and “Start new run”
- Collapsible evidence list (cap length, virtualize if needed)

7) Environments

- Dev: `API_BASE=http://localhost:8000`, `WS_BASE=ws://localhost:8000`
- Prod: use `window.location.origin` and `ws(s)` based on protocol; ensure CORS aligns

8) Testing checklist

- Verify: POST returns `run_id`
- WS receives `evidence` and `task_state`
- Final `completed` message received; UI switches to completed
- GET returns payload for run_id after completion
- Refresh mid-run resumes; refresh post-run shows cached result quickly

## Minimal Example Snippets (for dev handoff)

- WebSocket message handling:
```ts
ws.onmessage = (e) => {
  const m = JSON.parse(e.data) as AgentMsg;
  if (m.type === 'evidence') handleEvidence(JSON.parse(m.arguments));
  if (m.type === 'task_state') handleTaskState(JSON.parse(m.arguments));
  if (m.type === 'completed') handleCompleted(m.payload);
  if (m.type === 'error') handleError(m.error);
};
```

- URL persistence helpers: add/remove `run` query param on start/finish

## Notes for FE Dev

- `arguments` fields are JSON strings; always `JSON.parse`
- Prefer the WS `completed` message to know “done”; GET is a fallback
- Result TTL is 24h; after that GET will 404
- No cancel endpoint at present; provide a UI stop that just closes WS