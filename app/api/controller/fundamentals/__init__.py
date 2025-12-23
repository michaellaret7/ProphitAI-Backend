"""Fundamentals controller functions."""

from .estimates import (
    get_analyst_estimates_controller,
    get_earnings_calls_transcripts_controller,
)
from .ratings import (
    get_analyst_recommendations_controller,
    get_price_target_summary_controller,
    get_price_target_consensus_controller,
    get_stock_grades_individual_controller,
    get_stock_grades_summary_controller,
    get_ratings_controller,
)
from .company import (
    get_stock_peers_controller,
    get_esg_disclosures_controller,
    get_revenue_product_segmentation_controller,
    get_revenue_geographic_segmentation_controller,
    get_institutional_holder_analytics_controller,
    get_institutional_positions_summary_controller,
    get_company_notes_controller,
)

__all__ = [
    # Estimates
    "get_analyst_estimates_controller",
    "get_earnings_calls_transcripts_controller",
    # Ratings
    "get_analyst_recommendations_controller",
    "get_price_target_summary_controller",
    "get_price_target_consensus_controller",
    "get_stock_grades_individual_controller",
    "get_stock_grades_summary_controller",
    "get_ratings_controller",
    # Company
    "get_stock_peers_controller",
    "get_esg_disclosures_controller",
    "get_revenue_product_segmentation_controller",
    "get_revenue_geographic_segmentation_controller",
    "get_institutional_holder_analytics_controller",
    "get_institutional_positions_summary_controller",
    "get_company_notes_controller",
]
