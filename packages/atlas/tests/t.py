from dotenv import load_dotenv
from prophitai_atlas.agents.agent import Agent
from prophitai_atlas.models import PrintMode
from prophitai_tools import ALL_TOOL_FUNCTIONS

load_dotenv()

agent = Agent(
    provider="bedrock",
    model="nemotron-super-3-120b",
    print_mode=PrintMode.PRODUCTION,
    tools=ALL_TOOL_FUNCTIONS,
)

result = agent.run(
    user_message=(
        "Run a comprehensive analysis on Microsoft (MSFT). Cover recent stock performance, "
        "key risk metrics, fundamental health, factor exposures, and any relevant news. "
        "Provide a clear investment summary."
        "Then, find some investment candidates to replace MSFT in my portfolio."
        "Finally, propose a trade for each candidate."
    ),
)

print(result.answer)