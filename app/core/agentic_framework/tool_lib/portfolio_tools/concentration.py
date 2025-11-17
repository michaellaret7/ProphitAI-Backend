from app.core.calculations.portfolio.concentration import PortfolioConcentration
from app.models.portfolio_models import PortfolioInput
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator
from app.core.agentic_framework.tool_lib.common.schemas import PORTFOLIO_DICT_SCHEMA
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response

def exposure_calculator(portfolio_dict: PortfolioInput | dict, exposure_type: str, **kwargs) -> str:
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)
    v.require_enum('exposure_type', exposure_type, ['net', 'gross', 'long', 'short'])

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values
    portfolio_dict = v.get('portfolio_dict')
    exposure_type = v.get('exposure_type')

    try:
        if exposure_type == "net":
            result = PortfolioConcentration(portfolio_dict).net_exposure()
        elif exposure_type == "gross":
            result = PortfolioConcentration(portfolio_dict).gross_exposure()
        elif exposure_type == "long":
            result = PortfolioConcentration(portfolio_dict).long_exposure()
        elif exposure_type == "short":
            result = PortfolioConcentration(portfolio_dict).short_exposure()
        else:
            return error_response(f"Invalid exposure type: {exposure_type}")
        return success_response({"exposure": result, "type": exposure_type})
    except Exception as e:
        return error_response(e)

def industry_concentration(portfolio_dict: PortfolioInput | dict, industry_level: str, **kwargs) -> str:
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)
    v.require_enum('industry_level', industry_level, ['industry', 'sub_industry'])

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values
    portfolio_dict = v.get('portfolio_dict')
    industry_level = v.get('industry_level')

    try:
        if industry_level == "industry":
            res = PortfolioConcentration(portfolio_dict).industry_concentration()
        elif industry_level == "sub_industry":
            res = PortfolioConcentration(portfolio_dict).sub_industry_concentration()
        else:
            return error_response(f"Invalid industry level: {industry_level}")
        # Round values to 5 decimals for cleaner display
        data = {k: round(float(v), 5) for k, v in res.items()}
        return success_response(data)
    except Exception as e:
        return error_response(e)

@log_simulation_data_range()
def VaR_calculator(portfolio_dict: PortfolioInput | dict, level: str, **kwargs) -> str:
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)
    v.require_enum('level', level, ['portfolio', 'industry', 'sub_industry'])

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values
    portfolio_dict = v.get('portfolio_dict')
    level = v.get('level')

    try:
        # Extract simulation date if present (for backtesting/simulation)
        end_date = kwargs.get('_simulation_date', None)

        if level == "industry":
            res = PortfolioConcentration(portfolio_dict, end_date=end_date).industry_var()
            data = {k: round(float(v), 5) for k, v in res.items()}
        elif level == "sub_industry":
            res = PortfolioConcentration(portfolio_dict, end_date=end_date).sub_industry_var()
            data = {k: round(float(v), 5) for k, v in res.items()}
        elif level == "portfolio":
            # Single float
            val = PortfolioConcentration(portfolio_dict, end_date=end_date).portfolio_var()
            data = {"VaR": round(float(val), 5) if val is not None else None}
        else:
            return error_response(f"Invalid level: {level}")
        return success_response(data)
    except Exception as e:
        return error_response(e)


# Tool Schema Constants
EXPOSURE_CALCULATOR_DESCRIPTION = (
    "Calculate portfolio exposure metrics. Net exposure is long minus short exposure. "
    "Gross exposure is the sum of absolute values of all positions. Long exposure is the sum of all long positions. "
    "Short exposure is the absolute value sum of all short positions. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings and specify 'exposure_type'. "
    "Example: exposure_calculator(portfolio_dict={'AAPL': {'allocation': 0.6, 'position': 'long'}, 'TSLA': {'allocation': 0.4, 'position': 'short'}}, exposure_type='gross')"
)

EXPOSURE_CALCULATOR_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
        "exposure_type": {
            "type": "string",
            "description": "Type of exposure to calculate. Must be one of: 'net' (long minus short), 'gross' (sum of absolute values), 'long' (sum of long positions), or 'short' (sum of short positions).",
            "enum": ["net", "gross", "long", "short"],
        },
    },
    "required": ["portfolio_dict", "exposure_type"],
    "additionalProperties": False
}

EXPOSURE_CALCULATOR_TOOL = {
    "name": "portfolio_exposure_calculator",
    "description": EXPOSURE_CALCULATOR_DESCRIPTION,
    "parameters": EXPOSURE_CALCULATOR_PARAMETERS,
    "function": exposure_calculator,
}

# ------------------------------------------------------------- #

INDUSTRY_CONCENTRATION_DESCRIPTION = (
    "Calculate portfolio concentration by industry or sub-industry. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings and specify 'industry_level' as 'industry' or 'sub_industry'. "
    "Returns a dictionary of allocation percentages per group (rounded to 5 decimals). "
    "Example: industry_concentration(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'KO': {'allocation': 0.5, 'position': 'long'}}, industry_level='sub_industry')"
)

INDUSTRY_CONCENTRATION_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
        "industry_level": {
            "type": "string",
            "description": "Level of industry aggregation. 'industry' provides broader categories (e.g., 'Food Products'), while 'sub_industry' provides more granular categories (e.g., 'Packaged Foods').",
            "enum": ["industry", "sub_industry"],
        },
    },
    "required": ["portfolio_dict", "industry_level"],
    "additionalProperties": False
}

INDUSTRY_CONCENTRATION_TOOL = {
    "name": "portfolio_industry_concentration",
    "description": INDUSTRY_CONCENTRATION_DESCRIPTION,
    "parameters": INDUSTRY_CONCENTRATION_PARAMETERS,
    "function": industry_concentration,
}

# ------------------------------------------------------------- #

VAR_CALCULATOR_DESCRIPTION = (
    "Calculate Value at Risk (VaR) at portfolio, industry, or sub-industry level. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings and specify 'level'. "
    "Portfolio level returns a single float; industry and sub-industry return dictionaries per group (rounded to 5 decimals). "
    "Example: VaR_calculator(portfolio_dict={'AAPL': {'allocation': 0.6, 'position': 'long'}, 'TSLA': {'allocation': 0.4, 'position': 'short'}}, level='industry')"
)

VAR_CALCULATOR_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
        "level": {
            "type": "string",
            "description": "Level at which to calculate VaR. 'portfolio' calculates overall portfolio VaR, 'industry' calculates VaR by industry groups, 'sub_industry' calculates VaR by sub-industry groups.",
            "enum": ["portfolio", "industry", "sub_industry"],
        },
    },
    "required": ["portfolio_dict", "level"],
    "additionalProperties": False
}

VAR_CALCULATOR_TOOL = {
    "name": "portfolio_VaR_calculator",
    "description": VAR_CALCULATOR_DESCRIPTION,
    "parameters": VAR_CALCULATOR_PARAMETERS,
    "function": VaR_calculator,
}