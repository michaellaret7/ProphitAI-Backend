from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import *
from app.db.core.pull_fmp_data import FMP_API_DATA
from datetime import datetime, timedelta, date
from app.utils.time_utils import get_current_utc_time
from decimal import Decimal
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func, and_, text
import json

class UpdateFundamentalData:
    def __init__(self):
        self.fmp_api = FMP_API_DATA()
        self.lock = threading.Lock()
        
        # Progress tracking counters
        self.total_tickers = 0
        self.processed = 0
        self.errors = 0
        
        # Data type specific counters
        self.counters = {
            'balance_sheets': 0,
            'cash_flows': 0,
            'income_statements': 0,
            'financial_ratios': 0,
            'analyst_estimates': 0,
            'etf_holdings': 0,
            'etf_info': 0,
            'dividends': 0,
            'press_releases': 0,
            'stock_news': 0,
            'price_target_news': 0,
            'stock_grade_news': 0,
            'stock_grades': 0,
            'rating_scores': 0,
            'analyst_recommendations': 0,
            'price_targets': 0,
            'earnings_transcripts': 0
        }
    
    def _safe_decimal(self, value):
        """Convert value to Decimal safely"""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except:
            return None
    
    def _safe_date(self, date_string):
        """Convert string to date safely"""
        if not date_string:
            return None
        try:
            if isinstance(date_string, str):
                return datetime.strptime(date_string, '%Y-%m-%d').date()
            return date_string
        except:
            return None
    
    def _safe_datetime(self, datetime_string):
        """Convert string to datetime safely"""
        if not datetime_string:
            return None
        try:
            # Handle different datetime formats from FMP API
            if 'T' in datetime_string:
                # ISO format
                return datetime.fromisoformat(datetime_string.replace('Z', '+00:00'))
            else:
                # Space separated format
                return datetime.strptime(datetime_string, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                # Try date only format
                return datetime.strptime(datetime_string, '%Y-%m-%d')
            except:
                return None 

    # =========================================================================
    # CORE FUNDAMENTAL DATA UPDATE METHODS
    # =========================================================================
    
    def _update_balance_sheets(self, ticker_id: str, ticker_symbol: str, session):
        """Update balance sheet data for a ticker"""
        try:
            data = self.fmp_api.get_balance_sheets(ticker_symbol, period='quarter')
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

    def _update_cash_flows(self, ticker_id: str, ticker_symbol: str, session):
        """Update cash flow statement data for a ticker"""
        try:
            data = self.fmp_api.get_cash_flow_statements(ticker_symbol, period='quarter')
            if not data:
                return 0
            
            # Use a dictionary to deduplicate by date
            unique_records = {}
            for item in data[:20]:  # Last 20 quarters
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
    
    def _update_income_statements(self, ticker_id: str, ticker_symbol: str, session):
        """Update income statement data for a ticker"""
        try:
            data = self.fmp_api.get_income_statements(ticker_symbol, period='quarter')
            if not data:
                return 0
            
            # Use a dictionary to deduplicate by date
            unique_records = {}
            for item in data[:20]:  # Last 20 quarters
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

    def _update_financial_ratios(self, ticker_id: str, ticker_symbol: str, session):
        """Update financial ratios data for a ticker"""
        try:
            data = self.fmp_api.get_financial_ratios(ticker_symbol, period='quarter')
            if not data:
                return 0
            
            # Use a dictionary to deduplicate by date
            unique_records = {}
            for item in data[:20]:  # Last 20 quarters
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
    
    def _update_analyst_estimates(self, ticker_id: str, ticker_symbol: str, session):
        """Update analyst estimates data for a ticker"""
        try:
            data = self.fmp_api.get_analyst_estimates(ticker_symbol, period='quarter')
            if not data:
                return 0
            
            # Use a dictionary to deduplicate by date
            unique_records = {}
            for item in data[:20]:  # Last 20 quarters
                date = self._safe_date(item.get('date'))
                if date and date not in unique_records:
                    unique_records[date] = {
                        'ticker_id': ticker_id,
                        'date': date,
                        'revenueLow': self._safe_decimal(item.get('revenueLow')),
                        'revenueHigh': self._safe_decimal(item.get('revenueHigh')),
                        'revenueAvg': self._safe_decimal(item.get('revenueAvg')),
                        'ebitdaLow': self._safe_decimal(item.get('ebitdaLow')),
                        'ebitdaHigh': self._safe_decimal(item.get('ebitdaHigh')),
                        'ebitdaAvg': self._safe_decimal(item.get('ebitdaAvg')),
                        'ebitLow': self._safe_decimal(item.get('ebitLow')),
                        'ebitHigh': self._safe_decimal(item.get('ebitHigh')),
                        'ebitAvg': self._safe_decimal(item.get('ebitAvg')),
                        'netIncomeLow': self._safe_decimal(item.get('netIncomeLow')),
                        'netIncomeHigh': self._safe_decimal(item.get('netIncomeHigh')),
                        'netIncomeAvg': self._safe_decimal(item.get('netIncomeAvg')),
                        'sgaExpenseLow': self._safe_decimal(item.get('sgaExpenseLow')),
                        'sgaExpenseHigh': self._safe_decimal(item.get('sgaExpenseHigh')),
                        'sgaExpenseAvg': self._safe_decimal(item.get('sgaExpenseAvg')),
                        'epsAvg': item.get('epsAvg'),
                        'epsHigh': item.get('epsHigh'),
                        'epsLow': item.get('epsLow'),
                        'numAnalystsRevenue': item.get('numberAnalystEstimatedRevenue'),
                        'numAnalystsEps': item.get('numberAnalystEstimatedEps')
                    }
            
            records = list(unique_records.values())
            
            if records:
                stmt = insert(AnalystEstimate).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker_id', 'date'],
                    set_=dict(stmt.excluded)
                )
                session.execute(stmt)
                return len(records)
            return 0
            
        except Exception as e:
            print(f"Error updating analyst estimates for {ticker_symbol}: {str(e)}")
            return -1
    
    def _update_etf_holdings(self, ticker_id: str, ticker_symbol: str, session):
        """Update ETF holdings data (only for ETF tickers)"""
        try:
            # First check if this is an ETF
            ticker = session.query(Ticker).filter(Ticker.id == ticker_id).first()
            if not ticker or not ticker.is_etf:
                return 0
            
            data = self.fmp_api.get_etf_holdings(ticker_symbol)
            if not data:
                return 0
            
            # Delete existing holdings for this ETF
            session.query(ETFHolding).filter(ETFHolding.ticker_id == ticker_id).delete()
            session.flush()  # Ensure delete is executed within the transaction
            
            # Use a dictionary to deduplicate holdings by asset symbol
            unique_holdings = {}
            for item in data[:500]:  # Limit to top 500 holdings
                asset = item.get('asset', '').strip()
                
                # Skip empty assets
                if not asset:
                    continue
                
                # If we already have this asset, keep the one with higher weight or first occurrence
                if asset in unique_holdings:
                    existing_weight = unique_holdings[asset].get('weightPercentage', 0) or 0
                    new_weight = item.get('weightPercentage', 0) or 0
                    if new_weight <= existing_weight:
                        continue  # Keep the existing one
                
                # Add or update the holding
                unique_holdings[asset] = {
                    'ticker_id': ticker_id,
                    'asset': asset,
                    'name': item.get('name'),
                    'isin': item.get('isin'),
                    'securityCusip': item.get('cusip'),
                    'sharesNumber': self._safe_decimal(item.get('sharesNumber')),
                    'weightPercentage': item.get('weightPercentage'),
                    'marketValue': self._safe_decimal(item.get('marketValue')),
                    'updatedAt': self._safe_datetime(item.get('updated'))
                }
            
            if unique_holdings:
                records = list(unique_holdings.values())
                stmt = insert(ETFHolding).values(records)
                # Add ON CONFLICT clause as extra safety
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker_id', 'asset'],
                    set_={'weightPercentage': stmt.excluded.weightPercentage,
                          'sharesNumber': stmt.excluded.sharesNumber,
                          'marketValue': stmt.excluded.marketValue,
                          'updatedAt': stmt.excluded.updatedAt}
                )
                session.execute(stmt)
                return len(records)
            return 0
            
        except Exception as e:
            print(f"Error updating ETF holdings for {ticker_symbol}: {str(e)}")
            return -1
    
    def _update_etf_info(self, ticker_id: str, ticker_symbol: str, session):
        """Update ETF info data (only for ETF tickers)"""
        try:
            # First check if this is an ETF
            ticker = session.query(Ticker).filter(Ticker.id == ticker_id).first()
            if not ticker or not ticker.is_etf:
                return 0
            
            data = self.fmp_api.get_etf_info(ticker_symbol)
            if not data or not isinstance(data, list) or len(data) == 0:
                return 0
            
            info = data[0]  # API returns a list with one item
            
            record = {
                'ticker_id': ticker_id,
                'name': info.get('name'),
                'description': info.get('description'),
                'isin': info.get('isin'),
                'assetClass': info.get('assetClass'),
                'securityCusip': info.get('cusip'),
                'domicile': info.get('domicile'),
                'website': info.get('website'),
                'etfCompany': info.get('etfCompany'),
                'expenseRatio': info.get('expenseRatio'),
                'assetsUnderManagement': self._safe_decimal(info.get('aum')),
                'avgVolume': info.get('avgVolume'),
                'inceptionDate': self._safe_date(info.get('inceptionDate')),
                'nav': info.get('nav'),
                'navCurrency': info.get('navCurrency'),
                'holdingsCount': info.get('holdingsCount'),
                'updatedAt': self._safe_datetime(info.get('updated')),
                'sectorsList': info.get('sectorsList')
            }
            
            stmt = insert(ETFInfo).values(record)
            stmt = stmt.on_conflict_do_update(
                index_elements=['ticker_id'],
                set_=dict(stmt.excluded)
            )
            session.execute(stmt)
            return 1
            
        except Exception as e:
            print(f"Error updating ETF info for {ticker_symbol}: {str(e)}")
            return -1
    
    def _update_dividends(self, ticker_id: str, ticker_symbol: str, session):
        """Update dividend data for a ticker"""
        try:
            data = self.fmp_api.get_dividends(ticker_symbol)
            if not data:
                return 0
            
            records = []
            for item in data[:100]:  # Last 100 dividend records
                record = {
                    'ticker_id': ticker_id,
                    'date': self._safe_date(item.get('date')),
                    'recordDate': self._safe_date(item.get('recordDate')),
                    'paymentDate': self._safe_date(item.get('paymentDate')),
                    'declarationDate': self._safe_date(item.get('declarationDate')),
                    'adjDividend': item.get('adjDividend'),
                    'dividend': item.get('dividend'),
                    'yield_': item.get('yield'),
                    'frequency': item.get('frequency')
                }
                if record['date']:
                    records.append(record)
            
            if records:
                stmt = insert(Dividend).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker_id', 'date'],
                    set_=dict(stmt.excluded)
                )
                session.execute(stmt)
                return len(records)
            return 0
            
        except Exception as e:
            print(f"Error updating dividends for {ticker_symbol}: {str(e)}")
            return -1 

    # =========================================================================
    # NEWS DATA UPDATE METHODS
    # =========================================================================
    
    def _update_press_releases(self, ticker_id: str, ticker_symbol: str, session):
        """Update press releases for a ticker"""
        try:
            data = self.fmp_api.get_press_releases(ticker_symbol, limit=100)
            if not data:
                return 0
            
            # Use a dictionary to deduplicate by URL
            unique_records = {}
            for item in data[:100]:  # Last 100 press releases
                url = item.get('url', '')[:512]  # Limit URL length
                if url and url not in unique_records:  # Only add if URL is unique
                    unique_records[url] = {
                        'ticker_id': ticker_id,
                        'publishedDate': self._safe_datetime(item.get('publishedDate')),
                        'publisher': item.get('publisher'),
                        'title': item.get('title'),
                        'image': item.get('image'),
                        'site': item.get('site'),
                        'text': item.get('text'),
                        'url': url
                    }
            
            records = list(unique_records.values())
            
            if records:
                stmt = insert(PressRelease).values(records)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['ticker_id', 'url']
                )
                result = session.execute(stmt)
                return result.rowcount
            return 0
            
        except Exception as e:
            print(f"Error updating press releases for {ticker_symbol}: {str(e)}")
            return -1
    
    def _update_stock_news(self, ticker_id: str, ticker_symbol: str, session):
        """Update stock news for a ticker"""
        try:
            data = self.fmp_api.get_stock_news(ticker_symbol, limit=100)
            if not data:
                return 0
            
            # Use a dictionary to deduplicate by URL
            unique_records = {}
            for item in data[:100]:  # Last 100 news items
                url = item.get('url', '')[:512]
                if url and url not in unique_records:
                    unique_records[url] = {
                        'ticker_id': ticker_id,
                        'publishedDate': self._safe_datetime(item.get('publishedDate')),
                        'publisher': item.get('publisher'),
                        'title': item.get('title'),
                        'image': item.get('image'),
                        'site': item.get('site'),
                        'text': item.get('text'),
                        'url': url
                    }
            
            records = list(unique_records.values())
            
            if records:
                stmt = insert(StockNews).values(records)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['ticker_id', 'url']
                )
                result = session.execute(stmt)
                return result.rowcount
            return 0
            
        except Exception as e:
            print(f"Error updating stock news for {ticker_symbol}: {str(e)}")
            return -1
    
    def _update_price_target_news(self, ticker_id: str, ticker_symbol: str, session):
        """Update price target news for a ticker"""
        try:
            data = self.fmp_api.get_price_target_news(ticker_symbol, limit=100)
            if not data:
                return 0
            
            # Use a dictionary to deduplicate by newsURL
            unique_records = {}
            for item in data[:100]:
                news_url = item.get('newsURL', '')[:512]
                if news_url and news_url not in unique_records:
                    unique_records[news_url] = {
                        'ticker_id': ticker_id,
                        'publishedDate': self._safe_datetime(item.get('publishedDate')),
                        'newsURL': news_url,
                        'newsTitle': item.get('newsTitle'),
                        'analystName': item.get('analystName'),
                        'priceTarget': item.get('priceTarget'),
                        'adjPriceTarget': item.get('adjPriceTarget'),
                        'priceWhenPosted': item.get('priceWhenPosted'),
                        'newsPublisher': item.get('newsPublisher'),
                        'newsBaseURL': item.get('newsBaseURL'),
                        'analystCompany': item.get('analystCompany')
                    }
            
            records = list(unique_records.values())
            
            if records:
                stmt = insert(PriceTargetNews).values(records)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['ticker_id', 'newsURL']
                )
                result = session.execute(stmt)
                return result.rowcount
            return 0
            
        except Exception as e:
            print(f"Error updating price target news for {ticker_symbol}: {str(e)}")
            return -1
    
    def _update_stock_grade_news(self, ticker_id: str, ticker_symbol: str, session):
        """Update stock grade news for a ticker"""
        try:
            data = self.fmp_api.get_stock_grade_news(ticker_symbol, limit=100)
            if not data:
                return 0
            
            # Use a dictionary to deduplicate by newsURL
            unique_records = {}
            for item in data[:100]:
                news_url = item.get('newsURL', '')[:512]
                if news_url and news_url not in unique_records:
                    unique_records[news_url] = {
                        'ticker_id': ticker_id,
                        'publishedDate': self._safe_datetime(item.get('publishedDate')),
                        'newsURL': news_url,
                        'newsTitle': item.get('newsTitle'),
                        'newsBaseURL': item.get('newsBaseURL'),
                        'newsPublisher': item.get('newsPublisher'),
                        'newGrade': item.get('newGrade'),
                        'previousGrade': item.get('previousGrade'),
                        'gradingCompany': item.get('gradingCompany'),
                        'action': item.get('action'),
                        'priceWhenPosted': item.get('priceWhenPosted')
                    }
            
            records = list(unique_records.values())
            
            if records:
                stmt = insert(StockGradeNews).values(records)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['ticker_id', 'newsURL']
                )
                result = session.execute(stmt)
                return result.rowcount
            return 0
            
        except Exception as e:
            print(f"Error updating stock grade news for {ticker_symbol}: {str(e)}")
            return -1 

    # =========================================================================
    # GRADES AND RATINGS UPDATE METHODS
    # =========================================================================
    
    def _update_stock_grades(self, ticker_id: str, ticker_symbol: str, session):
        """Update stock grades (individual and summary) for a ticker"""
        try:
            # Update individual grades
            individual_data = self.fmp_api.get_stock_grades_individual(ticker_symbol, limit=100)
            individual_count = 0
            
            if individual_data:
                # Use a dictionary to deduplicate records by (date, normalized grading company)
                unique_records = {}
                for item in individual_data[:100]:
                    date = self._safe_date(item.get('date'))
                    # Normalize grading company name to avoid duplicates like 'Keybanc' vs 'KeyBanc'
                    grading_company = item.get('gradingCompany', '').strip().lower()
                    
                    if date and grading_company:
                        # Create a unique key for deduplication
                        key = (date, grading_company)
                        
                        # Only keep the first occurrence of each unique combination
                        if key not in unique_records:
                            unique_records[key] = {
                                'ticker_id': ticker_id,
                                'date': date,
                                'gradingCompany': item.get('gradingCompany', ''),  # Keep original case for storage
                                'previousGrade': item.get('previousGrade'),
                                'newGrade': item.get('newGrade'),
                                'action': item.get('action')
                            }
                
                if unique_records:
                    records = list(unique_records.values())
                    stmt = insert(StockGradesIndividual).values(records)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['ticker_id', 'date', 'gradingCompany'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    individual_count = len(records)
            
            # Update summary grades
            summary_data = self.fmp_api.get_stock_grades_summary(ticker_symbol, limit=20)
            summary_count = 0
            
            if summary_data:
                records = []
                for item in summary_data[:20]:
                    record = {
                        'ticker_id': ticker_id,
                        'date': self._safe_date(item.get('date')),
                        'analystRatingsStrongBuy': item.get('strongBuy'),
                        'analystRatingsBuy': item.get('buy'),
                        'analystRatingsHold': item.get('hold'),
                        'analystRatingsSell': item.get('sell'),
                        'analystRatingsStrongSell': item.get('strongSell')
                    }
                    if record['date']:
                        records.append(record)
                
                if records:
                    stmt = insert(StockGradesSummary).values(records)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['ticker_id', 'date'],
                        set_=dict(stmt.excluded)
                    )
                    session.execute(stmt)
                    summary_count = len(records)
            
            return individual_count + summary_count
            
        except Exception as e:
            print(f"Error updating stock grades for {ticker_symbol}: {str(e)}")
            return -1
    
    def _update_rating_scores(self, ticker_id: str, ticker_symbol: str, session):
        """Update rating scores for a ticker"""
        try:
            data = self.fmp_api.get_rating_scores(ticker_symbol, limit=20)
            if not data:
                return 0
            
            # Use a dictionary to deduplicate by date
            unique_records = {}
            for item in data[:20]:
                date = self._safe_date(item.get('date'))
                if date and date not in unique_records:
                    unique_records[date] = {
                        'ticker_id': ticker_id,
                        'date': date,
                        'rating': item.get('symbol'),  # Sometimes the API returns symbol as rating
                        'overallScore': item.get('score'),
                        'discountedCashFlowScore': item.get('discountedCashFlowScore'),
                        'returnOnEquityScore': item.get('returnOnEquityScore'),
                        'returnOnAssetsScore': item.get('returnOnAssetsScore'),
                        'debtToEquityScore': item.get('debtToEquityScore'),
                        'priceToEarningsScore': item.get('priceToEarningsScore'),
                        'priceToBookScore': item.get('priceToBookScore')
                    }
            
            records = list(unique_records.values())
            
            if records:
                stmt = insert(Rating).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker_id', 'date'],
                    set_=dict(stmt.excluded)
                )
                session.execute(stmt)
                return len(records)
            return 0
            
        except Exception as e:
            print(f"Error updating rating scores for {ticker_symbol}: {str(e)}")
            return -1
    
    def _update_analyst_recommendations(self, ticker_id: str, ticker_symbol: str, session):
        """Update analyst recommendations for a ticker"""
        try:
            data = self.fmp_api.get_analyst_recommendations(ticker_symbol)
            if not data:
                return 0
            
            # Use a dictionary to deduplicate by date
            unique_records = {}
            for item in data[:20]:  # Last 20 recommendations
                date = self._safe_date(item.get('date'))
                if date and date not in unique_records:
                    unique_records[date] = {
                        'ticker_id': ticker_id,
                        'date': date,
                        'rating': item.get('rating'),
                        'ratingScore': item.get('ratingScore'),
                        'ratingRecommendation': item.get('ratingRecommendation'),
                        'ratingDetailsDCFScore': item.get('ratingDetailsDCFScore'),
                        'ratingDetailsDCFRecommendation': item.get('ratingDetailsDCFRecommendation'),
                        'ratingDetailsROEScore': item.get('ratingDetailsROEScore'),
                        'ratingDetailsROERecommendation': item.get('ratingDetailsROERecommendation'),
                        'ratingDetailsROAScore': item.get('ratingDetailsROAScore'),
                        'ratingDetailsROARecommendation': item.get('ratingDetailsROARecommendation'),
                        'ratingDetailsDEScore': item.get('ratingDetailsDEScore'),
                        'ratingDetailsDERecommendation': item.get('ratingDetailsDERecommendation'),
                        'ratingDetailsPEScore': item.get('ratingDetailsPEScore'),
                        'ratingDetailsPERecommendation': item.get('ratingDetailsPERecommendation'),
                        'ratingDetailsPBScore': item.get('ratingDetailsPBScore'),
                        'ratingDetailsPBRecommendation': item.get('ratingDetailsPBRecommendation')
                    }
            
            records = list(unique_records.values())
            
            if records:
                stmt = insert(AnalystRecommendation).values(records)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker_id', 'date'],
                    set_=dict(stmt.excluded)
                )
                session.execute(stmt)
                return len(records)
            return 0
            
        except Exception as e:
            print(f"Error updating analyst recommendations for {ticker_symbol}: {str(e)}")
            return -1
    
    def _update_price_target_summary(self, ticker_id: str, ticker_symbol: str, session):
        """Update price target summary for a ticker"""
        try:
            data = self.fmp_api.get_price_target_summary(ticker_symbol)
            if not data or not isinstance(data, list) or len(data) == 0:
                return 0
            
            summary = data[0]  # API returns a list with one item
            
            record = {
                'ticker_id': ticker_id,
                'lastMonthCount': summary.get('lastMonth'),
                'lastMonthAvgPriceTarget': summary.get('lastMonthAvgPriceTarget'),
                'lastQuarterCount': summary.get('lastQuarter'),
                'lastQuarterAvgPriceTarget': summary.get('lastQuarterAvgPriceTarget'),
                'lastYearCount': summary.get('lastYear'),
                'lastYearAvgPriceTarget': summary.get('lastYearAvgPriceTarget'),
                'allTimeCount': summary.get('allTime'),
                'allTimeAvgPriceTarget': summary.get('allTimeAvgPriceTarget'),
                'publishers': json.dumps(summary.get('publishers', []))
            }
            
            stmt = insert(PriceTargetSummary).values(record)
            stmt = stmt.on_conflict_do_update(
                index_elements=['ticker_id'],
                set_=dict(stmt.excluded)
            )
            session.execute(stmt)
            return 1
            
        except Exception as e:
            print(f"Error updating price target summary for {ticker_symbol}: {str(e)}")
            return -1 

    # =========================================================================
    # TRANSCRIPT UPDATE METHOD
    # =========================================================================
    
    def _update_earnings_transcripts(self, ticker_id: str, ticker_symbol: str, session):
        """Update earnings transcripts with smart quarterly logic"""
        try:
            # Get current year and quarter
            current_date = get_current_utc_time()
            current_year = current_date.year
            current_quarter = (current_date.month - 1) // 3 + 1
            
            # Check last 8 quarters (2 years)
            transcripts_added = 0
            
            for i in range(8):
                year = current_year - (i // 4)
                quarter = current_quarter - (i % 4)
                
                # Adjust for quarter overflow
                if quarter <= 0:
                    quarter += 4
                    year -= 1
                
                # Check if transcript already exists
                existing = session.query(EarningsTranscript).filter(
                    and_(
                        EarningsTranscript.ticker_id == ticker_id,
                        EarningsTranscript.year == year,
                        EarningsTranscript.period == str(quarter)
                    )
                ).first()
                
                if not existing:
                    # Fetch transcript from API
                    data = self.fmp_api.get_earnings_transcript(ticker_symbol, year, quarter)
                    
                    # Handle both list and dict responses from API
                    transcript_data = None
                    if data:
                        if isinstance(data, list) and len(data) > 0:
                            transcript_data = data[0]
                        elif isinstance(data, dict):
                            transcript_data = data
                    
                    # Check if we have valid transcript data with content
                    if transcript_data and transcript_data.get('content'):
                        record = {
                            'ticker_id': ticker_id,
                            'period': str(quarter),
                            'year': year,
                            'date': self._safe_date(transcript_data.get('date')),
                            'content': transcript_data.get('content')
                        }
                        
                        stmt = insert(EarningsTranscript).values(record)
                        session.execute(stmt)
                        transcripts_added += 1
            
            return transcripts_added
            
        except Exception as e:
            print(f"Error updating earnings transcripts for {ticker_symbol}: {str(e)}")
            return -1
    
    # =========================================================================
    # PARALLEL PROCESSING ORCHESTRATION
    # =========================================================================
    
    def _update_single_ticker_fundamentals(self, ticker_data):
        """Update all fundamental data for a single ticker (thread-safe)"""
        ticker_id, ticker_symbol = ticker_data
        session = MarketSession()
        
        results = {
            'ticker': ticker_symbol,
            'success': True,
            'details': {}
        }
        
        try:
            # Update each data type
            update_methods = [
                ('balance_sheets', self._update_balance_sheets),
                ('cash_flows', self._update_cash_flows),
                ('income_statements', self._update_income_statements),
                ('financial_ratios', self._update_financial_ratios),
                ('analyst_estimates', self._update_analyst_estimates),
                ('etf_holdings', self._update_etf_holdings),
                ('etf_info', self._update_etf_info),
                ('dividends', self._update_dividends),
                ('press_releases', self._update_press_releases),
                ('stock_news', self._update_stock_news),
                ('price_target_news', self._update_price_target_news),
                ('stock_grade_news', self._update_stock_grade_news),
                ('stock_grades', self._update_stock_grades),
                ('rating_scores', self._update_rating_scores),
                ('analyst_recommendations', self._update_analyst_recommendations),
                ('price_targets', self._update_price_target_summary),
                ('earnings_transcripts', self._update_earnings_transcripts)
            ]
            
            for data_type, update_method in update_methods:
                try:
                    # Create a savepoint before each update method
                    session.execute(text(f"SAVEPOINT sp_{data_type}"))
                    
                    count = update_method(ticker_id, ticker_symbol, session)
                    results['details'][data_type] = count
                    
                    # If successful, release the savepoint
                    session.execute(text(f"RELEASE SAVEPOINT sp_{data_type}"))
                    
                    # Update counters
                    with self.lock:
                        if count > 0:
                            self.counters[data_type] += count
                        elif count == -1:
                            results['success'] = False
                            
                except Exception as e:
                    # Rollback to the savepoint if this specific update fails
                    session.execute(text(f"ROLLBACK TO SAVEPOINT sp_{data_type}"))
                    print(f"Failed to update {data_type} for {ticker_symbol}: {str(e)}")
                    results['details'][data_type] = -1
                    # Continue with other updates instead of failing entirely
            
            # Commit all successful changes for this ticker
            session.commit()
            
            # Update progress
            with self.lock:
                self.processed += 1
                if self.processed % 10 == 0:
                    print(f"Progress: {self.processed}/{self.total_tickers} tickers processed")
            
            return results
            
        except Exception as e:
            session.rollback()
            print(f"Error updating fundamentals for {ticker_symbol}: {str(e)}")
            results['success'] = False
            results['error'] = str(e)
            
            with self.lock:
                self.errors += 1
            
            return results
            
        finally:
            session.close()
    
    def update_all_fundamentals(self, max_workers=5, ticker_limit=None):
        """Update fundamental data for all tickers using parallel processing"""
        session = MarketSession()
        
        try:
            # Get all tickers
            query = session.query(Ticker.id, Ticker.ticker)
            if ticker_limit:
                query = query.limit(ticker_limit)
            
            ticker_data = query.all()
            self.total_tickers = len(ticker_data)
            
            # Reset counters
            self.processed = 0
            self.errors = 0
            self.counters = {k: 0 for k in self.counters}
            
            print(f"Starting fundamental data update for {self.total_tickers} tickers with {max_workers} workers...")
            start_time = time.time()
            
            results = []
            
            # Use ThreadPoolExecutor for parallel processing
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_ticker = {
                    executor.submit(self._update_single_ticker_fundamentals, ticker): ticker[1]
                    for ticker in ticker_data
                }
                
                # Process completed tasks
                for future in as_completed(future_to_ticker):
                    ticker_symbol = future_to_ticker[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as exc:
                        print(f"Ticker {ticker_symbol} generated an exception: {exc}")
                        results.append({
                            'ticker': ticker_symbol,
                            'success': False,
                            'error': str(exc)
                        })
            
            # Final summary
            end_time = time.time()
            duration = end_time - start_time
            
            self._print_summary(duration, results)
            
            return results
            
        except Exception as e:
            print(f"Fundamental data update failed: {e}")
            raise
        finally:
            try:
                session.close()
            except Exception as e:
                print(f"Warning: Error closing session (data was saved successfully): {e}")
    
    def _print_summary(self, duration, results):
        """Print a detailed summary of the update process"""
        successful = sum(1 for r in results if r['success'])
        
        print(f"\n{'='*70}")
        print("FUNDAMENTAL DATA UPDATE SUMMARY:")
        print(f"{'='*70}")
        print(f"Total tickers processed: {len(results)}")
        print(f"Successful updates: {successful}")
        print(f"Failed updates: {self.errors}")
        print(f"Time taken: {duration:.2f} seconds")
        print(f"Average time per ticker: {duration/len(results):.3f} seconds")
        print(f"\nRecords updated by type:")
        for data_type, count in self.counters.items():
            if count > 0:
                print(f"  {data_type}: {count:,}")
        print("="*70)


if __name__ == "__main__":
    updater = UpdateFundamentalData()
    
    # Uncomment to run full update
    updater.update_all_fundamentals(max_workers=5) 