from app.core.atlas.agents import OrchestratorAgent
from app.core.atlas.models import PrintMode
from app.domain.ai_watchlist.prompts import WATCHLIST_PROMPT
from .models import WatchlistResponse


class Watchlist(OrchestratorAgent):
    def __init__(
        self,
        user_preferences: str,
        print_mode: PrintMode = PrintMode.PRODUCTION,
        provider: str = "gemini",
        model: str = "gemini-3-pro-preview"
    ):

        task = WATCHLIST_PROMPT.format(user_query=user_preferences)

        super().__init__(
            task=task,
            print_mode=print_mode,
            provider=provider,
            model=model,
            format_output=WatchlistResponse
        )

if __name__ == "__main__":
    watchlist = Watchlist(
        user_preferences="Build me a watchlist of software stocks that you think will rebound from the recent software selloff.",
        provider="anthropic",
        model="claude-opus-4-6",
    )
    result = watchlist.run()
    print(result.parsed_output.model_dump_json(indent=4))

