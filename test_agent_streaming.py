"""Test script for agent streaming functionality.

Run with: python test_agent_streaming.py

Prerequisites:
1. Start the server: uvicorn main:app --reload
2. Ensure you have a valid API key in your .env
3. Ensure you have a valid portfolio_id to test with
"""

import asyncio
import httpx
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"
API_KEY = os.getenv("PROPHIT_API_KEY", "KAuviO3i_vrojBmeQ5CxLzplk4Ps71wmFWftAkLsiTc")

# Replace with a valid portfolio ID from your database
TEST_PORTFOLIO_ID = "26da638b-5602-4e07-aeba-08dc1052bd86"


async def test_agent_streaming():
    """Test the full agent streaming flow."""

    print("=" * 60)
    print("Agent Streaming Test")
    print("=" * 60)

    # Step 1: Start the agent execution
    print("\n[1] Starting agent execution...")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/agents/execute",
            headers={"X-API-Key": API_KEY},
            json={
                "agent_type": "optimizer",
                "parameters": {
                    "portfolio_id": TEST_PORTFOLIO_ID,
                    "risk_tolerance": "moderate",
                    "time_horizon": "long-term",
                }
            }
        )

        if response.status_code != 200:
            print(f"Error starting agent: {response.status_code}")
            print(response.text)
            return

        data = response.json()
        execution_id = data["execution_id"]
        print(f"    Execution started: {execution_id}")

    # Step 2: Connect to WebSocket for streaming updates
    print("\n[2] Connecting to WebSocket for live updates...")

    ws_url = f"{WS_URL}/ws/agent/{execution_id}"

    async def listen_websocket():
        """Listen for WebSocket messages."""
        try:
            async with websockets.connect(ws_url) as ws:
                print(f"    Connected to {ws_url}")

                while True:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=300)
                        data = json.loads(message)

                        msg_type = data.get("type")
                        payload = data.get("payload", {})
                        timestamp = data.get("timestamp", "")

                        print(f"\n    [{timestamp}] {msg_type}:")

                        if msg_type == "plan_created":
                            tasks = payload.get("tasks", [])
                            print(f"        Plan created with {len(tasks)} tasks:")
                            for task in tasks:
                                print(f"          - [{task['id']}] {task['description'][:50]}...")
                                for st in task.get("subtasks", []):
                                    print(f"            - [{st['id']}] {st['description'][:40]}...")

                        elif msg_type == "task_update":
                            task_id = payload.get("task_id")
                            subtask_id = payload.get("subtask_id")
                            status = payload.get("status")
                            if subtask_id:
                                print(f"        Task {task_id}, Subtask {subtask_id} -> {status}")
                            else:
                                print(f"        Task {task_id} -> {status}")

                        elif msg_type == "complete":
                            print(f"        Agent execution complete!")
                            print(f"        Iterations: {payload.get('iterations')}")
                            print(f"        Tokens: {payload.get('tokens')}")
                            result = payload.get("result")
                            if result:
                                print(f"\n        === FINAL PORTFOLIO RESULT ===")
                                print(f"        {json.dumps(result, indent=2)[:2000]}...")
                            return result  # Exit and return the result

                    except asyncio.TimeoutError:
                        print("    WebSocket timeout (5 min)")
                        return

        except websockets.exceptions.ConnectionClosed as e:
            print(f"    WebSocket connection closed (code={e.code}, reason={e.reason})")
            print("    (Agent continues running - use polling to get final result)")
        except Exception as e:
            print(f"    WebSocket error: {e}")
            print("    (Agent continues running - use polling to get final result)")

    # Step 3: Poll for results in parallel with WebSocket
    async def poll_results():
        """Poll for final results."""
        await asyncio.sleep(2)  # Give agent time to start

        # Use longer timeout since agent can take a while
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            while True:
                try:
                    response = await client.get(
                        f"{BASE_URL}/api/agents/{execution_id}/result",
                        headers={"X-API-Key": API_KEY},
                    )

                    if response.status_code != 200:
                        print(f"\n[Poll] Error: {response.status_code}")
                        await asyncio.sleep(5)
                        continue

                    data = response.json()
                    status = data.get("status")

                    if status == "complete":
                        print("\n[3] Final Result Retrieved:")
                        print(f"    Status: {status}")
                        print(f"    Iterations: {data.get('iterations')}")
                        print(f"    Tokens: {data.get('tokens')}")
                        if data.get("result"):
                            print(f"    Result: {json.dumps(data['result'], indent=2)[:500]}...")
                        return data

                    elif status == "error":
                        print(f"\n[3] Agent Error: {data.get('error')}")
                        return data

                    # Still running, wait and poll again
                    print(f"    [Poll] Status: {status}, waiting...")
                    await asyncio.sleep(10)

                except httpx.ReadTimeout:
                    print("\n[Poll] Request timed out, retrying...")
                    await asyncio.sleep(5)
                except Exception as e:
                    print(f"\n[Poll] Error: {e}")
                    await asyncio.sleep(5)

    # Run WebSocket listener and result poller concurrently
    await asyncio.gather(
        listen_websocket(),
        poll_results(),
    )

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_agent_streaming())
