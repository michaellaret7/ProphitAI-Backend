"""Product segmentation tools.

Provides tools for fetching revenue breakdown by product segment
for companies across multiple fiscal years.
"""

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_data.clients.fmp import FMP_API_DATA


# ================================
# --> Tools
# ================================

@agent_tool(name="get_product_segmentation", category="ticker_info")
def get_product_segmentation(
    ticker: str,
) -> str:
    """
    Get revenue breakdown by product segment for a ticker across multiple fiscal years.

    Provides detailed product/business segment revenue data, showing how a company
    generates revenue across different business lines, products, or divisions.
    Essential for understanding business mix, segment concentration, and growth drivers.

    **Revenue Segments:**
    Segment names vary by company based on their business organization:
    - Technology companies: Cloud, Hardware, Software, Services
    - Retailers: Online, Physical Stores, Subscription Services
    - Industrials: Different product lines or geographical regions
    - Conglomerates: Multiple business divisions

    **Historical Data:**
    Returns multi-year history showing segment evolution over time, typically
    5-10 years of annual data depending on availability.

    **Use Cases:**
    - Diversification Analysis: Assess revenue concentration vs diversification
    - Segment Growth: Identify fast-growing vs declining business segments
    - Portfolio Construction: Build thematic exposure (e.g., cloud revenue)
    - Competitive Analysis: Compare segment mix across industry peers
    - Risk Assessment: Identify dependency on single products/segments

    **Key Insights:**
    - Concentration Risk: >50% revenue from single segment = high concentration
    - Growth Drivers: Fastest growing segments drive future performance
    - Segment Shifts: Changing mix indicates strategic pivots
    - Emerging Segments: New/small segments may become major growth drivers

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'AMZN', 'LMT')

    Returns:
        Multi-year revenue breakdown by product segment with symbol, date,
        and data dict mapping segment names to revenue values (in USD)

    Examples:
        get_product_segmentation(ticker='AAPL')
        >>> {"success": True, "data": [{"symbol": "AAPL", "date": "2025-09-30", "data": {"iPhone": ..., "Services": ...}}]}

        get_product_segmentation(ticker='AMZN')
        >>> {"success": True, "data": [{"symbol": "AMZN", "date": "2025-12-31", "data": {"AWS": ..., "Online stores": ...}}]}

    Raises:
        Exception: If ticker is invalid or no data found
    """
    try:
        fmp = FMP_API_DATA()
        data = fmp.get_revenue_product_segmentation(ticker.upper())

        if data is None or len(data) == 0:
            return error_response(f"No product segmentation data found for {ticker}")

        cleaned_data = [
            {
                'symbol': entry['symbol'],
                'date': entry['date'],
                'data': entry['data']
            }
            for entry in data
        ]

        return success_response(cleaned_data)
    except Exception as e:
        return error_response(f"Failed to retrieve product segmentation for {ticker}: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(get_product_segmentation.tool)
