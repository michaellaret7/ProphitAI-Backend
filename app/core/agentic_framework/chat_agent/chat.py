"""Interactive CLI for ChatAgent.

Run with: python -m app.core.agentic_framework.chat_agent.cli
"""

import re

from app.core.agentic_framework.chat_agent import ChatAgent, ChatSession
from app.core.agentic_framework.base_agent.utils.models import PrintMode

# ANSI color codes
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
RESET = "\033[0m"


def format_markdown(text: str) -> str:
    """Convert markdown to ANSI-colored terminal output."""
    lines = text.split("\n")
    formatted = []

    for line in lines:
        # Headers: ## Header -> colored and bold
        if line.startswith("###"):
            line = f"{BLUE}{BOLD}{line.lstrip('#').strip()}{RESET}"
        elif line.startswith("##"):
            line = f"{CYAN}{BOLD}{line.lstrip('#').strip()}{RESET}"
        elif line.startswith("#"):
            line = f"{GREEN}{BOLD}{line.lstrip('#').strip()}{RESET}"
        else:
            # Bold: **text** -> bold
            line = re.sub(r"\*\*(.+?)\*\*", rf"{BOLD}\1{RESET}", line)
            # Italic/emphasis: *text* -> dim (avoid matching ** patterns)
            line = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", rf"{DIM}\1{RESET}", line)

        formatted.append(line)

    return "\n".join(formatted)


def main():
    """Run interactive chat session."""
    print("=" * 60)
    print("ChatAgent Interactive Session")
    print("Press Ctrl+C to exit")
    print("=" * 60)

    agent = ChatAgent(print_mode=PrintMode.PRODUCTION)
    session = ChatSession(session_id="interactive")

    while True:
        try:
            user_input = input("\n[You]: ").strip()

            if not user_input:
                continue

            response = agent.run(user_input, session.get_history())

            session.add_user_message(user_input)
            session.add_assistant_message(response.answer)

            print(f"\n[Agent]: {format_markdown(response.answer)}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            continue


if __name__ == "__main__":
    main()
