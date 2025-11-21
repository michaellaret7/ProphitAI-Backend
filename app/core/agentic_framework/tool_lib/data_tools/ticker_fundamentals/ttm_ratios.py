from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.token_count import get_token_count
from datetime import datetime
from typing import Optional
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.utils.tool_validator import ToolValidator
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

@log_simulation_data_range()
def get_ratios_ttm(ticker: str, **kwargs) -> str:
    """Get trailing twelve months (TTM) financial ratios for a ticker"""
    fmp = FMP_API_DATA()
    data = fmp.get_ratios_ttm(ticker)

    if data is None or len(data) == 0:
        return error_response(f"No TTM ratios found for {ticker}")

    # Round all numeric values to 4 decimal places
    if isinstance(data, list) and len(data) > 0:
        data[0] = {k: round(v, 4) if isinstance(v, (int, float)) else v for k, v in data[0].items()}
        
    return success_response(data)

if __name__ == "__main__":
    x = get_ratios_ttm(ticker='AAPL')
    print(x)
    print(get_token_count(x))