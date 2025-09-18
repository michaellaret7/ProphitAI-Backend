from app.core.calculations.portfolio.utils import prepare_portfolio_data
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.portfolio.correlation import CorrelationAnalysis
from app.models.portfolio_models import PortfolioInput
import pandas as pd
from app.utils.gpt_parser import canonical_portfolio

def correlation_matrix(portfolio_dict: PortfolioInput | dict) -> dict:
    """
    Calculate pairwise correlations and return as records for easy LLM consumption.

    Output shape:
    {
      "correlations": [
        {"ticker1": "T1", "ticker2": "T2", "correlation": 0.123}
      ]
    }
    """
    if not portfolio_dict:
        return {"correlations": []}

    try:
        portfolio_dict = canonical_portfolio(portfolio_dict)
    except ValueError:
        return {"correlations": []}

    # Use utility to get portfolio data
    weights, price_data, dividend_data = prepare_portfolio_data(
        portfolio=portfolio_dict,
        lookback_days=252,
        include_dividends=False
    )

    if not price_data:
        return {"correlations": []}

    # Calculate returns for each ticker
    returns_df = pd.DataFrame({
        ticker: ReturnsCalculator.daily_price_returns(prices)
        for ticker, prices in price_data.items()
        if prices is not None and not prices.empty
    }).dropna()

    if returns_df.empty:
        return {"correlations": []}

    # Compute correlation matrix and round
    corr_df = CorrelationAnalysis.correlation_matrix(returns_df)
    if corr_df is None or corr_df.empty:
        return {"correlations": []}
    corr_df = corr_df.round(3)

    # Use the correlation matrix's own column order to avoid key-order drift
    ordered_tickers = [t for t in corr_df.columns if t in corr_df.index]

    # Build records for unique pairs (upper triangle, excluding diagonal)
    records = []
    for i, t1 in enumerate(ordered_tickers):
        for j in range(i + 1, len(ordered_tickers)):
            t2 = ordered_tickers[j]
            value = corr_df.loc[t1, t2]
            try:
                value = float(value)
            except Exception:
                pass
            records.append({
                "pair": f"{t1} | {t2}",
                "corr": value
            })

    return {"correlations": records}

if __name__ == "__main__":
    portfolio_dict = {
        "MNST": {"allocation": 0.05, "position": "long"},
        "COTY": {"allocation": 0.05, "position": "short"},
        "COST": {"allocation": 0.05, "position": "long"},
        "KR": {"allocation": 0.05, "position": "long"},
        "BJ": {"allocation": 0.05, "position": "long"},
        "WBA": {"allocation": 0.05, "position": "short"},
        "UNFI": {"allocation": 0.05, "position": "short"},
        "TGT": {"allocation": 0.05, "position": "short"},
        "PRMB": {"allocation": 0.05, "position": "short"},
    }
    print(correlation_matrix(portfolio_dict))