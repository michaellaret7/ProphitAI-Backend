from app.core.agentic_framework.tool_lib.sub_agents.sector_analyst.prompts import build_orchestrator_context, SECTOR_ANALYST_PROMPT
from app.core.agentic_framework.tool_lib.sub_agents.sector_analyst.agent import SectorAnalyst
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from typing import Optional
from datetime import datetime

def run_sector_analyst(
    sector: str,
    query: Optional[str] = None,
    _simulation_date: Optional[datetime] = None
) -> str:
    """Execute sector analysis using the SectorAnalyst subagent.

    Args:
        sector: The market sector to analyze.
        query: Optional orchestrator preferences/guidance for the analysis.
        _simulation_date: Optional simulation date for backtesting.
    """
    try:
        orchestrator_context = build_orchestrator_context(query)
        user_prompt = SECTOR_ANALYST_PROMPT.format(
            sector=sector,
            orchestrator_context=orchestrator_context
        )
        sector_analyst = SectorAnalyst(
            user_prompt=user_prompt,
            sector=sector,
            simulation_date=_simulation_date
        )
        output = sector_analyst.run()
        return success_response(output["final_answer"])
    except Exception as e:
        error_msg = f"Error running sector analyst sub-agent: {str(e)}"
        print(f"⚠️  {error_msg}")
        return error_response(error_msg)


if __name__ == "__main__":
    print(run_sector_analyst(
        sector="equity_sector_health_care",
        query="""Focus on defensive healthcare stocks with resilient business models: home-based care providers,
        digital health companies, value-based care organizations, and medical device
        companies benefiting from site-of-care migration. Prioritize companies with
        pricing power, strong cash flows, and recession-resistant characteristics for
        2025-2026."""
    ))
