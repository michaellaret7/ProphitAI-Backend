import yaml
from app.core.calculations.stress_test.runner import run_stress_test_workflow
from app.models.portfolio_models import PortfolioInput
from app.utils.gpt_parser import canonical_portfolio
from app.utils.decorators.tool_validation import validate_required_args, validate_portfolio_dict
import json

@validate_required_args('portfolio_dict')
@validate_portfolio_dict()
def stress_test(portfolio_dict: PortfolioInput | dict = None) -> str:
    """
    Run comprehensive stress tests on a portfolio including market crash scenarios (-20%, -30%, -40%), sector rotation stress, interest rate shock, inflation spike, and correlation breakdown scenarios.
    """
    try:
        if not portfolio_dict:
            return yaml.dump({"success": False, "error": "Portfolio dictionary is required"}, default_flow_style=False)

        portfolio_dict = canonical_portfolio(portfolio_dict)
        results = run_stress_test_workflow(portfolio_dict)
        return yaml.dump({"success": True, "data": results}, default_flow_style=False)
    except Exception as e:
        error_msg = f"Error running stress test: {str(e)}"
        print(f"Warning: {error_msg}")
        return yaml.dump({"success": False, "error": error_msg}, default_flow_style=False)


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
        "portfolio_dict": {
            "type": "object",
            "description": (
                "**MANDATORY - DO NOT OMIT THIS PARAMETER.** "
                "Complete portfolio with ALL holdings. "
                "Keys = ticker symbols (e.g., 'AAPL'). "
                "Values = objects with 'allocation' (decimal 0-1) and 'position' ('long'/'short'). "
                "You MUST include this parameter with all portfolio tickers."
                "\n\n"
                """Example of CORRECT function call:
                stress_test(
                    portfolio_dict={
                        "AAPL": {"allocation": 0.125, "position": "long"},
                        "MSFT": {"allocation": 0.125, "position": "long"},
                        "AMZN": {"allocation": 0.125, "position": "long"},
                        "TSLA": {"allocation": 0.125, "position": "short"},
                        "META": {"allocation": 0.125, "position": "short"},
                        "SPY": {"allocation": 0.125, "position": "long"},
                        "QQQ": {"allocation": 0.125, "position": "long"},
                        "IWM": {"allocation": 0.125, "position": "short"}
                    }
                )"""
            ),
            "patternProperties": {
                "^[A-Z]{1,5}$": {
                    "type": "object",
                    "properties": {
                        "allocation": {
                            "type": "number",
                            "description": "Weight as decimal (e.g., 0.125 for 12.5%)",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "position": {
                            "type": "string",
                            "description": "Must be 'long' or 'short'",
                            "enum": ["long", "short"]
                        }
                    },
                    "required": ["allocation", "position"],
                    "additionalProperties": False
                }
            },
            "minProperties": 1,
            "additionalProperties": False
        },
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



if __name__ == "__main__":
    print(stress_test(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'TSLA': {'allocation': 0.5, 'position': 'short'}}))