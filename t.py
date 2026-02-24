from app.core.atlas.agents.orchestrator_agent import OrchestratorAgent
from app.core.atlas.models import PrintMode

task = """
Planet Fitness had their earnings today and they beat all of their estimates but the stock is down 6%. 
I am bullish on the stock and I want you do some deep analytics and tell me if i should buy the dip or just hold my stake.
"""

orchestrator = OrchestratorAgent(
    task=task,
    provider="anthropic",
    model="claude-sonnet-4-6",
    max_iterations=50,
    print_mode=PrintMode.PRODUCTION,
    temperature=0.5,
    plan_first=True,
)

result = orchestrator.run()

print(result.answer)