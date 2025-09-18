from app.utils.gpt_parser import canonical_portfolio
from app.core.calculations.portfolio.concentration import PortfolioConcentration
from app.models.portfolio_models import PortfolioInput

def exposure_calculator(portfolio_dict: PortfolioInput | dict, exposure_type: str):
    portfolio_dict = canonical_portfolio(portfolio_dict)
    if exposure_type == "net":
        return PortfolioConcentration(portfolio_dict).net_exposure()
    elif exposure_type == "gross":
        return PortfolioConcentration(portfolio_dict).gross_exposure()
    elif exposure_type == "long":
        return PortfolioConcentration(portfolio_dict).long_exposure()
    elif exposure_type == "short":
        return PortfolioConcentration(portfolio_dict).short_exposure()
    else:
        raise ValueError(f"Invalid exposure type: {exposure_type}")

def industry_concentration(portfolio_dict: PortfolioInput | dict, industry_level: str):
    portfolio_dict = canonical_portfolio(portfolio_dict)
    if industry_level == "industry":
        res = PortfolioConcentration(portfolio_dict).industry_concentration()
    elif industry_level == "sub_industry":
        res = PortfolioConcentration(portfolio_dict).sub_industry_concentration()
    else:
        raise ValueError(f"Invalid industry level: {industry_level}")
    # Round values to 5 decimals for cleaner display
    return {k: round(float(v), 5) for k, v in res.items()}

def VaR_calculator(portfolio_dict: PortfolioInput | dict, level: str):
    portfolio_dict = canonical_portfolio(portfolio_dict)
    if level == "industry":
        res = PortfolioConcentration(portfolio_dict).industry_var()
    elif level == "sub_industry":
        res = PortfolioConcentration(portfolio_dict).sub_industry_var()
    elif level == "portfolio":
        # Single float
        val = PortfolioConcentration(portfolio_dict).portfolio_var()
        return round(float(val), 5) if val is not None else float('nan')
    else:
        raise ValueError(f"Invalid level: {level}")
    # Ensure dict results are rounded to 5 decimals
    return {k: round(float(v), 5) for k, v in res.items()}

    