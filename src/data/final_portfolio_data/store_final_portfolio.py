from __future__ import annotations

"""
Persist ticker-level allocation recommendations (Phase Two output) into our Postgres
`portfolio_results` database.

Behaviour
---------
1. Accept a dict or JSON string that follows the structure produced by
   `make_phaseTwo_recommendations` – see *testing/recentOutput.txt*.
2. Detect the most recent `portfolio_<n>` schema (created earlier by
   `store_portfolio_sector_allocations`) and create/use that schema.  If none
   exists, start with ``portfolio_one``.
3. In that schema create a table ``final_portfolio`` (if it does not already
   exist) with columns:
   • asset_class          VARCHAR
   • ticker               VARCHAR
   • allocation           NUMERIC
   • reason               TEXT
   • supporting_metrics   JSONB
   The composite (asset_class, ticker) acts as primary key to allow idempotent
   re-runs.
4. Bulk-insert / upsert the rows.
"""

import json
from typing import Dict, Any, List, Tuple
import re
from psycopg2 import sql
from psycopg2.extras import execute_values

# Re-use the connection helpers from the sibling module to avoid duplication
from .store_portfolio_sector_allocations import (
    _pg_connect,
    _ensure_database_exists,
    _list_portfolio_schemas,
    _english_word_to_int_map,
    _int_to_english,
)

__all__ = ["store_final_portfolio"]


def store_final_portfolio(portfolio: dict | str) -> str:
    """Store *portfolio* and return the schema name used.

    The function is deliberately symmetric to
    :pyfunc:`store_portfolio_sector_allocations` so that higher-level callers
    can treat them uniformly.
    """

    # ------------------------------------------------------------------
    # 1. Normalise / validate input
    # ------------------------------------------------------------------
    if isinstance(portfolio, str):
        try:
            portfolio_dict: Dict[str, Any] = json.loads(portfolio)
        except json.JSONDecodeError as err:
            raise ValueError("`portfolio` string is not valid JSON") from err
    elif isinstance(portfolio, dict):
        portfolio_dict = portfolio
    else:
        raise TypeError("`portfolio` must be dict or JSON str, got %s" % type(portfolio).__name__)

    if not portfolio_dict:
        raise ValueError("Portfolio payload is empty – nothing to persist")

    # ------------------------------------------------------------------
    # 2. Flatten the nested structure into rows
    # ------------------------------------------------------------------
    rows: List[Tuple[str, str, float, str, str]] = []

    for asset_class, info in portfolio_dict.items():
        # Skip entries that are not dicts or contain error message only
        if not isinstance(info, dict):
            continue

        recs = info.get("recommendations", [])
        if not recs:
            # skip asset_class with no recommendations (maybe contains 'error')
            continue

        for rec in recs:
            ticker = rec.get("ticker")
            if not ticker:
                continue  # malformed entry

            allocation = rec.get("allocation")
            # Convert allocation to float if possible
            try:
                allocation = float(allocation) if allocation is not None else None
            except (ValueError, TypeError):
                allocation = None

            reason = rec.get("reason_for_recommendation") or rec.get("reason") or ""
            metrics_json = json.dumps(rec.get("supporting_metrics", {}))

            rows.append((asset_class, ticker, allocation, reason, metrics_json))

    if not rows:
        raise ValueError("No recommendation rows found in portfolio payload")

    # ------------------------------------------------------------------
    # 3. DB prep – ensure database & find/latest schema
    # ------------------------------------------------------------------
    target_db = "portfolio_results"
    _ensure_database_exists(target_db)

    with _pg_connect(target_db) as conn:
        existing = _list_portfolio_schemas(conn)

        pattern = re.compile(r"^portfolio_([a-z_]+)$", re.IGNORECASE)
        english_to_num = _english_word_to_int_map()

        max_num = 0
        for sch in existing:
            m = pattern.match(sch)
            if m:
                num = english_to_num.get(m.group(1).lower(), 0)
                max_num = max(max_num, num)

        if max_num == 0:
            # No schema yet → create first one here so both sector & final live together
            schema_name = "portfolio_one"
            # also create schema so sector function isn't required beforehand
            with conn.cursor() as cur:
                cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {};").format(sql.Identifier(schema_name)))
        else:
            schema_name = f"portfolio_{_int_to_english(max_num)}"  # latest

        # ------------------------------------------------------------------
        # 4. Create table & insert data (no upsert)
        # ------------------------------------------------------------------
        table = "final_portfolio"
        with conn.cursor() as cur:
            create_sql = sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {schema}.{table} (
                    id SERIAL PRIMARY KEY,
                    asset_class       VARCHAR(255),
                    ticker            VARCHAR(32),
                    allocation        NUMERIC(10,3),
                    reason            TEXT,
                    supporting_metrics JSONB
                );
                """
            ).format(schema=sql.Identifier(schema_name), table=sql.Identifier(table))
            cur.execute(create_sql)

            insert_sql = sql.SQL(
                """
                INSERT INTO {schema}.{table}
                (asset_class, ticker, allocation, reason, supporting_metrics)
                VALUES %s;
                """
            ).format(schema=sql.Identifier(schema_name), table=sql.Identifier(table))

            execute_values(cur, insert_sql.as_string(conn), rows)
            conn.commit()

    return schema_name


if __name__ == "__main__":
    # rudimentary CLI test – run `python -m src.data.final_portfolio_data.store_final_portfolio <path_to_json>`
    portfolio = {
        "semiconductors": {
            "total_stocks_analyzed": 7,
            "recommendations": [
            {
                "ticker": "NVDA",
                "reason_for_recommendation": "NVDA offers exceptional growth potential with strong risk-adjusted returns (Sharpe 1.12, Sortino 1.84) and robust forward EPS estimates (up to $9.47 by Q4 2027). Despite high volatility (beta 2.2), its improving profitability (gross margin 78%) and alignment with medium-term growth goals justify inclusion for a medium-risk investor seeking high growth.",
                "supporting_metrics": {
                "annualized_return": 0.9065,
                "estimated_eps_growth_trend": "Positive"
                },
                "allocation": 4.9
            },
            {
                "ticker": "AVGO",
                "reason_for_recommendation": "AVGO balances growth and income potential with a high annualized return (56.76%) and strong free cash flow growth. Its forward EPS estimates show consistent improvement (up to $2.51 by Q4 2027), and moderate volatility (beta 1.58) aligns with medium risk tolerance. Recent deleveraging (D/E 1.45) and gross margin resilience (69%) support stability.",
                "supporting_metrics": {
                "sharpe_ratio": 0.99,
                "annualized_volatility": 0.42
                },
                "allocation": 4.9
            }
            ]
        },
        "broad_based_emerging_market_equity_etfs": {
            "total_stocks_analyzed": 4,
            "recommendations": [
            {
                "ticker": "SCHE",
                "reason_for_recommendation": "While all emerging market ETFs show negative recent returns, SCHE demonstrates relatively stronger momentum (7.63% 12-month momentum vs peers) and the lowest annualized volatility among higher momentum options. Its active management strategy may better navigate emerging market volatility while aligning with the user's medium-term growth focus. The beta of 0.67 provides moderate market correlation suitable for medium risk tolerance.",
                "supporting_metrics": {
                "momentum_12m": 0.0763,
                "beta": 0.67,
                "max_drawdown": -0.36
                },
                "allocation": 3.9
            },
            {
                "ticker": "VHO",
                "reason_for_recommendation": "VWO offers the lowest downside capture (66% vs market) and beta (0.61) in the group, providing relative stability for medium-risk growth seeking. Despite negative returns, its -2.46% annualized return is the least negative among peers, suggesting better capital preservation. The 6.33% 12-month momentum shows improving trajectory for a 5-year horizon.",
                "supporting_metrics": {
                "downside_capture": 0.66,
                "beta": 0.61,
                "momentum_12m": 0.0633
                },
                "allocation": 3.9
            }
            ]
        },
        "data_center_reits": {
            "total_stocks_analyzed": 2,
            "recommendations": [
            {
                "ticker": "EQIX",
                "reason_for_recommendation": "EQIX offers the best balance of growth potential and risk alignment for a medium-term horizon. It demonstrates stable gross margins (47-50%), improving operating margins (21% in 2024), and strong forward EPS growth estimates (projected to rise from 3.28 to 4.06 by 2026). While leverage is elevated (D/E ~1.59), its moderate beta (0.9), lower downside capture (0.92 vs market), and superior risk-adjusted returns (Sharpe 0.2 vs DLR's 0.09) align well with medium risk tolerance. The 8.79% annualized return and improving EBITD estimates (+22% by 2027) support the 'medium-term high growth' objective.",
                "supporting_metrics": {
                "annualized_return": "8.79%",
                "forward_eps_growth": "24% (2025-2026)",
                "beta": 0.9,
                "downside_capture": 0.92
                },
                "allocation": 6.9
            }
            ]
        },
        "multi_utilities": {
            "total_stocks_analyzed": 8,
            "recommendations": [
            {
                "ticker": "CNP",
                "reason_for_recommendation": "CNP offers the best combination of risk-adjusted returns (Sharpe 0.50, Sortino 0.71) and growth potential for a medium-term horizon. Its 14.34% annualized return and moderate beta (0.48) align with medium risk tolerance. While historical cash flow challenges exist, forward EPS estimates show growth (e.g., Q3 2027 EPS 0.55 vs. Q2 2025 0.40) and improving margins suggest operational progress. The 32.41% 12-month momentum indicates strong market confidence.",
                "supporting_metrics": {
                "sharpe_ratio": 0.5,
                "annualized_return": 0.1434,
                "estimated_eps_growth_trend": "Positive"
                },
                "allocation": 2.3
            },
            {
                "ticker": "ED",
                "reason_for_recommendation": "ED provides exceptional downside protection (beta 0.24, downside capture 0.16) while delivering 11.63% annualized returns. Its utility sector stability matches medium-term wealth preservation needs, and improving liquidity metrics (current ratio >1.0 recently) address historical concerns. The 0.64 Sortino ratio demonstrates efficient management of downside risk, and Q2 2025-Q4 2027 EPS estimates show gradual growth (0.66 to 1.27).",
                "supporting_metrics": {
                "beta": 0.24,
                "sortino_ratio": 0.64,
                "downside_capture": 0.16
                },
                "allocation": 2.3
            },
            {
                "ticker": "NI",
                "reason_for_recommendation": "NI presents a growth complement with 13.04% annualized returns and strong momentum (38.76% 12-month). While leverage is high, robust gross margins (59-85%) and Q1 2026 EPS estimate of 0.96 suggest growth potential. Medium-risk tolerance accommodates its 0.5 beta, and the 0.62 Sortino ratio indicates acceptable downside management for the projected returns.",
                "supporting_metrics": {
                "annualized_return": 0.1304,
                "momentum_12m": 0.3876,
                "gross_margin_range": "59-85%"
                },
                "allocation": 2.3
            }
            ]
        },
        "investment_grade_corporate_bond_etfs": {
            "total_stocks_analyzed": 5,
            "recommendations": [
            {
                "ticker": "VCIT",
                "reason_for_recommendation": "Best balance of risk-adjusted returns and growth potential among corporate bond ETFs. Shows the strongest 12-month momentum (+4.23%) and lowest annualized volatility (7%) in its category, aligning with medium-term growth goals. While historical returns are negative (likely due to recent rate hikes), its intermediate-term focus (5-10 year maturities) positions it for potential recovery as rates stabilize.",
                "supporting_metrics": {
                "annualized_return": -0.0315,
                "beta": 0.14,
                "momentum_12m": 0.0423,
                "downside_capture": 0.17
                },
                "allocation": 3.45
            },
            {
                "ticker": "IGSB",
                "reason_for_recommendation": "Provides stability with minimal volatility (3% annualized) and near-flat returns (-0.01%) in challenging bond markets. Its ultra-low beta (0.06) and smallest drawdown (-11%) make it suitable for the income portion of the strategy. Short duration (1-5 year maturities) reduces interest rate risk while maintaining investment-grade credit quality.",
                "supporting_metrics": {
                "annualized_volatility": 0.03,
                "max_drawdown": -0.11,
                "beta": 0.06
                },
                "allocation": 3.45
            }
            ]
        },
        "industrial_metals": {
            "total_stocks_analyzed": 2,
            "recommendations": [
            {
                "ticker": "CPER",
                "reason_for_recommendation": "CPER offers exposure to copper futures with moderate growth potential aligned with a 5-year horizon. While it doesn't provide income, its lower beta (0.56) and volatility (25% annualized) suit medium risk tolerance. Positive 6-month momentum (+4.45%) and copper's role in green energy infrastructure support medium-term growth potential. The -35% max drawdown requires monitoring but is acceptable for medium-risk investors.",
                "supporting_metrics": {
                "beta": 0.56,
                "momentum_6m": 0.0445,
                "annualized_return": 0.0386
                },
                "allocation": 5.9
            }
            ]
        },
        "pharmaceuticals": {
            "total_stocks_analyzed": 7,
            "recommendations": [
            {
                "ticker": "LLY",
                "reason_for_recommendation": "LLY (Eli Lilly) offers strong alignment with medium-term growth objectives, combining robust risk-adjusted returns (Sharpe 1.34) with improving fundamentals. Analysts project significant EPS growth (2026 Q4 estimate: 8.35) driven by pipeline expansion, while reduced debt-to-equity (4-5x) and stable 82%+ gross margins provide fundamental support. Moderate beta (0.61) and low volatility (31% annualized) suit medium risk tolerance.",
                "supporting_metrics": {
                "sharpe_ratio": 1.34,
                "estimated_eps_growth_2025-2026": "48% (5.56 to 8.35)",
                "debt-to-equity_trend": "Improved from 14.29 (2019) to 4-5x (2024)"
                },
                "allocation": 2.95
            },
            {
                "ticker": "AMRX",
                "reason_for_recommendation": "AMRX presents high growth potential with exceptional risk-adjusted returns (Sharpe 1.74, Sortino 3.13) and positive EPS estimates trending upward (0.18 to 0.23 in 2025). While historical fundamentals show weakness, projected 39% gross margins and 785M+ quarterly revenue by 2025 Q3 suggest operational improvement. Suitable for medium-risk investors willing to accept speculative aspects for growth.",
                "supporting_metrics": {
                "sortino_ratio": 3.13,
                "forward_eps_growth": "28% (2025 Q2 to Q3)",
                "sector_upside_capture": 1.52
                },
                "allocation": 2.95
            }
            ]
        },
        "broad_us_market": {
            "total_stocks_analyzed": 5,
            "recommendations": [
            {
                "ticker": "VTI",
                "reason_for_recommendation": "Best combination of growth potential and risk management for medium-term goals. Strongest risk-adjusted returns (Sharpe 0.76, Sortino 0.99) with below-market volatility (16% annualized) and moderate beta (0.99). The -19% max drawdown shows better capital preservation than peers, aligning well with medium risk tolerance while still delivering 16.3% annualized returns.",
                "supporting_metrics": {
                "sharpe_ratio": 0.76,
                "annualized_return": 0.163,
                "max_drawdown": -0.19
                },
                "allocation": 2.95
            },
            {
                "ticker": "QQQ",
                "reason_for_recommendation": "Provides growth exposure to Nasdaq-100 tech leaders with 11.8% annualized returns, suitable for the 'medium term high growth' objective. While more volatile (beta 1.25), its 1.28 upside capture ratio shows strong participation in market gains. Recent momentum improvement (-4.88% 6m vs -11.39% for IWM) suggests relative strength recovery.",
                "supporting_metrics": {
                "annualized_return": 0.1182,
                "upside_capture": 1.28,
                "momentum_6m": -0.0488
                },
                "allocation": 2.95
            }
            ]
        },
        "electric_utilities": {
            "total_stocks_analyzed": 7,
            "recommendations": [
            {
                "ticker": "NRG",
                "reason_for_recommendation": "NRG offers the strongest growth potential aligned with the user's medium-term high growth objective. It demonstrates superior risk-adjusted returns (Sharpe Ratio: 0.86, highest among peers) and robust momentum (12m: 47.6%). Forward EPS estimates show consistent growth (1.78 \u2192 2.23 by 2027), while moderate sector beta (0.91) balances its market volatility (beta: 1.04) within the user's medium risk tolerance.",
                "supporting_metrics": {
                "sharpe_ratio": 0.86,
                "annualized_return": 0.414,
                "estimated_eps_growth_trend": "Positive (Q2 2025 to Q3 2027)"
                },
                "allocation": 2.45
            },
            {
                "ticker": "ETR",
                "reason_for_recommendation": "ETR provides a balance of growth and stability. It shows improving fundamentals (rising gross margins, reduced debt-to-equity) and strong forward EPS growth (0.89 \u2192 1.64 by 2026). With moderate volatility (beta: 0.47) and attractive risk-adjusted returns (Sortino: 0.62), it aligns well with medium-term growth goals while offering downside protection (downside capture: 0.38).",
                "supporting_metrics": {
                "sortino_ratio": 0.62,
                "momentum_12m": 0.5469,
                "debt-to-equity_trend": "Declining (4.46 \u2192 3.08)"
                },
                "allocation": 2.45
            }
            ]
        },
        "asset_management_and_custody_banks": {
            "total_stocks_analyzed": 7,
            "recommendations": [
            {
                "ticker": "BK",
                "reason_for_recommendation": "BK aligns with medium-term growth goals through improving fundamentals and forward EPS growth (2026 Q4 estimate: 2.05 vs. current 1.73). Moderate beta (0.95) suits medium risk tolerance. Recent stabilization in operating margins (Q3 2024: ~30%) and strong Sharpe (0.44)/Sortino (0.61) ratios show balanced risk-adjusted returns. Debt remains elevated but is typical for banks.",
                "supporting_metrics": {
                "sharpe_ratio": 0.44,
                "estimated_eps_growth_trend": "+19% (2025 Q2 to 2026 Q4)",
                "beta": 0.95
                },
                "allocation": 2.45
            },
            {
                "ticker": "FHI",
                "reason_for_recommendation": "Offers growth potential with 12% annualized return and moderate volatility (beta 0.77). Forward EPS estimates show consistent growth (2026 Q3: 1.08 vs. 2025 Q2: 0.95). Recent FCF improvement (2023-2024) and reasonable valuation (P/E ~11x) balance growth expectations with risk. Matches medium-term horizon with 3-5 year growth trajectory.",
                "supporting_metrics": {
                "annualized_return": 0.1204,
                "estimated_eps_growth_trend": "+14% (2025 Q2 to 2026 Q3)",
                "beta": 0.77
                },
                "allocation": 2.45
            }
            ]
        },
        "renewable_electricity": {
            "total_stocks_analyzed": 7,
            "recommendations": [
            {
                "ticker": "ORA",
                "reason_for_recommendation": "ORA aligns with medium risk tolerance through its below-market volatility (beta 0.76) and stable fundamentals. It shows moderate growth potential with forward EPS estimates rising to 1.04 by 2027, while maintaining reasonable debt levels (debt-to-equity 1.14-1.28). The 4.83% annualized return and low downside capture (84%) provide a balance of growth and stability suitable for a 5-year horizon.",
                "supporting_metrics": {
                "beta": 0.76,
                "annualized_volatility": 0.31,
                "estimated_eps_growth": "Up to 1.04 by Q4 2027"
                },
                "allocation": 1.95
            },
            {
                "ticker": "WAVE",
                "reason_for_recommendation": "WAVE offers high growth potential (94.57% annualized return) with controlled downside risk (Sortino ratio 1.02, downside capture 38%). While unprofitable currently, its low beta (0.32) and improving gross margins (0.15% to 0.86%) suggest emerging efficiency. Projected positive EPS in late 2026 aligns with the user's 5-year timeframe, making it a compelling risk/reward proposition for medium-term growth.",
                "supporting_metrics": {
                "sortino_ratio": 1.02,
                "annualized_return": 0.9457,
                "beta": 0.32
                },
                "allocation": 1.95
            }
            ]
        },
        "packaged_foods_and_meats": {
            "total_stocks_analyzed": 8,
            "recommendations": [
            {
                "ticker": "CALM",
                "reason_for_recommendation": "CALM offers a balanced risk-reward profile with strong fundamentals, moderate volatility (beta 0.38), and improving profitability. Its forward EPS estimates show significant growth (e.g., Q3 2025 EPS estimate of 10.9), aligning with medium-term growth objectives. Strong liquidity (current ratio >3) and low debt (D/E 0.21) provide stability for medium risk tolerance.",
                "supporting_metrics": {
                "sharpe_ratio": 0.74,
                "annualized_return": 0.3254,
                "estimated_eps_growth": "Q3 2025 EPS: 10.9"
                },
                "allocation": 1.3
            },
            {
                "ticker": "MAMA",
                "reason_for_recommendation": "MAMA demonstrates exceptional risk-adjusted returns (Sharpe 1.27, Sortino 2.01) with high annualized return (124.75%). Recent operational improvements and modest forward EPS growth (0.04-0.06) suggest growth potential. Moderate beta (0.67) and manageable drawdown (-43%) suit a medium-risk profile.",
                "supporting_metrics": {
                "calmar_ratio": 2.93,
                "annualized_volatility": 0.62
                },
                "allocation": 1.3
            },
            {
                "ticker": "PPC",
                "reason_for_recommendation": "PPC provides stable growth with improving fundamentals, including reduced leverage (D/E 1.51) and positive FCF. Forward EPS estimates (up to 1.59 in 2025) and moderate volatility (beta 0.54) align well with a 5-year horizon. Recent valuation multiples (P/E ~10) suggest reasonable pricing for medium-term growth.",
                "supporting_metrics": {
                "annualized_return": 0.2842,
                "debt-to-equity": 1.51
                },
                "allocation": 1.3
            }
            ]
        },
        "aerospace_and_defense": {
            "total_stocks_analyzed": 7,
            "recommendations": [
            {
                "ticker": "HWM",
                "reason_for_recommendation": "HWM demonstrates strong risk-adjusted returns (Sharpe 1.2, Sortino 1.81) with improving fundamentals. Its moderate volatility (beta 1.16) aligns with medium risk tolerance, while 51.9% annualized return and low max drawdown (-24%) suit medium-term growth objectives. Analyst estimates show steady EPS growth (0.81 to 1.24 from 2025-2027) and expanding gross margins (31.8% to 34.2%), supported by improving FCF generation and reduced leverage.",
                "supporting_metrics": {
                "sharpe_ratio": 1.2,
                "annualized_return": 0.5192,
                "estimated_eps_growth_trend": "Positive"
                },
                "allocation": 1.3
            },
            {
                "ticker": "TATT",
                "reason_for_recommendation": "TATT offers exceptional returns (74.5% annualized) with below-market volatility (beta 0.52). Recent fundamental improvements include stabilized 6-8% net margins and 22% gross margins, supported by 12-month momentum of 138%. Analyst EPS estimates show 31-48\u00a2 growth through 2026. Low downside capture (25%) provides protection during market declines, aligning well with medium-term growth objectives while managing risk exposure.",
                "supporting_metrics": {
                "sortino_ratio": 1.87,
                "beta": 0.52,
                "momentum_12m": 1.3802
                },
                "allocation": 1.3
            },
            {
                "ticker": "DRS",
                "reason_for_recommendation": "DRS combines improving financial health (current ratio 2.11, debt-to-equity 0.56) with 50.1% annualized return. Moderate beta (0.89) and 88% downside capture provide stability, while analyst SREV estimates project 24% growth from 2025-Q2 to 2026-Q4. Recent stabilization in margins (23-24% gross) and EPS growth aligns with medium-term horizon requirements, though investors should monitor cash flow consistency.",
                "supporting_metrics": {
                "annualized_volatility": 0.43,
                "estimated_revenue_growth": "24% over 18 months",
                "debt_to_equity": 0.56
                },
                "allocation": 1.3
            }
            ]
        },
        "precious_metals_etfs": {
            "total_stocks_analyzed": 5,
            "recommendations": [
            {
                "ticker": "IAU",
                "reason_for_recommendation": "IAU (iShares Gold Trust) demonstrates strong risk-adjusted returns with a Sharpe ratio of 0.91 and Sortino ratio of 1.37, aligning well with medium risk tolerance. Its low beta (0.13) and downside capture (0.04) provide stability, while 17.52% annualized return supports medium-term growth objectives. Gold's historical role as a hedge adds portfolio diversification benefits.",
                "supporting_metrics": {
                "annualized_return": "17.52%",
                "beta": 0.13,
                "downside_capture": 0.04
                },
                "allocation": 1.95
            },
            {
                "ticker": "GLD",
                "reason_for_recommendation": "SPDR Gold Shares offers nearly identical characteristics to IAU with slightly lower returns (17.32% vs 17.52%) but similar stability profile. Its 0.9 Sharpe ratio and minimal downside capture (0.05) make it a complementary conservative growth holding for a 5-year horizon, particularly given gold's inflation-hedging properties.",
                "supporting_metrics": {
                "annualized_return": "17.32%",
                "max_drawdown": -0.21,
                "upside_capture": 0.2
                },
                "allocation": 1.95
            }
            ]
        },
        "treasury_and_inflation_bond_etfs": {
            "total_stocks_analyzed": 5,
            "recommendations": [
            {
                "ticker": "SCHP",
                "reason_for_recommendation": "While all bond ETFs show negative returns in this dataset, SCHP demonstrates relatively better momentum (1.86% 6-month return vs peers) and the strongest upside capture ratio (0.07) among Treasury ETFs. Its TIPS exposure provides some inflation protection which aligns with medium-term growth objectives in uncertain rate environments. The -3.34% annualized return is less severe than longer-duration alternatives like TLT (-9.13%).",
                "supporting_metrics": {
                "momentum_6m": 0.0186,
                "downside_capture": 0.12,
                "annualized_volatility": 0.07
                },
                "allocation": 1.95
            },
            {
                "ticker": "SHY",
                "reason_for_recommendation": "Offers the lowest volatility (2% annualized) and smallest max drawdown (-7%), making it the most stable option for medium-risk tolerance. While returns are minimal (-0.92% annualized), its ultra-short duration (1-3 year Treasuries) provides income stability and protects against rate hikes. Aligns with the 'some income' requirement while maintaining capital preservation characteristics.",
                "supporting_metrics": {
                "annualized_volatility": 0.02,
                "max_drawdown": -0.07,
                "beta": 0.01
                },
                "allocation": 1.95
            }
            ]
        },
        "health_care_equipment": {
            "total_stocks_analyzed": 7,
            "recommendations": [
            {
                "ticker": "BSX",
                "reason_for_recommendation": "BSX aligns well with medium-term growth goals, offering a balance of stability and growth potential. It demonstrates moderate volatility (beta 0.75), improving debt management, and strong forward EPS growth projections (0.72 to 0.98 by 2026). The Sharpe ratio of 0.92 and Sortino ratio of 1.26 indicate solid risk-adjusted returns. Analyst estimates show consistent revenue and EBITDA growth, supporting its position in the medical devices sector with defensive characteristics.",
                "supporting_metrics": {
                "sharpe_ratio": 0.92,
                "estimated_eps_growth": "36% (2025-2026)",
                "debt-to-equity": 0.79
                },
                "allocation": 0.97
            },
            {
                "ticker": "IRMD",
                "reason_for_recommendation": "IRMD provides strong profitability (28% net margin) and financial health (current ratio 9.21) with moderate beta (0.9). While revenue growth has slowed, stable EPS estimates (0.43-0.47) and high gross margins (76%) suggest resilience. Its low debt-to-equity (0.29) and improved cash flow generation make it suitable for medium-term growth with reduced downside risk.",
                "supporting_metrics": {
                "net_margin": 28,
                "current_ratio": 9.21,
                "debt-to-equity": 0.29
                },
                "allocation": 0.97
            },
            {
                "ticker": "ELMD",
                "reason_for_recommendation": "ELMD offers lower volatility (beta 0.41) and strong gross margins (75-78%) with conservative leverage (debt-to-equity 0.22). While growth is inconsistent, forward EPS estimates show 41% growth (0.22 to 0.31 by 2026) and improved FCF generation. Its downside capture of 0.16 provides protection during market declines, aligning with medium risk tolerance.",
                "supporting_metrics": {
                "beta": 0.41,
                "estimated_eps_growth": "41% (2025-2026)",
                "downside_capture": 0.16
                },
                "allocation": 0.97
            }
            ]
        },
        "broadline_retail": {
            "error": "LLM response was not valid JSON."
        },
        "insurance_brokers": {
            "total_stocks_analyzed": 7,
            "recommendations": [
            {
                "ticker": "AJG",
                "reason_for_recommendation": "AJG aligns well with medium-term growth goals, offering a balance of moderate volatility (beta 0.67) and strong forward-looking EPS growth (projected to rise from 2.38 in Q2 2025 to 4.97 in Q1 2027). Its improving free cash flow and 24.17% annualized return provide growth potential, while sector beta (0.63) and downside capture (0.53) add defensive characteristics suitable for medium risk tolerance.",
                "supporting_metrics": {
                "sharpe_ratio": 0.88,
                "annualized_return": "24.17%",
                "estimated_eps_growth_trend": "Positive",
                "beta": 0.67
                },
                "allocation": 1.45
            },
            {
                "ticker": "BRO",
                "reason_for_recommendation": "BRO demonstrates consistent growth potential with 22.78% annualized return and moderate volatility (beta 0.74). Its improving free cash flow per share (up to $1.47 in recent quarters) and projected EPS growth (1.03 to 1.57 by 2027) support medium-term objectives. The Sortino ratio (0.89) indicates good downside risk management, aligning with medium risk tolerance.",
                "supporting_metrics": {
                "sortino_ratio": 0.89,
                "annualized_return": "22.78%",
                "debt-to-equity_trend": "Moderating (1.74 in Q4 2024)",
                "momentum_12m": "31.18%"
                },
                "allocation": 1.45
            }
            ]
        }
    }

    store_final_portfolio(portfolio)
