"""Fundamental statement processing and retrieval functions.

Higher-level functions that build on the base fetchers to provide
filtered, formatted fundamental data for specific statement types.
"""

from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional, Literal, List

from app.repositories.fundamentals.fetchers import get_fundamentals_raw


def _filter_by_cutoff(statements: List, cutoff_date: date) -> List:
    """Filter statements to only include those on or before cutoff_date.

    Args:
        statements: List of statement objects with 'date' attribute
        cutoff_date: Date object representing the cutoff

    Returns:
        Filtered list of statements
    """
    if not statements:
        return []
    filtered = []
    for s in statements:
        if not hasattr(s, 'date') or s.date is None:
            continue
        # s.date is datetime.date from SQLAlchemy Date column
        if s.date <= cutoff_date:
            filtered.append(s)
    return filtered


def _serialize_sa_model(instance: Any) -> Dict[str, Any]:
    """Serialize a SQLAlchemy model instance to a JSON-ready dict with all columns.

    - Includes every column present on the model table
    - Converts Decimal to float
    - Converts date/datetime to ISO string
    """
    data: Dict[str, Any] = {}
    # Fallback if instance doesn't expose __table__
    columns = getattr(getattr(instance, "__table__", None), "columns", None)
    if columns is None:
        # best-effort: include public attrs only
        for key, value in instance.__dict__.items():
            if key.startswith("_"):
                continue
            if isinstance(value, (datetime, date)):
                data[key] = str(value)
            elif isinstance(value, Decimal):
                data[key] = float(value)
            else:
                data[key] = float(value) if isinstance(value, (int, float)) else value
        return data

    for col in columns:
        name = col.name
        value = getattr(instance, name, None)
        if value is None:
            data[name] = None
            continue
        if isinstance(value, (datetime, date)):
            data[name] = str(value)
        elif isinstance(value, Decimal):
            data[name] = float(value)
        else:
            data[name] = value
    return data

def get_fundamental_data(
    ticker: str,
    statement_type: Literal["income_statement", "balance_sheet", "cash_flow", "financial_ratios", "analyst_estimates"],
    quarters_back: int = 1,
    _simulation_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Retrieve fundamental data from the database for a given ticker.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        statement_type: Type of fundamental data to retrieve
        quarters_back: Number of quarters of historical data to retrieve (1 = most recent only)
        _simulation_date: INTERNAL USE ONLY - For simulation mode, only return data on or before this date

    Returns:
        Dictionary containing the requested fundamental data
    """
    try:
        # Fetch fundamental data directly from database
        fundamentals = get_fundamentals_raw(ticker.upper())

        result = {
            "ticker": ticker.upper(),
            "statement_type": statement_type,
            "quarters_requested": quarters_back,
            "data": []
        }

        # Get the appropriate statement list based on type
        if statement_type == "income_statement":
            statements = fundamentals.income_statements if fundamentals.income_statements else []

            # Filter by simulation date if provided (simulation mode)
            if _simulation_date is not None:
                statements = _filter_by_cutoff(statements, _simulation_date.date())

            # Slice for quarters_back
            statements = statements[:quarters_back]

            for stmt in statements:
                period_data = {
                    "date": str(stmt.date) if hasattr(stmt, 'date') else None,
                    "revenue": float(stmt.revenue) if hasattr(stmt, 'revenue') and stmt.revenue else None,
                    "gross_profit": float(stmt.grossProfit) if hasattr(stmt, 'grossProfit') and stmt.grossProfit else None,
                    "operating_income": float(stmt.operatingIncome) if hasattr(stmt, 'operatingIncome') and stmt.operatingIncome else None,
                    "net_income": float(stmt.netIncome) if hasattr(stmt, 'netIncome') and stmt.netIncome else None,
                    "ebitda": float(stmt.ebitda) if hasattr(stmt, 'ebitda') and stmt.ebitda else None,
                    "eps": float(stmt.eps) if hasattr(stmt, 'eps') and stmt.eps else None,
                    "diluted_eps": float(stmt.epsdiluted) if hasattr(stmt, 'epsdiluted') and stmt.epsdiluted else None,
                    "shares_outstanding": float(stmt.weightedAverageShsOut) if hasattr(stmt, 'weightedAverageShsOut') and stmt.weightedAverageShsOut else None,
                    "shares_outstanding_diluted": float(stmt.weightedAverageShsOutDil) if hasattr(stmt, 'weightedAverageShsOutDil') and stmt.weightedAverageShsOutDil else None,
                }
                result["data"].append(period_data)

        elif statement_type == "balance_sheet":
            statements = fundamentals.balance_sheets if fundamentals.balance_sheets else []

            # Filter by simulation date if provided (simulation mode)
            if _simulation_date is not None:
                statements = _filter_by_cutoff(statements, _simulation_date.date())

            # Slice for quarters_back
            statements = statements[:quarters_back]

            for stmt in statements:
                period_data = {
                    "date": str(stmt.date) if hasattr(stmt, 'date') else None,
                    "total_assets": float(stmt.totalAssets) if hasattr(stmt, 'totalAssets') and stmt.totalAssets else None,
                    "total_liabilities": float(stmt.totalLiabilities) if hasattr(stmt, 'totalLiabilities') and stmt.totalLiabilities else None,
                    "total_equity": float(stmt.totalStockholdersEquity) if hasattr(stmt, 'totalStockholdersEquity') and stmt.totalStockholdersEquity else None,
                    "total_debt": float(stmt.totalDebt) if hasattr(stmt, 'totalDebt') and stmt.totalDebt else None,
                    "cash_and_equivalents": float(stmt.cashAndCashEquivalents) if hasattr(stmt, 'cashAndCashEquivalents') and stmt.cashAndCashEquivalents else None,
                    "current_assets": float(stmt.totalCurrentAssets) if hasattr(stmt, 'totalCurrentAssets') and stmt.totalCurrentAssets else None,
                    "current_liabilities": float(stmt.totalCurrentLiabilities) if hasattr(stmt, 'totalCurrentLiabilities') and stmt.totalCurrentLiabilities else None,
                    "inventory": float(stmt.inventory) if hasattr(stmt, 'inventory') and stmt.inventory else None,
                    "retained_earnings": float(stmt.retainedEarnings) if hasattr(stmt, 'retainedEarnings') and stmt.retainedEarnings else None,
                    "working_capital": float(stmt.totalCurrentAssets - stmt.totalCurrentLiabilities) if (
                        hasattr(stmt, 'totalCurrentAssets') and stmt.totalCurrentAssets and
                        hasattr(stmt, 'totalCurrentLiabilities') and stmt.totalCurrentLiabilities
                    ) else None,
                }
                result["data"].append(period_data)

        elif statement_type == "cash_flow":
            statements = fundamentals.cash_flow_statements if fundamentals.cash_flow_statements else []

            # Filter by simulation date if provided (simulation mode)
            if _simulation_date is not None:
                statements = _filter_by_cutoff(statements, _simulation_date.date())

            # Slice for quarters_back
            statements = statements[:quarters_back]

            for stmt in statements:
                period_data = {
                    "date": str(stmt.date) if hasattr(stmt, 'date') else None,
                    "operating_cash_flow": float(stmt.netCashProvidedByOperatingActivities) if hasattr(stmt, 'netCashProvidedByOperatingActivities') and stmt.netCashProvidedByOperatingActivities else None,
                    "free_cash_flow": float(stmt.freeCashFlow) if hasattr(stmt, 'freeCashFlow') and stmt.freeCashFlow else None,
                    "capital_expenditures": float(stmt.capitalExpenditure) if hasattr(stmt, 'capitalExpenditure') and stmt.capitalExpenditure else None,
                    "dividends_paid": float(stmt.dividendsPaid) if hasattr(stmt, 'dividendsPaid') and stmt.dividendsPaid else None,
                    "investing_cash_flow": float(stmt.netCashUsedForInvestingActivites) if hasattr(stmt, 'netCashUsedForInvestingActivites') and stmt.netCashUsedForInvestingActivites else None,
                    "financing_cash_flow": float(stmt.netCashUsedProvidedByFinancingActivities) if hasattr(stmt, 'netCashUsedProvidedByFinancingActivities') and stmt.netCashUsedProvidedByFinancingActivities else None,
                    "change_in_cash": float(stmt.netChangeInCash) if hasattr(stmt, 'netChangeInCash') and stmt.netChangeInCash else None,
                }
                result["data"].append(period_data)

        elif statement_type == "financial_ratios":
            statements = fundamentals.financial_ratios if fundamentals.financial_ratios else []

            # Filter by simulation date if provided (simulation mode)
            if _simulation_date is not None:
                statements = _filter_by_cutoff(statements, _simulation_date.date())

            # Slice for quarters_back
            statements = statements[:quarters_back]

            for stmt in statements:
                period_data = {
                    "date": str(stmt.date) if hasattr(stmt, 'date') else None,
                    "pe_ratio": float(stmt.priceEarningsRatio) if hasattr(stmt, 'priceEarningsRatio') and stmt.priceEarningsRatio else None,
                    "price_to_book": float(stmt.priceToBookRatio) if hasattr(stmt, 'priceToBookRatio') and stmt.priceToBookRatio else None,
                    "price_to_sales": float(stmt.priceToSalesRatio) if hasattr(stmt, 'priceToSalesRatio') and stmt.priceToSalesRatio else None,
                    "price_to_cash_flow": float(stmt.priceCashFlowRatio) if hasattr(stmt, 'priceCashFlowRatio') and stmt.priceCashFlowRatio else None,
                    "roe": float(stmt.returnOnEquity) if hasattr(stmt, 'returnOnEquity') and stmt.returnOnEquity else None,
                    "roa": float(stmt.returnOnAssets) if hasattr(stmt, 'returnOnAssets') and stmt.returnOnAssets else None,
                    "roic": float(stmt.returnOnCapitalEmployed) if hasattr(stmt, 'returnOnCapitalEmployed') and stmt.returnOnCapitalEmployed else None,
                    "debt_to_equity": float(stmt.debtEquityRatio) if hasattr(stmt, 'debtEquityRatio') and stmt.debtEquityRatio else None,
                    "current_ratio": float(stmt.currentRatio) if hasattr(stmt, 'currentRatio') and stmt.currentRatio else None,
                    "quick_ratio": float(stmt.quickRatio) if hasattr(stmt, 'quickRatio') and stmt.quickRatio else None,
                    "gross_margin": float(stmt.grossProfitMargin) if hasattr(stmt, 'grossProfitMargin') and stmt.grossProfitMargin else None,
                    "operating_margin": float(stmt.operatingProfitMargin) if hasattr(stmt, 'operatingProfitMargin') and stmt.operatingProfitMargin else None,
                    "net_margin": float(stmt.netProfitMargin) if hasattr(stmt, 'netProfitMargin') and stmt.netProfitMargin else None,
                }
                result["data"].append(period_data)

        elif statement_type == "analyst_estimates":
            statements = fundamentals.analyst_estimates if fundamentals.analyst_estimates else []

            # Filter by simulation date if provided (simulation mode)
            if _simulation_date is not None:
                statements = _filter_by_cutoff(statements, _simulation_date.date())

            # Slice for quarters_back
            statements = statements[:quarters_back]

            for stmt in statements:
                period_data = {
                    "date": str(stmt.date) if hasattr(stmt, 'date') else None,
                    "eps_avg": float(stmt.epsAvg) if hasattr(stmt, 'epsAvg') and stmt.epsAvg else None,
                    "eps_high": float(stmt.epsHigh) if hasattr(stmt, 'epsHigh') and stmt.epsHigh else None,
                    "eps_low": float(stmt.epsLow) if hasattr(stmt, 'epsLow') and stmt.epsLow else None,
                    "revenue_avg": float(stmt.revenueAvg) if hasattr(stmt, 'revenueAvg') and stmt.revenueAvg else None,
                    "revenue_high": float(stmt.revenueHigh) if hasattr(stmt, 'revenueHigh') and stmt.revenueHigh else None,
                    "revenue_low": float(stmt.revenueLow) if hasattr(stmt, 'revenueLow') and stmt.revenueLow else None,
                    "ebitda_avg": float(stmt.ebitdaAvg) if hasattr(stmt, 'ebitdaAvg') and stmt.ebitdaAvg else None,
                    "ebit_avg": float(stmt.ebitAvg) if hasattr(stmt, 'ebitAvg') and stmt.ebitAvg else None,
                    "net_income_avg": float(stmt.netIncomeAvg) if hasattr(stmt, 'netIncomeAvg') and stmt.netIncomeAvg else None,
                }
                result["data"].append(period_data)

        else:
            return {"error": f"Invalid statement_type: {statement_type}"}

        result["quarters_returned"] = len(result["data"])
        return result

    except Exception as e:
        return {
            "ticker": ticker.upper(),
            "statement_type": statement_type,
            "error": f"Failed to fetch fundamental data: {str(e)}"
        }


def get_analyst_estimates(
    ticker: str,
    quarters_back: int = 4,
    _simulation_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Retrieve analyst estimates for a given ticker.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        quarters_back: Number of quarters of estimates to retrieve (default: 4)
        _simulation_date: INTERNAL USE ONLY - For simulation mode, only return data on or before this date

    Returns:
        Dictionary containing analyst estimates data
    """
    return get_fundamental_data(
        ticker=ticker,
        statement_type="analyst_estimates",
        quarters_back=quarters_back,
        _simulation_date=_simulation_date
    )


def get_all_fundamentals(ticker: str, quarters_back: int = 1) -> Dict[str, Any]:
    """
    Retrieve all types of fundamental data for a given ticker.

    Args:
        ticker: Stock ticker symbol
        quarters_back: Number of quarters of historical data to retrieve

    Returns:
        Dictionary containing all fundamental data types
    """
    statement_types = ["income_statement", "balance_sheet", "cash_flow", "financial_ratios", "analyst_estimates"]

    result = {
        "ticker": ticker.upper(),
        "quarters_requested": quarters_back
    }

    for statement_type in statement_types:
        data = get_fundamental_data(ticker, statement_type, quarters_back)
        if "error" not in data:
            result[statement_type] = data["data"]
        else:
            result[statement_type] = {"error": data.get("error", "Unknown error")}

    return result


def get_all_columns_fundamentals(
    ticker: str,
    statement_type: Literal["income_statement", "balance_sheet", "cash_flow", "financial_ratios", "analyst_estimates"],
    quarters_back: int = 1,
    _simulation_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Retrieve fundamentals with ALL columns/fields as stored in the DB for a given ticker and statement type.

    This mirrors get_fundamental_data but returns the full model payload using _serialize_sa_model.
    """
    try:
        fundamentals = get_fundamentals_raw(ticker.upper())
        result = {
            "ticker": ticker.upper(),
            "statement_type": statement_type,
            "quarters_requested": quarters_back,
            "data": []
        }

        if statement_type == "income_statement":
            statements = fundamentals.income_statements if fundamentals.income_statements else []
        elif statement_type == "balance_sheet":
            statements = fundamentals.balance_sheets if fundamentals.balance_sheets else []
        elif statement_type == "cash_flow":
            statements = fundamentals.cash_flow_statements if fundamentals.cash_flow_statements else []
        elif statement_type == "financial_ratios":
            statements = fundamentals.financial_ratios if fundamentals.financial_ratios else []
        elif statement_type == "analyst_estimates":
            statements = fundamentals.analyst_estimates if fundamentals.analyst_estimates else []
        else:
            return {"error": f"Invalid statement_type: {statement_type}"}

        if _simulation_date is not None:
            statements = _filter_by_cutoff(statements, _simulation_date.date())

        statements = statements[:quarters_back]

        for stmt in statements:
            period_data = _serialize_sa_model(stmt)
            if statement_type == "balance_sheet":
                try:
                    if getattr(stmt, 'totalCurrentAssets', None) is not None and getattr(stmt, 'totalCurrentLiabilities', None) is not None:
                        period_data["workingCapital"] = float(stmt.totalCurrentAssets - stmt.totalCurrentLiabilities)
                except Exception:
                    period_data["workingCapital"] = None
            result["data"].append(period_data)

        result["quarters_returned"] = len(result["data"])
        return result
    except Exception as e:
        return {
            "ticker": ticker.upper(),
            "statement_type": statement_type,
            "error": f"Failed to fetch fundamental data: {str(e)}"
        }
