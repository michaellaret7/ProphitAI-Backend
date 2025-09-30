import yaml
from app.utils.gpt_parser import canonical_portfolio
from app.core.calculations.portfolio.concentration import PortfolioConcentration
from app.models.portfolio_models import PortfolioInput

def exposure_calculator(portfolio_dict: PortfolioInput | dict, exposure_type: str) -> str:
    try:
        portfolio_dict = canonical_portfolio(portfolio_dict)
        if exposure_type == "net":
            result = PortfolioConcentration(portfolio_dict).net_exposure()
        elif exposure_type == "gross":
            result = PortfolioConcentration(portfolio_dict).gross_exposure()
        elif exposure_type == "long":
            result = PortfolioConcentration(portfolio_dict).long_exposure()
        elif exposure_type == "short":
            result = PortfolioConcentration(portfolio_dict).short_exposure()
        else:
            return yaml.dump({"success": False, "error": f"Invalid exposure type: {exposure_type}"}, default_flow_style=False)
        return yaml.dump({"success": True, "data": {"exposure": result, "type": exposure_type}}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)

def industry_concentration(portfolio_dict: PortfolioInput | dict, industry_level: str) -> str:
    try:
        portfolio_dict = canonical_portfolio(portfolio_dict)
        if industry_level == "industry":
            res = PortfolioConcentration(portfolio_dict).industry_concentration()
        elif industry_level == "sub_industry":
            res = PortfolioConcentration(portfolio_dict).sub_industry_concentration()
        else:
            return yaml.dump({"success": False, "error": f"Invalid industry level: {industry_level}"}, default_flow_style=False)
        # Round values to 5 decimals for cleaner display
        data = {k: round(float(v), 5) for k, v in res.items()}
        return yaml.dump({"success": True, "data": data}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)

def VaR_calculator(portfolio_dict: PortfolioInput | dict, level: str) -> str:
    try:
        portfolio_dict = canonical_portfolio(portfolio_dict)
        if level == "industry":
            res = PortfolioConcentration(portfolio_dict).industry_var()
            data = {k: round(float(v), 5) for k, v in res.items()}
        elif level == "sub_industry":
            res = PortfolioConcentration(portfolio_dict).sub_industry_var()
            data = {k: round(float(v), 5) for k, v in res.items()}
        elif level == "portfolio":
            # Single float
            val = PortfolioConcentration(portfolio_dict).portfolio_var()
            data = {"VaR": round(float(val), 5) if val is not None else None}
        else:
            return yaml.dump({"success": False, "error": f"Invalid level: {level}"}, default_flow_style=False)
        return yaml.dump({"success": True, "data": data}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)


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
                exposure_calculator(
                    portfolio_dict={
                        "AAPL": {"allocation": 0.125, "position": "long"},
                        "MSFT": {"allocation": 0.125, "position": "long"},
                        "AMZN": {"allocation": 0.125, "position": "long"},
                        "TSLA": {"allocation": 0.125, "position": "long"},
                        "META": {"allocation": 0.125, "position": "long"},
                        "SPY": {"allocation": 0.125, "position": "long"},
                        "QQQ": {"allocation": 0.125, "position": "long"},
                        "IWM": {"allocation": 0.125, "position": "long"}
                    },
                    exposure_type="gross"
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
                industry_concentration(
                    portfolio_dict={
                        "AAPL": {"allocation": 0.125, "position": "long"},
                        "MSFT": {"allocation": 0.125, "position": "long"},
                        "AMZN": {"allocation": 0.125, "position": "long"},
                        "TSLA": {"allocation": 0.125, "position": "long"},
                        "META": {"allocation": 0.125, "position": "long"},
                        "SPY": {"allocation": 0.125, "position": "long"},
                        "QQQ": {"allocation": 0.125, "position": "long"},
                        "IWM": {"allocation": 0.125, "position": "long"}
                    },
                    industry_level="sub_industry"
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
                VaR_calculator(
                    portfolio_dict={
                        "AAPL": {"allocation": 0.125, "position": "long"},
                        "MSFT": {"allocation": 0.125, "position": "long"},
                        "AMZN": {"allocation": 0.125, "position": "long"},
                        "TSLA": {"allocation": 0.125, "position": "long"},
                        "META": {"allocation": 0.125, "position": "long"},
                        "SPY": {"allocation": 0.125, "position": "long"},
                        "QQQ": {"allocation": 0.125, "position": "long"},
                        "IWM": {"allocation": 0.125, "position": "long"}
                    },
                    level="industry"
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