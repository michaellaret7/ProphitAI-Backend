from app.core.agentic_framework.tool_lib.data_tools.screeners.etf.execute import execute_query
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
import yaml

def etf_screener(**kwargs):
    """Screen ETFs based on fundamental, valuation, and performance criteria."""
    # Convert lists to tuples for range parameters (LLM sends JSON arrays)
    converted_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, list) and len(value) == 2:
            converted_kwargs[key] = tuple(value)
        else:
            converted_kwargs[key] = value

    results, error = execute_query(**converted_kwargs)

    if error is not None:
        return error_response(error)

    # Convert Pydantic models to dicts for clean YAML output
    results_data = [r.model_dump() for r in results]
    results_yaml = yaml.dump(results_data, default_flow_style=False)

    return success_response(results_yaml)


if __name__ == "__main__":
    results = etf_screener(
        # industries=['equity_etfs'],
        # beta=(0, 0.5),
        # ann_vol=(0, 0.2),
        # ann_ret=(0.2, None),
        # alpha=(0.1, None),
        dividend_yield_ttm=(0.1, None)
    )
    print(results)

    from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
    from app.core.calculations.returns.calculator import ReturnsCalculator
    from app.core.calculations.performance.calculator import PerformanceCalculator

    data = fetch_bulk_ohlcv_data_for_tickers(['PFFL', 'SPY'], '2024-12-03', '2025-12-03', returns=True)

    print(data['PFFL'])

    returns = ReturnsCalculator.daily_price_returns(data['PFFL']['adj_close'])
    spy_returns = ReturnsCalculator.daily_price_returns(data['SPY']['adj_close'])
    alpha = PerformanceCalculator.alpha_jensen(returns, spy_returns, periods_per_year=252)
    print(alpha)


