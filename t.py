"""Verify all tools_v2 tools load and have valid .tool schemas."""

from app.core.atlas.tools_v2.research.macro_research import macro_research
from app.core.atlas.tools_v2.research.earnings_calls import earnings_call_search
from app.core.atlas.tools_v2.research.user_uploads import user_upload_search
from app.core.atlas.tools_v2.research.tax_research import tax_research_search
from app.core.atlas.tools_v2.research.credit_research import credit_research_search
from app.core.atlas.tools_v2.research.economics_research import economics_research_search

from app.core.atlas.tools_v2.ticker.fundamentals.statements import get_ticker_fundamental_data
from app.core.atlas.tools_v2.ticker.fundamentals.ttm_ratios import get_ratios_ttm
from app.core.atlas.tools_v2.ticker.fundamentals.estimates import get_analyst_estimates
from app.core.atlas.tools_v2.ticker.fundamentals.price_target import get_price_target_data

from app.core.atlas.tools_v2.ticker.info.description import get_ticker_info
from app.core.atlas.tools_v2.ticker.info.ratings import get_stock_ratings
from app.core.atlas.tools_v2.ticker.info.peers import get_ticker_peers
from app.core.atlas.tools_v2.ticker.info.product_segmentation import get_product_segmentation

ALL_TOOLS = [
    macro_research,
    earnings_call_search,
    user_upload_search,
    tax_research_search,
    credit_research_search,
    economics_research_search,
    get_ticker_fundamental_data,
    get_ratios_ttm,
    get_analyst_estimates,
    get_price_target_data,
    get_ticker_info,
    get_stock_ratings,
    get_ticker_peers,
    get_product_segmentation,
]

for tool_fn in ALL_TOOLS:
    t = tool_fn.tool
    assert "name" in t, f"{tool_fn.__name__} missing 'name'"
    assert "description" in t, f"{tool_fn.__name__} missing 'description'"
    assert "parameters" in t, f"{tool_fn.__name__} missing 'parameters'"
    assert "function" in t, f"{tool_fn.__name__} missing 'function'"
    assert callable(t["function"]), f"{tool_fn.__name__} function not callable"
    print(f"  {t['name']:40s} params={list(t['parameters'].get('properties', {}).keys())}")

print(f"\nAll {len(ALL_TOOLS)} tools loaded successfully.")
