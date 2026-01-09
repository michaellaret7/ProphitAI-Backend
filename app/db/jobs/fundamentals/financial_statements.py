"""
Financial Statements Updater

Updates financial statement data for tickers:
- Balance sheets
- Cash flow statements
- Income statements
- Financial ratios

Part of the fundamentals update job, split for maintainability.
"""
from sqlalchemy.dialects.postgresql import insert

from app.db.core.models.market_data_models import (
    BalanceSheet,
    CashFlowStatement,
    IncomeStatement,
    FinancialRatio,
)
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.db.jobs.base_updater import BaseUpdater


class FinancialStatementsUpdater:
    """
    Updates financial statement data for a single ticker.

    Handles balance sheets, cash flows, income statements, and financial ratios.
    Designed to be called per-ticker within a parallel processing context.
    """

    def __init__(self):
        # Reuse safe conversion methods from BaseUpdater
        self._safe_decimal = BaseUpdater.safe_decimal
        self._safe_date = BaseUpdater.safe_date

    def update_balance_sheets(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update balance sheet data for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol (e.g., 'AAPL')
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted/updated, -1 on error
        """
        try:
            data = fmp_api.get_balance_sheets(ticker_symbol, period='quarter')
            if not data:
                return 0

            # Use a dictionary to deduplicate by date
            unique_records = {}
            for item in data[:20]:  # Last 20 quarters (5 years)
                date = self._safe_date(item.get('date'))
                if date and date not in unique_records:
                    unique_records[date] = {
                        'ticker_id': ticker_id,
                        'date': date,
                        'reportedCurrency': item.get('reportedCurrency'),
                        'cik': item.get('cik'),
                        'fillingDate': self._safe_date(item.get('fillingDate')),
                        'acceptedDate': self._safe_date(item.get('acceptedDate')),
                        'calendarYear': item.get('calendarYear'),
                        'period': item.get('period'),
                        'cashAndCashEquivalents': self._safe_decimal(item.get('cashAndCashEquivalents')),
                        'shortTermInvestments': self._safe_decimal(item.get('shortTermInvestments')),
                        'cashAndShortTermInvestments': self._safe_decimal(item.get('cashAndShortTermInvestments')),
                        'netReceivables': self._safe_decimal(item.get('netReceivables')),
                        'inventory': self._safe_decimal(item.get('inventory')),
                        'otherCurrentAssets': self._safe_decimal(item.get('otherCurrentAssets')),
                        'totalCurrentAssets': self._safe_decimal(item.get('totalCurrentAssets')),
                        'propertyPlantEquipmentNet': self._safe_decimal(item.get('propertyPlantEquipmentNet')),
                        'goodwill': self._safe_decimal(item.get('goodwill')),
                        'intangibleAssets': self._safe_decimal(item.get('intangibleAssets')),
                        'goodwillAndIntangibleAssets': self._safe_decimal(item.get('goodwillAndIntangibleAssets')),
                        'longTermInvestments': self._safe_decimal(item.get('longTermInvestments')),
                        'taxAssets': self._safe_decimal(item.get('taxAssets')),
                        'otherNonCurrentAssets': self._safe_decimal(item.get('otherNonCurrentAssets')),
                        'totalNonCurrentAssets': self._safe_decimal(item.get('totalNonCurrentAssets')),
                        'otherAssets': self._safe_decimal(item.get('otherAssets')),
                        'totalAssets': self._safe_decimal(item.get('totalAssets')),
                        'accountPayables': self._safe_decimal(item.get('accountPayables')),
                        'shortTermDebt': self._safe_decimal(item.get('shortTermDebt')),
                        'taxPayables': self._safe_decimal(item.get('taxPayables')),
                        'deferredRevenue': self._safe_decimal(item.get('deferredRevenue')),
                        'otherCurrentLiabilities': self._safe_decimal(item.get('otherCurrentLiabilities')),
                        'totalCurrentLiabilities': self._safe_decimal(item.get('totalCurrentLiabilities')),
                        'longTermDebt': self._safe_decimal(item.get('longTermDebt')),
                        'deferredRevenueNonCurrent': self._safe_decimal(item.get('deferredRevenueNonCurrent')),
                        'deferredTaxLiabilitiesNonCurrent': self._safe_decimal(item.get('deferredTaxLiabilitiesNonCurrent')),
                        'otherNonCurrentLiabilities': self._safe_decimal(item.get('otherNonCurrentLiabilities')),
                        'totalNonCurrentLiabilities': self._safe_decimal(item.get('totalNonCurrentLiabilities')),
                        'otherLiabilities': self._safe_decimal(item.get('otherLiabilities')),
                        'capitalLeaseObligations': self._safe_decimal(item.get('capitalLeaseObligations')),
                        'totalLiabilities': self._safe_decimal(item.get('totalLiabilities')),
                        'preferredStock': self._safe_decimal(item.get('preferredStock')),
                        'commonStock': self._safe_decimal(item.get('commonStock')),
                        'retainedEarnings': self._safe_decimal(item.get('retainedEarnings')),
                        'accumulatedOtherComprehensiveIncomeLoss': self._safe_decimal(item.get('accumulatedOtherComprehensiveIncomeLoss')),
                        'othertotalStockholdersEquity': self._safe_decimal(item.get('othertotalStockholdersEquity')),
                        'totalStockholdersEquity': self._safe_decimal(item.get('totalStockholdersEquity')),
                        'totalEquity': self._safe_decimal(item.get('totalEquity')),
                        'totalLiabilitiesAndStockholdersEquity': self._safe_decimal(item.get('totalLiabilitiesAndStockholdersEquity')),
                        'minorityInterest': self._safe_decimal(item.get('minorityInterest')),
                        'totalLiabilitiesAndTotalEquity': self._safe_decimal(item.get('totalLiabilitiesAndTotalEquity')),
                        'totalInvestments': self._safe_decimal(item.get('totalInvestments')),
                        'totalDebt': self._safe_decimal(item.get('totalDebt')),
                        'netDebt': self._safe_decimal(item.get('netDebt')),
                        'link': item.get('link'),
                        'finalLink': item.get('finalLink')
                    }

            records = list(unique_records.values())
            if records:
                stmt = insert(BalanceSheet).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker_id', 'date'],
                    set_=dict(stmt.excluded)
                )
                session.execute(stmt)
                return len(records)
            return 0

        except Exception as e:
            print(f"Error updating balance sheets for {ticker_symbol}: {str(e)}")
            return -1

    def update_cash_flows(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update cash flow statement data for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted/updated, -1 on error
        """
        try:
            data = fmp_api.get_cash_flow_statements(ticker_symbol, period='quarter')
            if not data:
                return 0

            unique_records = {}
            for item in data[:20]:
                date = self._safe_date(item.get('date'))
                if date and date not in unique_records:
                    unique_records[date] = {
                        'ticker_id': ticker_id,
                        'date': date,
                        'reportedCurrency': item.get('reportedCurrency'),
                        'cik': item.get('cik'),
                        'fillingDate': self._safe_date(item.get('fillingDate')),
                        'acceptedDate': self._safe_date(item.get('acceptedDate')),
                        'calendarYear': item.get('calendarYear'),
                        'period': item.get('period'),
                        'netIncome': self._safe_decimal(item.get('netIncome')),
                        'depreciationAndAmortization': self._safe_decimal(item.get('depreciationAndAmortization')),
                        'deferredIncomeTax': self._safe_decimal(item.get('deferredIncomeTax')),
                        'stockBasedCompensation': self._safe_decimal(item.get('stockBasedCompensation')),
                        'changeInWorkingCapital': self._safe_decimal(item.get('changeInWorkingCapital')),
                        'accountsReceivables': self._safe_decimal(item.get('accountsReceivables')),
                        'inventory': self._safe_decimal(item.get('inventory')),
                        'accountsPayables': self._safe_decimal(item.get('accountsPayables')),
                        'otherWorkingCapital': self._safe_decimal(item.get('otherWorkingCapital')),
                        'otherNonCashItems': self._safe_decimal(item.get('otherNonCashItems')),
                        'netCashProvidedByOperatingActivities': self._safe_decimal(item.get('netCashProvidedByOperatingActivities')),
                        'investmentsInPropertyPlantAndEquipment': self._safe_decimal(item.get('investmentsInPropertyPlantAndEquipment')),
                        'acquisitionsNet': self._safe_decimal(item.get('acquisitionsNet')),
                        'purchasesOfInvestments': self._safe_decimal(item.get('purchasesOfInvestments')),
                        'salesMaturitiesOfInvestments': self._safe_decimal(item.get('salesMaturitiesOfInvestments')),
                        'otherInvestingActivites': self._safe_decimal(item.get('otherInvestingActivites')),
                        'netCashUsedForInvestingActivites': self._safe_decimal(item.get('netCashUsedForInvestingActivites')),
                        'debtRepayment': self._safe_decimal(item.get('debtRepayment')),
                        'commonStockIssued': self._safe_decimal(item.get('commonStockIssued')),
                        'commonStockRepurchased': self._safe_decimal(item.get('commonStockRepurchased')),
                        'dividendsPaid': self._safe_decimal(item.get('dividendsPaid')),
                        'otherFinancingActivites': self._safe_decimal(item.get('otherFinancingActivites')),
                        'netCashUsedProvidedByFinancingActivities': self._safe_decimal(item.get('netCashUsedProvidedByFinancingActivities')),
                        'effectOfForexChangesOnCash': self._safe_decimal(item.get('effectOfForexChangesOnCash')),
                        'netChangeInCash': self._safe_decimal(item.get('netChangeInCash')),
                        'cashAtEndOfPeriod': self._safe_decimal(item.get('cashAtEndOfPeriod')),
                        'cashAtBeginningOfPeriod': self._safe_decimal(item.get('cashAtBeginningOfPeriod')),
                        'operatingCashFlow': self._safe_decimal(item.get('operatingCashFlow')),
                        'capitalExpenditure': self._safe_decimal(item.get('capitalExpenditure')),
                        'freeCashFlow': self._safe_decimal(item.get('freeCashFlow')),
                        'link': item.get('link'),
                        'finalLink': item.get('finalLink')
                    }

            records = list(unique_records.values())
            if records:
                stmt = insert(CashFlowStatement).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker_id', 'date'],
                    set_=dict(stmt.excluded)
                )
                session.execute(stmt)
                return len(records)
            return 0

        except Exception as e:
            print(f"Error updating cash flows for {ticker_symbol}: {str(e)}")
            return -1

    def update_income_statements(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update income statement data for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted/updated, -1 on error
        """
        try:
            data = fmp_api.get_income_statements(ticker_symbol, period='quarter')
            if not data:
                return 0

            unique_records = {}
            for item in data[:20]:
                date = self._safe_date(item.get('date'))
                if date and date not in unique_records:
                    unique_records[date] = {
                        'ticker_id': ticker_id,
                        'date': date,
                        'reportedCurrency': item.get('reportedCurrency'),
                        'cik': item.get('cik'),
                        'fillingDate': self._safe_date(item.get('fillingDate')),
                        'acceptedDate': self._safe_date(item.get('acceptedDate')),
                        'calendarYear': item.get('calendarYear'),
                        'period': item.get('period'),
                        'revenue': self._safe_decimal(item.get('revenue')),
                        'costOfRevenue': self._safe_decimal(item.get('costOfRevenue')),
                        'grossProfit': self._safe_decimal(item.get('grossProfit')),
                        'grossProfitRatio': item.get('grossProfitRatio'),
                        'researchAndDevelopmentExpenses': self._safe_decimal(item.get('researchAndDevelopmentExpenses')),
                        'generalAndAdministrativeExpenses': self._safe_decimal(item.get('generalAndAdministrativeExpenses')),
                        'sellingAndMarketingExpenses': self._safe_decimal(item.get('sellingAndMarketingExpenses')),
                        'sellingGeneralAndAdministrativeExpenses': self._safe_decimal(item.get('sellingGeneralAndAdministrativeExpenses')),
                        'otherExpenses': self._safe_decimal(item.get('otherExpenses')),
                        'operatingExpenses': self._safe_decimal(item.get('operatingExpenses')),
                        'costAndExpenses': self._safe_decimal(item.get('costAndExpenses')),
                        'interestIncome': self._safe_decimal(item.get('interestIncome')),
                        'interestExpense': self._safe_decimal(item.get('interestExpense')),
                        'depreciationAndAmortization': self._safe_decimal(item.get('depreciationAndAmortization')),
                        'ebitda': self._safe_decimal(item.get('ebitda')),
                        'ebitdaratio': item.get('ebitdaratio'),
                        'operatingIncome': self._safe_decimal(item.get('operatingIncome')),
                        'operatingIncomeRatio': item.get('operatingIncomeRatio'),
                        'totalOtherIncomeExpensesNet': self._safe_decimal(item.get('totalOtherIncomeExpensesNet')),
                        'incomeBeforeTax': self._safe_decimal(item.get('incomeBeforeTax')),
                        'incomeBeforeTaxRatio': item.get('incomeBeforeTaxRatio'),
                        'incomeTaxExpense': self._safe_decimal(item.get('incomeTaxExpense')),
                        'netIncome': self._safe_decimal(item.get('netIncome')),
                        'netIncomeRatio': item.get('netIncomeRatio'),
                        'eps': item.get('eps'),
                        'epsdiluted': item.get('epsdiluted'),
                        'weightedAverageShsOut': self._safe_decimal(item.get('weightedAverageShsOut')),
                        'weightedAverageShsOutDil': self._safe_decimal(item.get('weightedAverageShsOutDil')),
                        'link': item.get('link'),
                        'finalLink': item.get('finalLink')
                    }

            records = list(unique_records.values())
            if records:
                stmt = insert(IncomeStatement).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker_id', 'date'],
                    set_=dict(stmt.excluded)
                )
                session.execute(stmt)
                return len(records)
            return 0

        except Exception as e:
            print(f"Error updating income statements for {ticker_symbol}: {str(e)}")
            return -1

    def update_financial_ratios(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> int:
        """
        Update financial ratios data for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Number of records inserted/updated, -1 on error
        """
        try:
            data = fmp_api.get_financial_ratios(ticker_symbol, period='quarter')
            if not data:
                return 0

            unique_records = {}
            for item in data[:20]:
                date = self._safe_date(item.get('date'))
                if date and date not in unique_records:
                    record = {
                        'ticker_id': ticker_id,
                        'date': date,
                        'calendarYear': item.get('calendarYear'),
                        'period': item.get('period')
                    }

                    # Add all the ratio fields
                    ratio_fields = [
                        'currentRatio', 'quickRatio', 'cashRatio', 'daysOfSalesOutstanding',
                        'daysOfInventoryOutstanding', 'operatingCycle', 'daysOfPayablesOutstanding',
                        'cashConversionCycle', 'grossProfitMargin', 'operatingProfitMargin',
                        'pretaxProfitMargin', 'netProfitMargin', 'effectiveTaxRate', 'returnOnAssets',
                        'returnOnEquity', 'returnOnCapitalEmployed', 'netIncomePerEBT', 'ebtPerEbit',
                        'ebitPerRevenue', 'debtRatio', 'debtEquityRatio', 'longTermDebtToCapitalization',
                        'totalDebtToCapitalization', 'interestCoverage', 'cashFlowToDebtRatio',
                        'companyEquityMultiplier', 'receivablesTurnover', 'payablesTurnover',
                        'inventoryTurnover', 'fixedAssetTurnover', 'assetTurnover',
                        'operatingCashFlowPerShare', 'freeCashFlowPerShare', 'cashPerShare',
                        'payoutRatio', 'operatingCashFlowSalesRatio', 'freeCashFlowOperatingCashFlowRatio',
                        'cashFlowCoverageRatios', 'shortTermCoverageRatios', 'capitalExpenditureCoverageRatio',
                        'dividendPaidAndCapexCoverageRatio', 'dividendPayoutRatio', 'priceBookValueRatio',
                        'priceToBookRatio', 'priceToSalesRatio', 'priceEarningsRatio',
                        'priceToFreeCashFlowsRatio', 'priceToOperatingCashFlowsRatio', 'priceCashFlowRatio',
                        'priceEarningsToGrowthRatio', 'priceSalesRatio', 'dividendYield',
                        'enterpriseValueMultiple', 'priceFairValue'
                    ]

                    for field in ratio_fields:
                        record[field] = item.get(field)

                    unique_records[date] = record

            records = list(unique_records.values())
            if records:
                stmt = insert(FinancialRatio).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker_id', 'date'],
                    set_=dict(stmt.excluded)
                )
                session.execute(stmt)
                return len(records)
            return 0

        except Exception as e:
            print(f"Error updating financial ratios for {ticker_symbol}: {str(e)}")
            return -1

    def update_all(
        self,
        ticker_id: str,
        ticker_symbol: str,
        session,
        fmp_api: FMP_API_DATA
    ) -> dict:
        """
        Update all financial statement data for a ticker.

        Args:
            ticker_id: UUID of the ticker
            ticker_symbol: Ticker symbol
            session: Database session
            fmp_api: FMP API instance

        Returns:
            Dictionary with counts for each data type
        """
        return {
            'balance_sheets': self.update_balance_sheets(ticker_id, ticker_symbol, session, fmp_api),
            'cash_flows': self.update_cash_flows(ticker_id, ticker_symbol, session, fmp_api),
            'income_statements': self.update_income_statements(ticker_id, ticker_symbol, session, fmp_api),
            'financial_ratios': self.update_financial_ratios(ticker_id, ticker_symbol, session, fmp_api),
        }
