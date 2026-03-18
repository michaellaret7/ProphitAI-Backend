from typing import Optional

from app.core.atlas.agents import OrchestratorAgent
from app.core.atlas.models import PrintMode
from app.core.atlas.models.callbacks import ChatCallback
from app.domain.ai_watchlist.prompts import WATCHLIST_PROMPT
from .models import WatchlistResponse


class Watchlist(OrchestratorAgent):
    """AI Watchlist agent - builds themed stock watchlists via orchestration."""

    def __init__(
        self,
        user_preferences: str,
        print_mode: PrintMode = PrintMode.PRODUCTION,
        provider: str = "openai",
        model: str = "gpt-5.4",
        chat_callback: Optional[ChatCallback] = None,
        session_id: str = "watchlist",
    ):
    
        task = WATCHLIST_PROMPT.format(user_query=user_preferences)

        super().__init__(
            task=task,
            print_mode=print_mode,
            provider=provider,
            model=model,
            format_output=WatchlistResponse,
            chat_callback=chat_callback,
            session_id=session_id,
        )

