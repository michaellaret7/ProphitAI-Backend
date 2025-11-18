"""
Script to fetch and display all datasets for AAPL from the market_data database.
Writes complete datasets to a file.
"""

import pandas as pd
import sys
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import (
    Ticker,
    BalanceSheet,
    CashFlowStatement,
    IncomeStatement,
    FinancialRatio,
    AnalystEstimate,
    ETFHolding,
    ETFInfo,
    Dividend,
    EarningsTranscript,
    Price,
    PressRelease,
    StockNews,
    PriceTargetNews,
    StockGradeNews,
    StockGradesIndividual,
    StockGradesSummary,
    Rating,
    AnalystRecommendation,
    PriceTargetSummary
)


def print_dataset_info(name: str, df: pd.DataFrame):
    """Print complete dataset information."""
    print(f"\n{'='*80}")
    print(f"Dataset: {name}")
    print(f"{'='*80}")
    print(f"Total Records: {len(df)}")

    if len(df) == 0:
        print("No data available")
        return

    print(f"\nComplete Dataset:")
    # Set pandas display options to show all rows
    with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', None):
        print(df)

    if hasattr(df.index, 'min'):
        print(f"\nDate Range: {df.index.min()} to {df.index.max()}")


def fetch_all_aapl_data():
    """Fetch all datasets for AAPL and display head/tail for each."""

    session: Session = MarketSession()

    try:
        # Get AAPL ticker
        ticker = session.query(Ticker).filter(Ticker.ticker == 'AAPL').first()

        if not ticker:
            print("AAPL ticker not found in database!")
            return

        print(f"Found ticker: {ticker.ticker} (ID: {ticker.id})")
        print(f"Sector: {ticker.sector}, Industry: {ticker.industry}")

        # 1. Balance Sheets - SKIPPED
        print(f"\n{'='*80}")
        print(f"Dataset: Balance Sheets")
        print(f"{'='*80}")
        print("SKIPPED - Balance sheet data excluded from output")
        bs_count = session.query(BalanceSheet).filter(BalanceSheet.ticker_id == ticker.id).count()
        first_bs = session.query(BalanceSheet).filter(BalanceSheet.ticker_id == ticker.id).order_by(BalanceSheet.date).first()
        last_bs = session.query(BalanceSheet).filter(BalanceSheet.ticker_id == ticker.id).order_by(BalanceSheet.date.desc()).first()
        if first_bs and last_bs:
            print(f"Date Range: {first_bs.date} to {last_bs.date}")
            print(f"Total Records: {bs_count}")

        # 2. Cash Flow Statements - SKIPPED
        print(f"\n{'='*80}")
        print(f"Dataset: Cash Flow Statements")
        print(f"{'='*80}")
        print("SKIPPED - Cash flow data excluded from output")
        cf_count = session.query(CashFlowStatement).filter(CashFlowStatement.ticker_id == ticker.id).count()
        first_cf = session.query(CashFlowStatement).filter(CashFlowStatement.ticker_id == ticker.id).order_by(CashFlowStatement.date).first()
        last_cf = session.query(CashFlowStatement).filter(CashFlowStatement.ticker_id == ticker.id).order_by(CashFlowStatement.date.desc()).first()
        if first_cf and last_cf:
            print(f"Date Range: {first_cf.date} to {last_cf.date}")
            print(f"Total Records: {cf_count}")

        # 3. Income Statements - SKIPPED
        print(f"\n{'='*80}")
        print(f"Dataset: Income Statements")
        print(f"{'='*80}")
        print("SKIPPED - Income statement data excluded from output")
        inc_count = session.query(IncomeStatement).filter(IncomeStatement.ticker_id == ticker.id).count()
        first_inc = session.query(IncomeStatement).filter(IncomeStatement.ticker_id == ticker.id).order_by(IncomeStatement.date).first()
        last_inc = session.query(IncomeStatement).filter(IncomeStatement.ticker_id == ticker.id).order_by(IncomeStatement.date.desc()).first()
        if first_inc and last_inc:
            print(f"Date Range: {first_inc.date} to {last_inc.date}")
            print(f"Total Records: {inc_count}")

        # 4. Financial Ratios - SKIPPED
        print(f"\n{'='*80}")
        print(f"Dataset: Financial Ratios")
        print(f"{'='*80}")
        print("SKIPPED - Financial ratios data excluded from output")
        ratio_count = session.query(FinancialRatio).filter(FinancialRatio.ticker_id == ticker.id).count()
        first_ratio = session.query(FinancialRatio).filter(FinancialRatio.ticker_id == ticker.id).order_by(FinancialRatio.date).first()
        last_ratio = session.query(FinancialRatio).filter(FinancialRatio.ticker_id == ticker.id).order_by(FinancialRatio.date.desc()).first()
        if first_ratio and last_ratio:
            print(f"Date Range: {first_ratio.date} to {last_ratio.date}")
            print(f"Total Records: {ratio_count}")

        # 5. Analyst Estimates
        estimates = session.query(AnalystEstimate).filter(
            AnalystEstimate.ticker_id == ticker.id
        ).order_by(AnalystEstimate.date).all()

        if estimates:
            df = pd.DataFrame([{
                'date': e.date,
                'revenueLow': e.revenueLow,
                'revenueHigh': e.revenueHigh,
                'revenueAvg': e.revenueAvg,
                'ebitdaLow': e.ebitdaLow,
                'ebitdaHigh': e.ebitdaHigh,
                'ebitdaAvg': e.ebitdaAvg,
                'ebitLow': e.ebitLow,
                'ebitHigh': e.ebitHigh,
                'ebitAvg': e.ebitAvg,
                'netIncomeLow': e.netIncomeLow,
                'netIncomeHigh': e.netIncomeHigh,
                'netIncomeAvg': e.netIncomeAvg,
                'sgaExpenseLow': e.sgaExpenseLow,
                'sgaExpenseHigh': e.sgaExpenseHigh,
                'sgaExpenseAvg': e.sgaExpenseAvg,
                'epsAvg': e.epsAvg,
                'epsHigh': e.epsHigh,
                'epsLow': e.epsLow,
                'numAnalystsRevenue': e.numAnalystsRevenue,
                'numAnalystsEps': e.numAnalystsEps
            } for e in estimates]).set_index('date')
            print_dataset_info("Analyst Estimates", df)

        # 6. ETF Holdings
        etf_holdings = session.query(ETFHolding).filter(
            ETFHolding.ticker_id == ticker.id
        ).all()

        if etf_holdings:
            df = pd.DataFrame([{
                'asset': h.asset,
                'name': h.name,
                'isin': h.isin,
                'securityCusip': h.securityCusip,
                'sharesNumber': h.sharesNumber,
                'weightPercentage': h.weightPercentage,
                'marketValue': h.marketValue,
                'updatedAt': h.updatedAt
            } for h in etf_holdings])
            print_dataset_info("ETF Holdings", df)

        # 7. ETF Info
        etf_info = session.query(ETFInfo).filter(
            ETFInfo.ticker_id == ticker.id
        ).first()

        if etf_info:
            df = pd.DataFrame([{
                'name': etf_info.name,
                'description': etf_info.description,
                'isin': etf_info.isin,
                'assetClass': etf_info.assetClass,
                'securityCusip': etf_info.securityCusip,
                'domicile': etf_info.domicile,
                'website': etf_info.website,
                'etfCompany': etf_info.etfCompany,
                'expenseRatio': etf_info.expenseRatio,
                'assetsUnderManagement': etf_info.assetsUnderManagement,
                'avgVolume': etf_info.avgVolume,
                'inceptionDate': etf_info.inceptionDate,
                'nav': etf_info.nav,
                'navCurrency': etf_info.navCurrency,
                'holdingsCount': etf_info.holdingsCount,
                'updatedAt': etf_info.updatedAt,
                'sectorsList': str(etf_info.sectorsList)
            }])
            print_dataset_info("ETF Info", df)

        # 8. Dividends - SKIPPED
        print(f"\n{'='*80}")
        print(f"Dataset: Dividends")
        print(f"{'='*80}")
        print("SKIPPED - Dividend data excluded from output")
        div_count = session.query(Dividend).filter(Dividend.ticker_id == ticker.id).count()
        first_div = session.query(Dividend).filter(Dividend.ticker_id == ticker.id).order_by(Dividend.date).first()
        last_div = session.query(Dividend).filter(Dividend.ticker_id == ticker.id).order_by(Dividend.date.desc()).first()
        if first_div and last_div:
            print(f"Date Range: {first_div.date} to {last_div.date}")
            print(f"Total Records: {div_count}")

        # 9. Earnings Transcripts - SKIPPED
        print(f"\n{'='*80}")
        print(f"Dataset: Earnings Transcripts")
        print(f"{'='*80}")
        print("SKIPPED - Earnings transcript data excluded from output")
        trans_count = session.query(EarningsTranscript).filter(EarningsTranscript.ticker_id == ticker.id).count()
        first_trans = session.query(EarningsTranscript).filter(EarningsTranscript.ticker_id == ticker.id).order_by(EarningsTranscript.year, EarningsTranscript.period).first()
        last_trans = session.query(EarningsTranscript).filter(EarningsTranscript.ticker_id == ticker.id).order_by(EarningsTranscript.year.desc(), EarningsTranscript.period.desc()).first()
        if first_trans and last_trans:
            print(f"Date Range: {first_trans.year}/{first_trans.period} to {last_trans.year}/{last_trans.period}")
            print(f"Total Records: {trans_count}")

        # 10. Prices - SKIPPED (too large - 38,000+ records)
        print(f"\n{'='*80}")
        print(f"Dataset: Prices")
        print(f"{'='*80}")
        print("SKIPPED - Price data excluded from output (38,061 records)")
        price_count = session.query(Price).filter(Price.ticker_id == ticker.id).count()
        first_price = session.query(Price).filter(Price.ticker_id == ticker.id).order_by(Price.datetime).first()
        last_price = session.query(Price).filter(Price.ticker_id == ticker.id).order_by(Price.datetime.desc()).first()
        if first_price and last_price:
            print(f"Date Range: {first_price.datetime} to {last_price.datetime}")
            print(f"Total Records: {price_count}")

        # 11. Press Releases
        press_releases = session.query(PressRelease).filter(
            PressRelease.ticker_id == ticker.id
        ).order_by(PressRelease.publishedDate).all()

        if press_releases:
            df = pd.DataFrame([{
                'publishedDate': pr.publishedDate,
                'publisher': pr.publisher,
                'title': pr.title,
                'image': pr.image,
                'site': pr.site,
                'text': pr.text[:100] + '...' if pr.text and len(pr.text) > 100 else pr.text,
                'url': pr.url
            } for pr in press_releases]).set_index('publishedDate')
            print_dataset_info("Press Releases", df)

        # 12. Stock News
        stock_news = session.query(StockNews).filter(
            StockNews.ticker_id == ticker.id
        ).order_by(StockNews.publishedDate).all()

        if stock_news:
            df = pd.DataFrame([{
                'publishedDate': sn.publishedDate,
                'publisher': sn.publisher,
                'title': sn.title,
                'image': sn.image,
                'site': sn.site,
                'text': sn.text[:100] + '...' if sn.text and len(sn.text) > 100 else sn.text,
                'url': sn.url
            } for sn in stock_news]).set_index('publishedDate')
            print_dataset_info("Stock News", df)

        # 13. Price Target News
        price_targets = session.query(PriceTargetNews).filter(
            PriceTargetNews.ticker_id == ticker.id
        ).order_by(PriceTargetNews.publishedDate).all()

        if price_targets:
            df = pd.DataFrame([{
                'publishedDate': pt.publishedDate,
                'newsURL': pt.newsURL,
                'newsTitle': pt.newsTitle,
                'analystName': pt.analystName,
                'priceTarget': pt.priceTarget,
                'adjPriceTarget': pt.adjPriceTarget,
                'priceWhenPosted': pt.priceWhenPosted,
                'newsPublisher': pt.newsPublisher,
                'newsBaseURL': pt.newsBaseURL,
                'analystCompany': pt.analystCompany
            } for pt in price_targets]).set_index('publishedDate')
            print_dataset_info("Price Target News", df)

        # 14. Stock Grade News
        grade_news = session.query(StockGradeNews).filter(
            StockGradeNews.ticker_id == ticker.id
        ).order_by(StockGradeNews.publishedDate).all()

        if grade_news:
            df = pd.DataFrame([{
                'publishedDate': gn.publishedDate,
                'newsURL': gn.newsURL,
                'newsTitle': gn.newsTitle,
                'newsBaseURL': gn.newsBaseURL,
                'newsPublisher': gn.newsPublisher,
                'newGrade': gn.newGrade,
                'previousGrade': gn.previousGrade,
                'gradingCompany': gn.gradingCompany,
                'action': gn.action,
                'priceWhenPosted': gn.priceWhenPosted
            } for gn in grade_news]).set_index('publishedDate')
            print_dataset_info("Stock Grade News", df)

        # 15. Stock Grades Individual - SKIPPED
        print(f"\n{'='*80}")
        print(f"Dataset: Stock Grades Individual")
        print(f"{'='*80}")
        print("SKIPPED - Stock grades individual data excluded from output")
        grades_ind_count = session.query(StockGradesIndividual).filter(StockGradesIndividual.ticker_id == ticker.id).count()
        first_grade_ind = session.query(StockGradesIndividual).filter(StockGradesIndividual.ticker_id == ticker.id).order_by(StockGradesIndividual.date).first()
        last_grade_ind = session.query(StockGradesIndividual).filter(StockGradesIndividual.ticker_id == ticker.id).order_by(StockGradesIndividual.date.desc()).first()
        if first_grade_ind and last_grade_ind:
            print(f"Date Range: {first_grade_ind.date} to {last_grade_ind.date}")
            print(f"Total Records: {grades_ind_count}")

        # 16. Stock Grades Summary
        grades_summary = session.query(StockGradesSummary).filter(
            StockGradesSummary.ticker_id == ticker.id
        ).order_by(StockGradesSummary.date).all()

        if grades_summary:
            df = pd.DataFrame([{
                'date': gs.date,
                'analystRatingsStrongBuy': gs.analystRatingsStrongBuy,
                'analystRatingsBuy': gs.analystRatingsBuy,
                'analystRatingsHold': gs.analystRatingsHold,
                'analystRatingsSell': gs.analystRatingsSell,
                'analystRatingsStrongSell': gs.analystRatingsStrongSell
            } for gs in grades_summary]).set_index('date')
            print_dataset_info("Stock Grades Summary", df)

        # 17. Rating Scores
        ratings = session.query(Rating).filter(
            Rating.ticker_id == ticker.id
        ).order_by(Rating.date).all()

        if ratings:
            df = pd.DataFrame([{
                'date': r.date,
                'rating': r.rating,
                'overallScore': r.overallScore,
                'discountedCashFlowScore': r.discountedCashFlowScore,
                'returnOnEquityScore': r.returnOnEquityScore,
                'returnOnAssetsScore': r.returnOnAssetsScore,
                'debtToEquityScore': r.debtToEquityScore,
                'priceToEarningsScore': r.priceToEarningsScore,
                'priceToBookScore': r.priceToBookScore
            } for r in ratings]).set_index('date')
            print_dataset_info("Rating Scores", df)

        # 18. Analyst Recommendations
        recommendations = session.query(AnalystRecommendation).filter(
            AnalystRecommendation.ticker_id == ticker.id
        ).order_by(AnalystRecommendation.date).all()

        if recommendations:
            df = pd.DataFrame([{
                'date': rec.date,
                'rating': rec.rating,
                'ratingScore': rec.ratingScore,
                'ratingRecommendation': rec.ratingRecommendation,
                'ratingDetailsDCFScore': rec.ratingDetailsDCFScore,
                'ratingDetailsDCFRecommendation': rec.ratingDetailsDCFRecommendation,
                'ratingDetailsROEScore': rec.ratingDetailsROEScore,
                'ratingDetailsROERecommendation': rec.ratingDetailsROERecommendation,
                'ratingDetailsROAScore': rec.ratingDetailsROAScore,
                'ratingDetailsROARecommendation': rec.ratingDetailsROARecommendation,
                'ratingDetailsDEScore': rec.ratingDetailsDEScore,
                'ratingDetailsDERecommendation': rec.ratingDetailsDERecommendation,
                'ratingDetailsPEScore': rec.ratingDetailsPEScore,
                'ratingDetailsPERecommendation': rec.ratingDetailsPERecommendation,
                'ratingDetailsPBScore': rec.ratingDetailsPBScore,
                'ratingDetailsPBRecommendation': rec.ratingDetailsPBRecommendation
            } for rec in recommendations]).set_index('date')
            print_dataset_info("Analyst Recommendations", df)

        # 19. Price Target Summary
        pt_summary = session.query(PriceTargetSummary).filter(
            PriceTargetSummary.ticker_id == ticker.id
        ).first()

        if pt_summary:
            df = pd.DataFrame([{
                'lastMonthCount': pt_summary.lastMonthCount,
                'lastMonthAvgPriceTarget': pt_summary.lastMonthAvgPriceTarget,
                'lastQuarterCount': pt_summary.lastQuarterCount,
                'lastQuarterAvgPriceTarget': pt_summary.lastQuarterAvgPriceTarget,
                'lastYearCount': pt_summary.lastYearCount,
                'lastYearAvgPriceTarget': pt_summary.lastYearAvgPriceTarget,
                'allTimeCount': pt_summary.allTimeCount,
                'allTimeAvgPriceTarget': pt_summary.allTimeAvgPriceTarget,
                'publishers': str(pt_summary.publishers)
            }])
            print_dataset_info("Price Target Summary", df)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"aapl_datasets_output_{timestamp}.txt"

    # Redirect stdout to file
    original_stdout = sys.stdout

    try:
        with open(output_file, 'w') as f:
            sys.stdout = f
            fetch_all_aapl_data()

        # Restore stdout
        sys.stdout = original_stdout
        print(f"Output written to: {output_file}")

    except Exception as e:
        # Restore stdout in case of error
        sys.stdout = original_stdout
        print(f"Error writing to file: {e}")
        import traceback
        traceback.print_exc()
