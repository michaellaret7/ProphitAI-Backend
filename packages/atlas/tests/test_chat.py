"""Interactive chat test — simulates the API flow in the terminal.

Creates an Agent and ChatSession, then loops on user input, passing
conversation history each turn exactly as the API would.
"""

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode, ChatSession


def main():
    agent = Agent(
        model="anthropic/claude-sonnet-4.6",
        print_mode=PrintMode.PRODUCTION,
        temperature=0.7,
    )

    session = ChatSession(session_id="test-session")

    print("=" * 60)
    print("Interactive Chat Test (OpenRouter)")
    print("Type your message and press Enter. Ctrl+C to exit.")
    print("=" * 60)

    while True:
        try:
            user_message = input("\n[You]: ").strip()
            if not user_message:
                continue

            response = agent.run(user_message, session.get_history())

            session.add_user_message(user_message)
            session.add_assistant_message(response.answer)

            print(f"\n[Agent]: {response.answer}")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            continue


if __name__ == "__main__":
    main()
