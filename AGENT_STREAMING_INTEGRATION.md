# Agent Streaming Integration Guide

## Overview

This document describes the new real-time agent streaming feature that allows the frontend to display live progress updates while an AI agent (e.g., Portfolio Optimizer) is executing, and then display the final results when complete.

### Architecture Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React/TypeScript)                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   1. User clicks "Optimize Portfolio"                                    │
│              │                                                           │
│              ▼                                                           │
│   2. POST /api/agents/execute ──────────────────┐                       │
│              │                                   │                       │
│              ▼                                   ▼                       │
│   3. Receive execution_id              Backend starts agent             │
│              │                          in background                    │
│              ▼                                   │                       │
│   4. Connect WebSocket                          │                       │
│      /ws/agent/{execution_id}                   │                       │
│              │                                   │                       │
│              ▼                                   │                       │
│   5. Receive streaming updates ◄────────────────┘                       │
│      • plan_created (task list)                                         │
│      • task_update (progress)                                           │
│      • complete (final result)                                          │
│              │                                                           │
│              ▼                                                           │
│   6. Display optimized portfolio                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## API Reference

### 1. Start Agent Execution

**Endpoint:** `POST /api/agents/execute`

**Headers:**
```typescript
{
  "Content-Type": "application/json",
  "X-API-Key": "<your-api-key>"
}
```

**Request Body:**
```typescript
interface ExecuteAgentRequest {
  agent_type: "optimizer";  // Currently only optimizer is available
  parameters: {
    portfolio_id: string;           // Required - UUID of portfolio to optimize
    risk_tolerance?: string;        // Optional - "low" | "moderate" | "high"
    time_horizon?: string;          // Optional - "short-term" | "medium-term" | "long-term"
    investment_goals?: string;      // Optional - e.g., "growth, income, capital preservation"
    sectors_to_exclude?: string;    // Optional - e.g., "technology, energy"
    sectors_to_include?: string;    // Optional - e.g., "financials, healthcare"
    tickers_to_keep?: string;       // Optional - e.g., "AAPL, MSFT, GOOGL"
    tickers_to_exclude?: string;    // Optional - e.g., "TSLA, NVDA"
  };
}
```

**Response (200 OK):**
```typescript
interface ExecuteAgentResponse {
  execution_id: string;  // UUID to track this execution
  message: string;       // "Agent execution started for optimizer"
}
```

**Example:**
```typescript
const response = await fetch("/api/agents/execute", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
  },
  body: JSON.stringify({
    agent_type: "optimizer",
    parameters: {
      portfolio_id: "26da638b-5602-4e07-aeba-08dc1052bd86",
      risk_tolerance: "moderate",
      time_horizon: "long-term",
      investment_goals: "growth, income",
      sectors_to_include: "financials, healthcare",
      tickers_to_keep: "AAPL, MSFT, GOOGL, AMZN, META",
      tickers_to_exclude: "TSLA, NVDA",
    },
  }),
});

const { execution_id } = await response.json();
// execution_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

---

### 2. WebSocket Connection

**Endpoint:** `ws://<host>/ws/agent/{execution_id}`

> **Note:** The WebSocket endpoint does NOT require API key authentication in the URL. Authentication is handled by the initial POST request.

**Connection Example:**
```typescript
const ws = new WebSocket(`ws://localhost:8000/ws/agent/${execution_id}`);
```

---

## WebSocket Message Types

All WebSocket messages follow this structure:

```typescript
interface WebSocketMessage<T = unknown> {
  type: "plan_created" | "task_update" | "complete";
  payload: T;
  timestamp: string;  // ISO 8601 format
}
```

### Message Type 1: `plan_created`

Sent once after the agent creates its execution plan (usually within the first 10-30 seconds).

```typescript
interface PlanCreatedPayload {
  tasks: Array<{
    id: string;           // e.g., "1", "2", "3"
    description: string;  // e.g., "Analyze current portfolio composition and risk metrics"
    status: "not_started" | "in_progress" | "complete";
    subtasks: Array<{
      id: string;         // e.g., "1a", "1b", "1c"
      description: string;
      status: "not_started" | "in_progress" | "complete";
    }>;
  }>;
}
```

**Example Message:**
```json
{
  "type": "plan_created",
  "payload": {
    "tasks": [
      {
        "id": "1",
        "description": "Analyze current portfolio composition and risk metrics",
        "status": "not_started",
        "subtasks": [
          {
            "id": "1a",
            "description": "Fetch current portfolio holdings and weights",
            "status": "not_started"
          },
          {
            "id": "1b",
            "description": "Calculate portfolio risk metrics (Sharpe, volatility, beta)",
            "status": "not_started"
          }
        ]
      },
      {
        "id": "2",
        "description": "Research sector opportunities based on constraints",
        "status": "not_started",
        "subtasks": [
          {
            "id": "2a",
            "description": "Analyze Financials sector performance and valuations",
            "status": "not_started"
          }
        ]
      }
    ]
  },
  "timestamp": "2025-12-04T06:30:15.123456"
}
```

---

### Message Type 2: `task_update`

Sent whenever a task or subtask status changes. You'll receive many of these during execution.

```typescript
interface TaskUpdatePayload {
  task_id: string;           // e.g., "1", "2"
  subtask_id: string | null; // e.g., "1a" or null for main task updates
  status: "not_started" | "in_progress" | "complete";
}
```

**Example Messages:**
```json
// Subtask starting
{
  "type": "task_update",
  "payload": {
    "task_id": "1",
    "subtask_id": "1a",
    "status": "in_progress"
  },
  "timestamp": "2025-12-04T06:30:45.123456"
}

// Main task auto-updated to in_progress (when first subtask starts)
{
  "type": "task_update",
  "payload": {
    "task_id": "1",
    "subtask_id": null,
    "status": "in_progress"
  },
  "timestamp": "2025-12-04T06:30:45.234567"
}

// Subtask completed
{
  "type": "task_update",
  "payload": {
    "task_id": "1",
    "subtask_id": "1a",
    "status": "complete"
  },
  "timestamp": "2025-12-04T06:31:12.123456"
}

// Main task auto-completed (when all subtasks complete)
{
  "type": "task_update",
  "payload": {
    "task_id": "1",
    "subtask_id": null,
    "status": "complete"
  },
  "timestamp": "2025-12-04T06:32:00.123456"
}
```

---

### Message Type 3: `complete`

Sent once when the agent finishes execution. **This message contains the final portfolio result.**

```typescript
interface CompletePayload {
  execution_id: string;
  result: OptimizedPortfolioResult;
  iterations: number;  // How many LLM iterations the agent used
  tokens: number;      // Total tokens consumed
}
```

**Example Message:**
```json
{
  "type": "complete",
  "payload": {
    "execution_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "result": {
      "portfolio": {
        "AAPL": {
          "allocation": 0.066,
          "position": "long",
          "thesis": "Required tech holding. Hardware leader with steady ecosystem strength..."
        },
        "MSFT": {
          "allocation": 0.066,
          "position": "long",
          "thesis": "Required tech holding. Azure AI Services monetization leader..."
        },
        "JPM": {
          "allocation": 0.12,
          "position": "long",
          "thesis": "Mega-cap diversified bank with strongest capital position..."
        }
      },
      "changes": {
        "added": {
          "JPM": "Mega-cap diversified bank with strongest capital position, 46% P/E discount...",
          "CI": "Cigna Group managed care value opportunity with 85.5% forward EPS growth..."
        },
        "removed": {
          "QQQ": "Nasdaq 100 ETF violates technology sector exclusion constraint...",
          "TSLA": "Banned ticker per constraints. Automobile manufacturer creates volatility..."
        },
        "adjusted": {
          "AAPL": "Reduced from 8.05% to 6.6% to equalize required tech holdings...",
          "META": "Increased from 5.66% to 6.6% to equalize required tech holdings..."
        }
      },
      "metrics_delta": {
        "sharpe": "1.47 → 1.75 (+18.9% improvement)",
        "volatility": "22.51% → 16.77% (-25.5% reduction)",
        "max_drawdown": "-24.89% → -18.46% (+26.0% reduction)",
        "sortino": "2.23 → 2.624 (+17.6% improvement)",
        "beta": "~1.2+ (implied) → 0.9489 (defensive positioning)",
        "notes": "Optimized portfolio achieves primary objective..."
      }
    },
    "iterations": 42,
    "tokens": 125000
  },
  "timestamp": "2025-12-04T06:45:30.123456"
}
```

---

## TypeScript Types

Here are the complete TypeScript interfaces you should use:

```typescript
// ============================================
// API Types
// ============================================

type AgentType = "optimizer";

interface ExecuteAgentRequest {
  agent_type: AgentType;
  parameters: OptimizerParameters;
}

interface OptimizerParameters {
  portfolio_id: string;
  risk_tolerance?: string;
  time_horizon?: string;
  investment_goals?: string;
  sectors_to_exclude?: string;
  sectors_to_include?: string;
  tickers_to_keep?: string;
  tickers_to_exclude?: string;
}

interface ExecuteAgentResponse {
  execution_id: string;
  message: string;
}

// ============================================
// WebSocket Message Types
// ============================================

type TaskStatus = "not_started" | "in_progress" | "complete";

interface Subtask {
  id: string;
  description: string;
  status: TaskStatus;
}

interface Task {
  id: string;
  description: string;
  status: TaskStatus;
  subtasks: Subtask[];
}

interface PlanCreatedPayload {
  tasks: Task[];
}

interface TaskUpdatePayload {
  task_id: string;
  subtask_id: string | null;
  status: TaskStatus;
}

interface CompletePayload {
  execution_id: string;
  result: OptimizedPortfolioResult | null;
  iterations: number;
  tokens: number;
  error?: string;  // Present if agent failed
}

type WebSocketPayload = PlanCreatedPayload | TaskUpdatePayload | CompletePayload;

interface WebSocketMessage<T extends WebSocketPayload = WebSocketPayload> {
  type: "plan_created" | "task_update" | "complete";
  payload: T;
  timestamp: string;
}

// ============================================
// Portfolio Result Types
// ============================================

type PositionType = "long" | "short";

interface PortfolioPosition {
  allocation: number;  // 0.0 to 1.0 (e.g., 0.066 = 6.6%)
  position: PositionType;
  thesis: string;
}

interface PortfolioChanges {
  added: Record<string, string>;     // ticker -> reason
  removed: Record<string, string>;   // ticker -> reason
  adjusted: Record<string, string>;  // ticker -> description
}

interface MetricsDelta {
  sharpe: string;
  volatility: string;
  max_drawdown: string;
  sortino: string;
  beta: string;
  down_capture?: string;
  up_capture?: string;
  notes: string;
}

interface OptimizedPortfolioResult {
  portfolio: Record<string, PortfolioPosition>;  // ticker -> position
  changes: PortfolioChanges;
  metrics_delta?: MetricsDelta;
}
```

---

## React Implementation

### Step 1: Create a Custom Hook

```typescript
// hooks/useAgentStreaming.ts

import { useState, useEffect, useCallback, useRef } from "react";

type TaskStatus = "not_started" | "in_progress" | "complete";

interface Task {
  id: string;
  description: string;
  status: TaskStatus;
  subtasks: Array<{
    id: string;
    description: string;
    status: TaskStatus;
  }>;
}

interface OptimizedPortfolioResult {
  portfolio: Record<string, {
    allocation: number;
    position: "long" | "short";
    thesis: string;
  }>;
  changes: {
    added: Record<string, string>;
    removed: Record<string, string>;
    adjusted: Record<string, string>;
  };
  metrics_delta?: Record<string, string>;
}

interface UseAgentStreamingOptions {
  apiKey: string;
  baseUrl?: string;
  wsUrl?: string;
}

interface AgentStreamingState {
  status: "idle" | "starting" | "running" | "complete" | "error";
  executionId: string | null;
  tasks: Task[];
  result: OptimizedPortfolioResult | null;
  error: string | null;
  iterations: number;
  tokens: number;
}

export function useAgentStreaming(options: UseAgentStreamingOptions) {
  const { apiKey, baseUrl = "", wsUrl = "" } = options;

  const [state, setState] = useState<AgentStreamingState>({
    status: "idle",
    executionId: null,
    tasks: [],
    result: null,
    error: null,
    iterations: 0,
    tokens: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);

  // Clean up WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Update task status in local state
  const updateTaskStatus = useCallback(
    (taskId: string, subtaskId: string | null, status: TaskStatus) => {
      setState((prev) => ({
        ...prev,
        tasks: prev.tasks.map((task) => {
          if (task.id !== taskId) return task;

          if (subtaskId === null) {
            // Update main task
            return { ...task, status };
          } else {
            // Update subtask
            return {
              ...task,
              subtasks: task.subtasks.map((st) =>
                st.id === subtaskId ? { ...st, status } : st
              ),
            };
          }
        }),
      }));
    },
    []
  );

  // Connect to WebSocket and handle messages
  const connectWebSocket = useCallback(
    (executionId: string) => {
      const wsEndpoint = wsUrl || window.location.origin.replace("http", "ws");
      const ws = new WebSocket(`${wsEndpoint}/ws/agent/${executionId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[WebSocket] Connected");
        setState((prev) => ({ ...prev, status: "running" }));
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log("[WebSocket] Message:", message.type);

        switch (message.type) {
          case "plan_created":
            setState((prev) => ({
              ...prev,
              tasks: message.payload.tasks,
            }));
            break;

          case "task_update":
            updateTaskStatus(
              message.payload.task_id,
              message.payload.subtask_id,
              message.payload.status
            );
            break;

          case "complete":
            setState((prev) => ({
              ...prev,
              status: message.payload.error ? "error" : "complete",
              result: message.payload.result,
              error: message.payload.error || null,
              iterations: message.payload.iterations,
              tokens: message.payload.tokens,
            }));
            ws.close();
            break;
        }
      };

      ws.onerror = (error) => {
        console.error("[WebSocket] Error:", error);
      };

      ws.onclose = (event) => {
        console.log("[WebSocket] Closed:", event.code, event.reason);
      };
    },
    [wsUrl, updateTaskStatus]
  );

  // Start agent execution
  const startAgent = useCallback(
    async (parameters: Record<string, unknown>) => {
      setState({
        status: "starting",
        executionId: null,
        tasks: [],
        result: null,
        error: null,
        iterations: 0,
        tokens: 0,
      });

      try {
        const response = await fetch(`${baseUrl}/api/agents/execute`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": apiKey,
          },
          body: JSON.stringify({
            agent_type: "optimizer",
            parameters,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Failed to start agent");
        }

        const { execution_id } = await response.json();

        setState((prev) => ({ ...prev, executionId: execution_id }));
        connectWebSocket(execution_id);
      } catch (error) {
        setState((prev) => ({
          ...prev,
          status: "error",
          error: error instanceof Error ? error.message : "Unknown error",
        }));
      }
    },
    [apiKey, baseUrl, connectWebSocket]
  );

  // Reset state
  const reset = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    setState({
      status: "idle",
      executionId: null,
      tasks: [],
      result: null,
      error: null,
      iterations: 0,
      tokens: 0,
    });
  }, []);

  return {
    ...state,
    startAgent,
    reset,
  };
}
```

---

### Step 2: Create Progress Display Component

```typescript
// components/AgentProgress.tsx

import React from "react";

type TaskStatus = "not_started" | "in_progress" | "complete";

interface Subtask {
  id: string;
  description: string;
  status: TaskStatus;
}

interface Task {
  id: string;
  description: string;
  status: TaskStatus;
  subtasks: Subtask[];
}

interface AgentProgressProps {
  tasks: Task[];
}

const StatusIcon: React.FC<{ status: TaskStatus }> = ({ status }) => {
  switch (status) {
    case "not_started":
      return <span className="text-gray-400">○</span>;
    case "in_progress":
      return <span className="text-blue-500 animate-pulse">◉</span>;
    case "complete":
      return <span className="text-green-500">✓</span>;
  }
};

const StatusBadge: React.FC<{ status: TaskStatus }> = ({ status }) => {
  const styles: Record<TaskStatus, string> = {
    not_started: "bg-gray-100 text-gray-600",
    in_progress: "bg-blue-100 text-blue-700",
    complete: "bg-green-100 text-green-700",
  };

  const labels: Record<TaskStatus, string> = {
    not_started: "Pending",
    in_progress: "In Progress",
    complete: "Complete",
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  );
};

export const AgentProgress: React.FC<AgentProgressProps> = ({ tasks }) => {
  const completedTasks = tasks.filter((t) => t.status === "complete").length;
  const totalTasks = tasks.length;
  const progressPercent = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;

  return (
    <div className="space-y-4">
      {/* Overall Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>Overall Progress</span>
          <span>{completedTasks} / {totalTasks} tasks</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-500 h-2 rounded-full transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Task List */}
      <div className="space-y-3">
        {tasks.map((task) => (
          <div
            key={task.id}
            className="border rounded-lg p-4 bg-white shadow-sm"
          >
            {/* Task Header */}
            <div className="flex items-start gap-3">
              <StatusIcon status={task.status} />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium text-gray-900">
                    Task {task.id}: {task.description}
                  </h4>
                  <StatusBadge status={task.status} />
                </div>

                {/* Subtasks */}
                {task.subtasks.length > 0 && (
                  <div className="mt-3 ml-4 space-y-2">
                    {task.subtasks.map((subtask) => (
                      <div
                        key={subtask.id}
                        className="flex items-center gap-2 text-sm text-gray-600"
                      >
                        <StatusIcon status={subtask.status} />
                        <span className={subtask.status === "complete" ? "line-through opacity-60" : ""}>
                          {subtask.id}: {subtask.description}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

### Step 3: Create Portfolio Result Display Component

```typescript
// components/PortfolioResult.tsx

import React from "react";

interface PortfolioPosition {
  allocation: number;
  position: "long" | "short";
  thesis: string;
}

interface PortfolioChanges {
  added: Record<string, string>;
  removed: Record<string, string>;
  adjusted: Record<string, string>;
}

interface OptimizedPortfolioResult {
  portfolio: Record<string, PortfolioPosition>;
  changes: PortfolioChanges;
  metrics_delta?: Record<string, string>;
}

interface PortfolioResultProps {
  result: OptimizedPortfolioResult;
  iterations: number;
  tokens: number;
}

export const PortfolioResult: React.FC<PortfolioResultProps> = ({
  result,
  iterations,
  tokens,
}) => {
  const { portfolio, changes, metrics_delta } = result;

  // Sort portfolio by allocation (descending)
  const sortedPositions = Object.entries(portfolio).sort(
    ([, a], [, b]) => b.allocation - a.allocation
  );

  return (
    <div className="space-y-8">
      {/* Header Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-blue-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-blue-700">
            {Object.keys(portfolio).length}
          </div>
          <div className="text-sm text-blue-600">Positions</div>
        </div>
        <div className="bg-green-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-green-700">{iterations}</div>
          <div className="text-sm text-green-600">Iterations</div>
        </div>
        <div className="bg-purple-50 p-4 rounded-lg">
          <div className="text-2xl font-bold text-purple-700">
            {(tokens / 1000).toFixed(1)}k
          </div>
          <div className="text-sm text-purple-600">Tokens Used</div>
        </div>
      </div>

      {/* Metrics Improvements */}
      {metrics_delta && (
        <div className="bg-gradient-to-r from-green-50 to-blue-50 p-6 rounded-lg">
          <h3 className="text-lg font-semibold mb-4">Performance Improvements</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {Object.entries(metrics_delta)
              .filter(([key]) => key !== "notes")
              .map(([key, value]) => (
                <div key={key} className="text-sm">
                  <div className="text-gray-500 capitalize">
                    {key.replace(/_/g, " ")}
                  </div>
                  <div className="font-medium">{value}</div>
                </div>
              ))}
          </div>
          {metrics_delta.notes && (
            <p className="mt-4 text-sm text-gray-600 italic">
              {metrics_delta.notes}
            </p>
          )}
        </div>
      )}

      {/* Portfolio Holdings */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Optimized Portfolio</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-4">Ticker</th>
                <th className="text-right py-2 px-4">Allocation</th>
                <th className="text-center py-2 px-4">Position</th>
                <th className="text-left py-2 px-4">Thesis</th>
              </tr>
            </thead>
            <tbody>
              {sortedPositions.map(([ticker, position]) => (
                <tr key={ticker} className="border-b hover:bg-gray-50">
                  <td className="py-3 px-4 font-mono font-medium">{ticker}</td>
                  <td className="py-3 px-4 text-right">
                    {(position.allocation * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        position.position === "long"
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      {position.position.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-600 max-w-md">
                    {position.thesis.length > 150
                      ? `${position.thesis.slice(0, 150)}...`
                      : position.thesis}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Changes Section */}
      <div className="grid md:grid-cols-3 gap-6">
        {/* Added */}
        <div>
          <h4 className="font-semibold text-green-700 mb-3 flex items-center gap-2">
            <span className="text-lg">+</span> Added
          </h4>
          <div className="space-y-2">
            {Object.entries(changes.added).map(([ticker, reason]) => (
              <div key={ticker} className="bg-green-50 p-3 rounded">
                <div className="font-mono font-medium text-green-800">
                  {ticker}
                </div>
                <div className="text-sm text-green-700 mt-1">{reason}</div>
              </div>
            ))}
            {Object.keys(changes.added).length === 0 && (
              <div className="text-gray-400 text-sm">No positions added</div>
            )}
          </div>
        </div>

        {/* Removed */}
        <div>
          <h4 className="font-semibold text-red-700 mb-3 flex items-center gap-2">
            <span className="text-lg">−</span> Removed
          </h4>
          <div className="space-y-2">
            {Object.entries(changes.removed).map(([ticker, reason]) => (
              <div key={ticker} className="bg-red-50 p-3 rounded">
                <div className="font-mono font-medium text-red-800">
                  {ticker}
                </div>
                <div className="text-sm text-red-700 mt-1">{reason}</div>
              </div>
            ))}
            {Object.keys(changes.removed).length === 0 && (
              <div className="text-gray-400 text-sm">No positions removed</div>
            )}
          </div>
        </div>

        {/* Adjusted */}
        <div>
          <h4 className="font-semibold text-yellow-700 mb-3 flex items-center gap-2">
            <span className="text-lg">↕</span> Adjusted
          </h4>
          <div className="space-y-2">
            {Object.entries(changes.adjusted).map(([ticker, description]) => (
              <div key={ticker} className="bg-yellow-50 p-3 rounded">
                <div className="font-mono font-medium text-yellow-800">
                  {ticker}
                </div>
                <div className="text-sm text-yellow-700 mt-1">{description}</div>
              </div>
            ))}
            {Object.keys(changes.adjusted).length === 0 && (
              <div className="text-gray-400 text-sm">No positions adjusted</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
```

---

### Step 4: Main Page Component

```typescript
// pages/PortfolioOptimizer.tsx

import React, { useState } from "react";
import { useAgentStreaming } from "../hooks/useAgentStreaming";
import { AgentProgress } from "../components/AgentProgress";
import { PortfolioResult } from "../components/PortfolioResult";

const API_KEY = process.env.REACT_APP_API_KEY || "";

export const PortfolioOptimizer: React.FC = () => {
  const {
    status,
    tasks,
    result,
    error,
    iterations,
    tokens,
    startAgent,
    reset,
  } = useAgentStreaming({ apiKey: API_KEY });

  const [portfolioId, setPortfolioId] = useState("");
  const [riskTolerance, setRiskTolerance] = useState("moderate");
  const [timeHorizon, setTimeHorizon] = useState("long-term");

  const handleOptimize = () => {
    if (!portfolioId) {
      alert("Please enter a portfolio ID");
      return;
    }

    startAgent({
      portfolio_id: portfolioId,
      risk_tolerance: riskTolerance,
      time_horizon: timeHorizon,
    });
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8">Portfolio Optimizer</h1>

      {/* Form - Only show when idle or error */}
      {(status === "idle" || status === "error") && (
        <div className="bg-white p-6 rounded-lg shadow mb-8">
          <div className="grid md:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Portfolio ID
              </label>
              <input
                type="text"
                value={portfolioId}
                onChange={(e) => setPortfolioId(e.target.value)}
                className="w-full border rounded px-3 py-2"
                placeholder="UUID of portfolio"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Risk Tolerance
              </label>
              <select
                value={riskTolerance}
                onChange={(e) => setRiskTolerance(e.target.value)}
                className="w-full border rounded px-3 py-2"
              >
                <option value="low">Low</option>
                <option value="moderate">Moderate</option>
                <option value="high">High</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Time Horizon
              </label>
              <select
                value={timeHorizon}
                onChange={(e) => setTimeHorizon(e.target.value)}
                className="w-full border rounded px-3 py-2"
              >
                <option value="short-term">Short Term</option>
                <option value="medium-term">Medium Term</option>
                <option value="long-term">Long Term</option>
              </select>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 text-red-700 p-3 rounded mb-4">
              Error: {error}
            </div>
          )}

          <button
            onClick={handleOptimize}
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
          >
            Optimize Portfolio
          </button>
        </div>
      )}

      {/* Loading State */}
      {status === "starting" && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Starting optimization agent...</p>
        </div>
      )}

      {/* Progress Display */}
      {status === "running" && (
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Optimization in Progress</h2>
            <div className="flex items-center gap-2">
              <div className="animate-pulse h-3 w-3 bg-blue-500 rounded-full" />
              <span className="text-sm text-gray-600">Agent working...</span>
            </div>
          </div>
          <AgentProgress tasks={tasks} />
        </div>
      )}

      {/* Results Display */}
      {status === "complete" && result && (
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-green-700">
              ✓ Optimization Complete
            </h2>
            <button
              onClick={reset}
              className="text-blue-600 hover:text-blue-800"
            >
              Start New Optimization
            </button>
          </div>
          <PortfolioResult
            result={result}
            iterations={iterations}
            tokens={tokens}
          />
        </div>
      )}
    </div>
  );
};
```

---

## Error Handling

### WebSocket Disconnection

If the WebSocket disconnects during execution, the agent **continues running** on the backend. The `complete` message with results will be stored. You can implement a fallback polling mechanism:

```typescript
// In your hook, add polling fallback
const pollForResult = async (executionId: string) => {
  const response = await fetch(`/api/agents/${executionId}/result`, {
    headers: { "X-API-Key": apiKey },
  });
  const data = await response.json();

  if (data.status === "complete") {
    setState(prev => ({
      ...prev,
      status: "complete",
      result: data.result,
      iterations: data.iterations,
      tokens: data.tokens,
    }));
  } else if (data.status === "error") {
    setState(prev => ({
      ...prev,
      status: "error",
      error: data.error,
    }));
  } else {
    // Still running, poll again
    setTimeout(() => pollForResult(executionId), 5000);
  }
};
```

### API Error Codes

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad request - missing/invalid parameters (e.g., invalid portfolio_id) |
| 401 | Unauthorized - invalid or missing API key |
| 404 | Not found - execution_id doesn't exist |
| 500 | Server error - agent creation or execution failed |

---

## Timeline Expectations

| Phase | Duration | What Happens |
|-------|----------|--------------|
| Start → Plan | 10-30 sec | Agent analyzes request, creates task plan |
| Plan → Completion | 5-15 min | Agent executes tasks, calls various tools |
| Total | 5-20 min | Depends on portfolio complexity and constraints |

---

## Testing

Use this test portfolio ID for development:
```
26da638b-5602-4e07-aeba-08dc1052bd86
```

---

## Questions?

Contact the backend team if you have questions about:
- WebSocket message format changes
- New agent types being added
- Rate limiting or authentication
- Result data structure changes
