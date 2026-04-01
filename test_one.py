"""Interactive chat agent with all tools available."""

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode
from prophitai_tools.registry import ALL_TOOL_FUNCTIONS


def main():
    agent = Agent(
        provider="anthropic",
        model="claude-sonnet-4-6",
        print_mode=PrintMode.VERBOSE,
        deferred_tools=ALL_TOOL_FUNCTIONS,
        max_iterations=50,
    )

    conversation_history = []

    print("\n" + "=" * 60)
    print("  ProphitAI Chat Agent")
    print("  Type 'quit' or 'exit' to end the session.")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye.")
            break

        result = agent.run(
            user_message=user_input,
            conversation_history=conversation_history,
            max_iterations=50,
        )

        print(f"\nAssistant: {result.answer}\n")

        # Reason: Track conversation for multi-turn context
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": result.answer})


if __name__ == "__main__":
    main()
