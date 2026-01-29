"""Sector mapping constants for converting between internal and FMP sector names.

This module provides the canonical sector name mappings used across all sector-related tools.
Following DRY principle - this is the single source of truth for sector name conversions.
"""

# Internal format → FMP API format
SECTOR_MAPPING = {
    'equity_sector_information_technology': 'Technology',
    'equity_sector_health_care': 'Healthcare',
    'equity_sector_financials': 'Financial Services',
    'equity_sector_consumer_discretionary': 'Consumer Cyclical',
    'equity_sector_consumer_staples': 'Consumer Defensive',
    'equity_sector_industrials': 'Industrials',
    'equity_sector_communication_services': 'Communication Services',
    'equity_sector_energy': 'Energy',
    'equity_sector_materials': 'Basic Materials',
    'equity_sector_utilities': 'Utilities',
    'equity_sector_real_estate': 'Real Estate'
}

# FMP API format → Internal format (reverse mapping)
FMP_TO_EQUITY_SECTOR = {
    'Technology': 'equity_sector_information_technology',
    'Healthcare': 'equity_sector_health_care',
    'Financial Services': 'equity_sector_financials',
    'Consumer Cyclical': 'equity_sector_consumer_discretionary',
    'Consumer Defensive': 'equity_sector_consumer_staples',
    'Industrials': 'equity_sector_industrials',
    'Communication Services': 'equity_sector_communication_services',
    'Energy': 'equity_sector_energy',
    'Basic Materials': 'equity_sector_materials',
    'Utilities': 'equity_sector_utilities',
    'Real Estate': 'equity_sector_real_estate'
}
