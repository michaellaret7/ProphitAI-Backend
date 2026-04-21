from pathlib import Path

from prophitai_substack.trade_idea.agent import TradeIdeaAgent
from prophitai_atlas.models import PrintMode
from prophitai_shared.time_utils import get_current_utc_time


def run_trade_idea_agent():

    agent = TradeIdeaAgent(
        provider="anthropic",
        model="claude-opus-4-7",
        print_mode=PrintMode.PRODUCTION,
    )

    response = agent.run()

    timestamp = get_current_utc_time().strftime("%Y-%m-%d_%H%M%S")
    output_dir = Path(__file__).parent / "src" / "prophitai_substack" / "submissions" / "trade_ideas"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"trade_idea_{timestamp}.md"
    output_file.write_text(response.answer, encoding="utf-8")

    print(f"\nSaved to: {output_file}")


if __name__ == "__main__":
    run_trade_idea_agent()
