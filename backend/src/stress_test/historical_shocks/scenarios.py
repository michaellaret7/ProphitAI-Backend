"""
Stress test scenario definitions.
"""

# Historical stress scenario date ranges
STRESS_SCENARIOS = {
    'trump_tariff_crash': {
        'start_date': '2025-04-02',
        'end_date': '2025-04-05',
        'description': 'Trump tariff announcement market crash'
    },
    'tariff_pause_relief_rally': {
        'start_date': '2025-04-08',
        'end_date': '2025-04-10',
        'description': 'Relief rally after tariff pause announcement'
    },
    'svb_bank_collapse': {
        'start_date': '2023-03-09',
        'end_date': '2023-03-13',
        'description': 'Silicon Valley Bank collapse'
    },
    'hot_cpi_shock': {
        'start_date': '2022-09-12',
        'end_date': '2022-09-14',
        'description': 'Hot CPI print market shock'
    },
    'powell_hawkish_jackson_hole_speech': {
        'start_date': '2022-08-25',
        'end_date': '2022-08-27',
        'description': 'Powell hawkish Jackson Hole speech'
    },
    'japan_nikkei_black_monday': {
        'start_date': '2024-08-05',
        'end_date': '2024-08-07',
        'description': 'Japan Nikkei Black Monday crash'
    }
}