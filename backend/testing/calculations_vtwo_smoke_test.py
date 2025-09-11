import os
from typing import Dict, Any

from backend.src.agentic_framework.base_agent.agent import BaseAgent


def create_and_run_simple_agent() -> Dict[str, Any]:
    """
    Minimal smoke test that instantiates the BaseAgent, runs a short plan,
    and prints the final result. Keeps configuration simple and self-contained.
    """

    system_prompt = (
        "You are a focused execution agent. Use available tools to accomplish the goal "
        "concisely. Prefer the calculator tool when doing arithmetic. Always end with "
        "'Final Answer:' when done."
    )

    user_prompt = (
        "Goal: Use the calculator tool to compute 2+2 and provide the result. "
        "Do not browse the web. Keep it to the minimum steps."
    )

    agent = BaseAgent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_iterations=75,
        verbose=True,
        plan_first=True,  # Let the agent create a tiny plan and execute
        strict_validation=True,
        save_messages=True,
        use_error_memory=True,
        use_episodic_memory=False,
    )

    result = agent.run()
    final_text = result.get("final_text", "")
    print("\n=== SIMPLE AGENT FINAL TEXT ===\n")
    print(final_text)
    return result


if __name__ == "__main__":
    create_and_run_simple_agent()

