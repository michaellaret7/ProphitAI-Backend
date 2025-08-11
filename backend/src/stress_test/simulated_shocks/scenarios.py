# Hypothetical Scenarios - Dictionary format for easy programmatic access
hypothetical_scenarios = {
    'stagflation_scenario': {
        'SPY': -0.10,   
        'USO': 0.50,
        'TLT': -0.15,
        'DBA': 0.30,
    },
    
    'energy_supply_shock': {
        'USO':  0.30,   # Crude oil spike
        'XLE':  0.15,   # Energy equities benefit
        'SPY': -0.10,   # Broad equities hit by cost shock
        'TLT': -0.05,   # Long Treasuries pressured by higher inflation expectations
    },
    
    'credit_crunch_banking_stress': {
        'XLF': -0.15,   # Regional banks under pressure
        'HYG': -0.10,   # HY credit selloff (wider spreads)
        'LQD': -0.05,   # IG credit weaker
        'TLT':  0.05,   # Flight-to-quality into Treasuries
    },
    
    'fed_overtightening': {
        'SPY': -0.08,    # S&P 500 - moderate correction
        'QQQ': -0.12,    # Tech - rate sensitive
        'TLT': -0.06,    # Long bonds - higher rates
        'IWM': -0.10,    # Small caps - liquidity concerns
        'XLRE': -0.15,   # Real estate - rate sensitive
        'XLF': 0.04      # Financials - benefit from rates
    },
    
    'sticky_inflation': {
        'TIP': 0.06,     # TIPS - inflation protection
        'XLE': 0.12,     # Energy - inflation beneficiary
        'GLD': 0.08,     # Gold - inflation hedge
        'TLT': -0.10,    # Long bonds - real yield concerns
        'XLK': -0.12,    # Tech - multiple compression
        'XLP': 0.03      # Consumer staples - pricing power
    },
    
    'credit_stress': {
        'HYG': -0.08,    # High yield - spreads widen
        'LQD': -0.05,    # Investment grade - mild impact
        'SPY': -0.10,    # Equities - risk-off sentiment
        'XLF': -0.12,    # Financials - credit concerns
        'IEF': 0.04,     # Intermediate treasuries - quality bid
    },
}

# Historical Scenarios - Individual variables for consistency with existing code
historical_scenarios = {
    'trump_tariff_crash': {
        'VIXY': 0.3865,
        'USO': -0.1318,
        'XLF': -0.1248,
        'QQQ': -0.1208,
        'SPY': -0.1117,
        'XLU': -0.0610,
        'HYG': -0.0269,
        'GLD': -0.0255,
        'TLT': 0.0206,
        'UUP': -0.0081,
        'start_date': '2025-04-02',
        'end_date': '2025-04-05',
    },
    'svb_bank_collapse': {
        'VIXY': 0.0895,
        'TLT': 0.0338,
        'GLD': 0.0204,
        'XLF': -0.0173,
        'XLU': -0.0160,
        'SPY': -0.0135,
        'QQQ': -0.0133,
        'USO': 0.0124,
        'UUP': -0.0056,
        'HYG': -0.0005,

        'start_date': '2023-03-09',
        'end_date': '2023-03-13',
    },
    'tariff_pause_relief_rally': {
        'VIXY': -0.2412,
        'QQQ': 0.1162,
        'SPY': 0.0938,
        'XLF': 0.0708,
        'USO': 0.0653,
        'XLU': 0.0427,
        'GLD': 0.0367,
        'HYG': 0.0257,
        'TLT': 0.0040,
        'UUP': 0.0016,

        'start_date': '2025-04-08',
        'end_date': '2025-04-10',
    },
    'hot_cpi_shock': {
        'VIXY': 0.0940,
        'QQQ': -0.0564,
        'SPY': -0.0427,
        'XLF': -0.0372,
        'XLU': -0.0266,
        'HYG': -0.0226,
        'UUP': 0.0148,
        'GLD': -0.0130,
        'USO': -0.0050,
        'TLT': 0.0020,

        'start_date': '2022-09-12',
        'end_date': '2022-09-14',
    },
    'powell_hawkish_jackson_hole_speech': {
        'VIXY': 0.0973,
        'QQQ': -0.0402,
        'SPY': -0.0324,
        'XLF': -0.0311,
        'HYG': -0.0165,
        'XLU': -0.0156,
        'GLD': -0.0115,
        'TLT': 0.0087,
        'USO': -0.0069,
        'UUP': 0.0041,

        'start_date': '2022-08-25',
        'end_date': '2022-08-27',
    },
    'japan_nikkei_black_monday': {
        'VIXY': -0.2035,
        'TLT': -0.0192,
        'USO': -0.0120,
        'XLF': 0.0117,
        'XLU': 0.0093,
        'GLD': -0.0074,
        'SPY': 0.0066,
        'QQQ': 0.0053,
        'HYG': 0.0038,
        'UUP': 0.0032,

        'start_date': '2024-08-05',
        'end_date': '2024-08-07',
    },
}