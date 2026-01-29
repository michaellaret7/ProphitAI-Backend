from app.core.calculations.stress_test.runner import run_stress_test_workflow
from app.models.portfolio_models import PortfolioInput
import json
from app.utils.tool_validator import ToolValidator
from app.core.atlas.tools.tool_schemas import PORTFOLIO_DICT_SCHEMA
from app.core.atlas.tools.responses import success_response, error_response

def stress_test(portfolio_dict: PortfolioInput | dict = None, _simulation_date: str = None) -> str:
    """
    Run comprehensive stress tests on a portfolio including market crash scenarios (-20%, -30%, -40%), sector rotation stress, interest rate shock, inflation spike, and correlation breakdown scenarios.

    Args:
        portfolio_dict: Portfolio to stress test
        _simulation_date: Optional simulation date (injected by agent framework, not used by tool)
    """
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values
    portfolio_dict = v.get('portfolio_dict')

    try:
        results = run_stress_test_workflow(portfolio_dict)
        return success_response(results)
    except Exception as e:
        error_msg = f"Error running stress test: {str(e)}"
        print(f"Warning: {error_msg}")
        return error_response(error_msg)


# Tool Schema Constants
STRESS_TEST_DESCRIPTION = (
    "Run comprehensive stress tests on a portfolio including market crash scenarios (-20%, -30%, -40%), sector rotation stress, interest rate shock, inflation spike, and correlation breakdown scenarios. "
    "Returns detailed dictionary with risk metrics, VaR calculations (%), scenario-specific performance impacts (%), maximum drawdowns (%), and stress test results by scenario type. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings. "
    "Example: stress_test(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'TSLA': {'allocation': 0.5, 'position': 'short'}})"
)

STRESS_TEST_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

STRESS_TEST_TOOL = {
    "name": "portfolio_stress_test",
    "description": STRESS_TEST_DESCRIPTION,
    "parameters": STRESS_TEST_PARAMETERS,
    "function": stress_test,
}
