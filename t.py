from app.core.atlas.agents.chat_agent import ChatAgent
from app.core.atlas.models import PrintMode

chat = ChatAgent(
    provider="anthropic",
    model="claude-sonnet-4-6",
    print_mode=PrintMode.PRODUCTION,
    temperature=0.7,
    max_iterations=20,
    user_id="user_3Anw2M5QNbqc7G7z2l5Uo48aHjw",
)

chat.run_interactive()