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
def get_product_segmentation(ticker: str, **kwargs) -> str:
    """Get product segmentation for a ticker"""
    fmp = FMP_API_DATA()
    data = fmp.get_revenue_product_segmentation(ticker)

    if data is None or len(data) == 0:
        return error_response(f"No product segmentation data found for {ticker}")

    # Clean up data - keep only symbol, date, and data fields
    cleaned_data = [
        {
            'symbol': entry['symbol'],
            'date': entry['date'],
            'data': entry['data']
        }
        for entry in data
    ]

    return success_response(cleaned_data)

# Tool Schema Constants
GET_PRODUCT_SEGMENTATION_DESCRIPTION = (
    "Get revenue breakdown by product segment for a ticker across multiple fiscal years.\n\n"
    "This tool provides detailed product/business segment revenue data, showing how a company "
    "generates revenue across different business lines, products, or divisions. Essential for "
    "understanding business mix, segment concentration, and growth drivers.\n\n"
    "**Data Returned:**\n"
    "  - **symbol**: Ticker symbol\n"
    "  - **date**: Fiscal year end date for each period\n"
    "  - **data**: Dictionary of segment names to revenue values (in USD)\n\n"
    "**Revenue Segments:**\n"
    "  Segment names and structure vary by company based on their business organization:\n"
    "  - Technology companies: Cloud, Hardware, Software, Services\n"
    "  - Retailers: Online, Physical Stores, Subscription Services\n"
    "  - Industrials: Different product lines or geographical regions\n"
    "  - Conglomerates: Multiple business divisions\n\n"
    "**Historical Data:**\n"
    "  Returns multi-year history showing segment evolution over time, typically 5-10 years "
    "  of annual data depending on availability.\n\n"
    "**Use Cases:**\n"
    "  - **Diversification Analysis**: Assess revenue concentration vs diversification\n"
    "  - **Segment Growth**: Identify fast-growing vs declining business segments\n"
    "  - **Portfolio Construction**: Build thematic exposure (e.g., cloud revenue)\n"
    "  - **Competitive Analysis**: Compare segment mix across industry peers\n"
    "  - **M&A Analysis**: Understand post-merger business composition changes\n"
    "  - **Risk Assessment**: Identify dependency on single products/segments\n\n"
    "**Key Insights:**\n"
    "  - **Concentration Risk**: >50% revenue from single segment = high concentration\n"
    "  - **Growth Drivers**: Fastest growing segments drive future performance\n"
    "  - **Segment Shifts**: Changing mix indicates strategic pivots\n"
    "  - **Diversification**: More balanced segments = lower business risk\n"
    "  - **Emerging Segments**: New/small segments may become major growth drivers\n"
    "  - **Declining Segments**: Shrinking segments may need turnaround or divestiture\n\n"
    "**Analysis Tips:**\n"
    "  - Calculate year-over-year growth rates by segment\n"
    "  - Compute segment as % of total revenue to track mix changes\n"
    "  - Compare segment growth vs company-wide growth\n"
    "  - Identify segments with consistent vs volatile revenue\n"
    "  - Track segment additions/removals indicating structural changes\n\n"
    "**Example:**\n"
    "  get_product_segmentation(ticker='LMT')  # Lockheed Martin's defense segments\n"
    "  get_product_segmentation(ticker='AMZN')  # Amazon's retail vs AWS vs ads\n"
    "  get_product_segmentation(ticker='AAPL')  # Apple's iPhone, Mac, Services, etc."
)

GET_PRODUCT_SEGMENTATION_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": (
                "The ticker symbol to get product segmentation data for. "
                "For example: 'AAPL', 'MSFT', 'AMZN', 'LMT', etc."
            ),
        },
    },
    "required": ["ticker"],
}

GET_PRODUCT_SEGMENTATION_TOOL = {
    "name": "get_product_segmentation",
    "description": GET_PRODUCT_SEGMENTATION_DESCRIPTION,
    "parameters": GET_PRODUCT_SEGMENTATION_PARAMETERS,
    "function": get_product_segmentation,
}
