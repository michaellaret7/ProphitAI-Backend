"""Interactive chat REPL for the Atlas ChatAgent with token streaming."""

from typing import Any, Dict, List

from prophitai_api.agents.chat import ChatAgent
from prophitai_atlas.models.callbacks import ConsoleStreamCallback


def main() -> None:
    callback = ConsoleStreamCallback()
    agent = ChatAgent(chat_callback=callback, session_id="repl")

    history: List[Dict[str, Any]] = []

    print("Atlas chat REPL — type 'exit' or Ctrl+C to quit.\n")

    while True:
        try:
            user_input = input("you: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            return

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", ":q"}:
            print("bye.")
            return

        callback.reset()

        response = agent.run(user_input, conversation_history=history)

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response.answer})


if __name__ == "__main__":
    main()
