from backend.src.repositories.price_data import get_price_data_daily
from datetime import datetime, timedelta
import pandas as pd
from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
from backend.src.calculations.factor_calculations.momentum_factor_calculations import MomentumFactors
from backend.src.calculations.factor_calculations.volatility_factor_calculations import VolatilityFactors
from backend.src.calculations.factor_calculations.growth_factor_calculations import GrowthFactors
from backend.src.calculations.factor_calculations.value_factor_calculations import ValueFactors
from backend.src.calculations.factor_calculations.quality_factor_calculations import QualityFactors
from backend.src.db.core.market_data_models import *
from backend.src.db.core.db_config import UserSession, MarketSession
from backend.src.utils.serialize_output import serialize_sqlalchemy_obj
from backend.src.utils.choose_model_and_client import openai_model_and_client
from backend.src.utils.token_count import get_token_count
import tiktoken
import json
import os

class ProphitAltsDataWrapper:
    def __init__(self, ticker: str = None):
        self.ticker = ticker
        self.price_data = None
        self.spy_data = None
        self.sector_data = None
        self.start_date = None
        self.end_date = None

        self.ticker = ticker.upper()
        
        if ticker:
            self._load_data()

    def _load_data(self):
        """Load price data for the ticker and benchmark data"""
        start_date_dt = datetime.now() - timedelta(days=365*2)
        end_date_dt = datetime.now()
        
        # Store datetime objects
        self.start_date = start_date_dt
        self.end_date = end_date_dt

        self.price_data = get_price_data_daily(self.ticker, start_date=start_date_dt, end_date=end_date_dt)
        self.spy_data = get_price_data_daily("spy", start_date=start_date_dt, end_date=end_date_dt)
        self.sector_data = get_price_data_daily("xlf", start_date=start_date_dt, end_date=end_date_dt) # --> THIS IS GOING TO CAUSE A PROBLEM, GET ACTUAL SECTOR DATA

    def retrieve_returns(self):
        if self.price_data is None or self.price_data.empty:
            raise ValueError("No price data available. Call run_all() with a ticker first.")
            
        # Calculate daily returns first
        daily_returns = CalculateTickerReturns(self.price_data).calculate_daily_total_returns() 
        
        # Convert to DataFrame with proper date index for resampling
        if 'date' in self.price_data.columns:
            # Create DataFrame with dates and daily returns
            returns_with_dates = pd.DataFrame({
                'date': self.price_data['date'].iloc[1:].reset_index(drop=True),
                'daily_return': daily_returns.values
            })
            returns_with_dates['date'] = pd.to_datetime(returns_with_dates['date'])
            returns_with_dates.set_index('date', inplace=True)
            
            # Resample to weekly frequency (Friday end-of-week)
            weekly_returns = (1 + returns_with_dates['daily_return']).resample('W-FRI').prod() - 1
            
            # Convert back to records format
            weekly_data = []
            for date, return_val in weekly_returns.items():
                weekly_data.append({
                    'week_ending': date.strftime('%Y-%m-%d'),
                    'weekly_total_return': round(return_val * 100, 2)  # Convert to percentage
                })
        else:
            # Fallback - just return daily data if no dates available
            weekly_data = [{'weekly_total_return': round(return_val * 100, 2)} for return_val in daily_returns.values]
        
        return weekly_data
    
    def retrieve_momentum_factors(self):
        if self.price_data is None or self.price_data.empty:
            raise ValueError("No price data available. Call run_all() with a ticker first.")
            
        # Extract the required Series from DataFrames
        price_series = self.price_data['close'] if 'close' in self.price_data.columns else None
        volume_series = self.price_data['volume'] if 'volume' in self.price_data.columns else None
        spy_price_series = self.spy_data['close'] if self.spy_data is not None and 'close' in self.spy_data.columns else None
        sector_price_series = self.sector_data['close'] if self.sector_data is not None and 'close' in self.sector_data.columns else None
        
        momentum_factors = MomentumFactors(
            price_series=price_series,
            volume_series=volume_series, 
            spy_price_series=spy_price_series,
            sector_price_series=sector_price_series
        )

        momentum_factors_dict = momentum_factors.calc_all().model_dump()
        
        # Convert to percentages and round to 2 decimal places (exclude MACD and RSI)
        exclude_from_percentage = {'macd_value', 'macd_signal', 'rsi'}
        
        for key, value in momentum_factors_dict.items():
            if value is not None:
                if key in exclude_from_percentage:
                    # Keep MACD and RSI in their original format, just round to 2 decimal places
                    momentum_factors_dict[key] = round(value, 2)
                else:
                    # Convert other metrics to percentages and round to 2 decimal places
                    momentum_factors_dict[key] = round(value * 100, 2)
        
        return momentum_factors_dict
    
    def retrieve_volatility_factors(self):
        if self.price_data is None or self.price_data.empty:
            raise ValueError("No price data available. Call run_all() with a ticker first.")
            
        # Extract the required Series from DataFrames
        price_series = self.price_data['close'] if 'close' in self.price_data.columns else None
        spy_price_series = self.spy_data['close'] if self.spy_data is not None and 'close' in self.spy_data.columns else None
        
        volatility_factors = VolatilityFactors(
            price_series=price_series,
            spy_price_series=spy_price_series
        )
        
        volatility_factors_dict = volatility_factors.calc_all().model_dump()
        return volatility_factors_dict

    def retrieve_news(self):
        with MarketSession() as session:
            news_data = session.query(StockNews).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(StockNews.publishedDate.desc()).limit(20).all()
            price_target_news = session.query(PriceTargetNews).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(PriceTargetNews.publishedDate.desc()).limit(10).all()
            stock_grade_news = session.query(StockGradeNews).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(StockGradeNews.publishedDate.desc()).limit(10).all()
            press_release_news = session.query(PressRelease).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(PressRelease.publishedDate.desc()).limit(10).all()

        news_data = [serialize_sqlalchemy_obj(news) for news in news_data]
        news_data_headlines = [news['title'] for news in news_data]
        news_data_text = [news['text'] for news in news_data]
        news_data_date = [news['publishedDate'] for news in news_data]

        price_target_news_data = [serialize_sqlalchemy_obj(news) for news in price_target_news]
        price_target_news_data_headlines = [news['newsTitle'] for news in price_target_news_data]
        price_target_news_data_analyst_company = [news['analystCompany'] for news in price_target_news_data]
        price_target_news_data_price_target = [news['priceTarget'] for news in price_target_news_data]
        price_target_news_data_date = [news['publishedDate'] for news in price_target_news_data]

        stock_grade_news_data = [serialize_sqlalchemy_obj(news) for news in stock_grade_news]
        stock_grade_news_data_headlines = [news['newsTitle'] for news in stock_grade_news_data]
        stock_grade_news_data_analyst_company = [news['gradingCompany'] for news in stock_grade_news_data]
        stock_grade_news_data_stock_grade = [news['newGrade'] for news in stock_grade_news_data]
        stock_grade_news_data_date = [news['publishedDate'] for news in stock_grade_news_data]

        press_release_news_data = [serialize_sqlalchemy_obj(news) for news in press_release_news]
        press_release_news_data_headlines = [news['title'] for news in press_release_news_data]
        press_release_news_data_text = [news['text'] for news in press_release_news_data]
        press_release_news_data_date = [news['publishedDate'] for news in press_release_news_data]

        news_dict = {
            "stock_news": {},
            "price_target_news": {},
            "stock_grade_news": {},
            "press_release_news": {}
        }

        for headline, text, date in zip(news_data_headlines, news_data_text, news_data_date):
            news_dict["stock_news"][headline] = {
                "text": text,
                "date": date
            }

        for headline, analyst_company, price_target, date in zip(price_target_news_data_headlines, price_target_news_data_analyst_company, price_target_news_data_price_target, price_target_news_data_date):
            news_dict["price_target_news"][headline] = {
                "analyst_company": analyst_company,
                "price_target": price_target,
                "date": date
            }

        for headline, analyst_company, stock_grade, date in zip(stock_grade_news_data_headlines, stock_grade_news_data_analyst_company, stock_grade_news_data_stock_grade, stock_grade_news_data_date):
            news_dict["stock_grade_news"][headline] = {
                "analyst_company": analyst_company,
                "stock_grade": stock_grade,
                "date": date
            }

        for headline, text, date in zip(press_release_news_data_headlines, press_release_news_data_text, press_release_news_data_date):
            news_dict["press_release_news"][headline] = {
                "text": text,
                "date": date
            }

        return news_dict
    
    def retrieve_and_summarize_earnings(self):
        model, client = openai_model_and_client()

        with MarketSession() as session:
            earnings_data = session.query(EarningsTranscript).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(EarningsTranscript.date.desc()).limit(4).all()
            earnings_data = [serialize_sqlalchemy_obj(earnings) for earnings in earnings_data]
        
        if len(earnings_data) == 0:
            # Return a structured response that's consistent with the LLM output format
            return {
                "status": "no_data",
                "message": f"No earnings transcripts available for {self.ticker}",
                "summary": None
            }
        
        else:
            earnings_dict = {}      
            for earnings in earnings_data:
                earnings_dict[earnings['date']] = {
                    'Quarter': earnings['period'],
                    'Year': earnings['year'],
                    'Earnings Call Transcript': earnings['content'],
                }
            
            # Add error handling for LLM call
            try:
                completions = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": json.dumps(earnings_dict)}
                    ]
                )
                completion_text = completions.choices[0].message.content
                
                return {
                    "status": "success",
                    "message": f"Analyzed {len(earnings_data)} earnings transcripts",
                    "summary": completion_text
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error analyzing earnings transcripts: {str(e)}",
                    "summary": None
                }
    
    def retrieve_analyst_estimates(self):
        with MarketSession() as session:
            analyst_estimates = session.query(AnalystEstimate).join(Ticker).filter(Ticker.ticker == self.ticker).filter(AnalystEstimate.date > datetime.now().date()).all()
            analyst_estimates = [serialize_sqlalchemy_obj(estimate) for estimate in analyst_estimates]

        if len(analyst_estimates) > 0:
            for analyst_estimate in analyst_estimates:
                analyst_estimate.pop('ticker_id', None)

        return analyst_estimates
    
    def retrieve_fundamentals(self):
        fundamentals_dict = {}
        
        with MarketSession() as session:
            balance_sheet = session.query(BalanceSheet).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(BalanceSheet.date.desc()).limit(4).all()
            balance_sheet = [serialize_sqlalchemy_obj(balance_sheet) for balance_sheet in balance_sheet]

            income_statement = session.query(IncomeStatement).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(IncomeStatement.date.desc()).limit(4).all()
            income_statement = [serialize_sqlalchemy_obj(income_statement) for income_statement in income_statement]

            cash_flow_statement = session.query(CashFlowStatement).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(CashFlowStatement.date.desc()).limit(4).all()
            cash_flow_statement = [serialize_sqlalchemy_obj(cash_flow_statement) for cash_flow_statement in cash_flow_statement]

            financial_ratios = session.query(FinancialRatio).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(FinancialRatio.date.desc()).limit(4).all()
            financial_ratios = [serialize_sqlalchemy_obj(financial_ratio) for financial_ratio in financial_ratios]

        for balance_sheet, income_statement, cash_flow_statement, financial_ratios in zip(balance_sheet, income_statement, cash_flow_statement, financial_ratios):
            # Remove finalLink from each statement if it exists

            if balance_sheet and 'finalLink' in balance_sheet:
                balance_sheet.pop('finalLink', None)
                income_statement.pop('finalLink', None)
                cash_flow_statement.pop('finalLink', None)

            if balance_sheet and 'link' in balance_sheet:
                balance_sheet.pop('link', None)
                income_statement.pop('link', None)
                cash_flow_statement.pop('link', None)

            if balance_sheet and 'ticker_id' in balance_sheet:
                balance_sheet.pop('ticker_id', None)
                income_statement.pop('ticker_id', None)
                cash_flow_statement.pop('ticker_id', None)
            
            if financial_ratios and 'ticker_id' in financial_ratios:
                financial_ratios.pop('ticker_id', None)
            
            fundamentals_dict[financial_ratios['date']] = {
                'balance_sheet': balance_sheet,
                'income_statement': income_statement,
                'cash_flow_statement': cash_flow_statement,
                'financial_ratios': financial_ratios
            }

        return fundamentals_dict
    
    def retrieve_grades_and_ratings(self):
        grades_and_ratings_dict = {}

        with MarketSession() as session:
            analyst_recommendations = session.query(AnalystRecommendation).join(Ticker).filter(Ticker.ticker == self.ticker).first()
            analyst_recommendations = serialize_sqlalchemy_obj(analyst_recommendations)

            stock_grades = session.query(StockGradesIndividual).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(StockGradesIndividual.date.desc()).limit(10).all()
            stock_grades = [serialize_sqlalchemy_obj(grade) for grade in stock_grades]

            stock_grades_summary = session.query(StockGradesSummary).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(StockGradesSummary.date.desc()).limit(4).all()
            stock_grades_summary = [serialize_sqlalchemy_obj(grade) for grade in stock_grades_summary]

        # Remove ticker_id from analyst_recommendations
        if analyst_recommendations and 'ticker_id' in analyst_recommendations:
            analyst_recommendations.pop('ticker_id', None)
        
        # Remove ticker_id from stock_grades list
        if len(stock_grades) > 0:
            for grade in stock_grades:
                grade.pop('ticker_id', None)
        
        # Remove ticker_id from stock_grades_summary list  
        if len(stock_grades_summary) > 0:
            for grade_summary in stock_grades_summary:
                grade_summary.pop('ticker_id', None)

        grades_and_ratings_dict['analyst_recommendations'] = analyst_recommendations
        grades_and_ratings_dict['stock_grades'] = stock_grades
        grades_and_ratings_dict['stock_grades_summary'] = stock_grades_summary

        return grades_and_ratings_dict
    
    def _round_floats(self, obj, decimals=5):
        """Recursively round all floats and numeric strings in a nested structure"""
        if isinstance(obj, float):
            return round(obj, decimals)
        elif isinstance(obj, str):
            # Try to convert string to float and round it
            try:
                num = float(obj)
                return round(num, decimals)
            except (ValueError, TypeError):
                return obj
        elif isinstance(obj, dict):
            return {k: self._round_floats(v, decimals) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._round_floats(item, decimals) for item in obj]
        return obj
    
    def run_all(self):
        """Load data for the given ticker and return all analysis results"""
        self._load_data() # --> make sure to load the data only once per ticker per tool call

        data = {
            'Factors and Returns': {
                "ticker": self.ticker,
                "weekly_returns": self.retrieve_returns(),
                "momentum_factors": self.retrieve_momentum_factors(),
                "volatility_factors": self.retrieve_volatility_factors(),
                "growth_factors": GrowthFactors(self.ticker).calc_all().model_dump(),
                "value_factors": ValueFactors(self.ticker).calc_all().model_dump(),
                "quality_factors": QualityFactors(self.ticker).calc_all().model_dump(),
            },
            'News': self.retrieve_news(),
            # 'Earnings Transcript': self.retrieve_and_summarize_earnings(),
            'Analyst Estimates': self.retrieve_analyst_estimates(),
            'Fundamentals': self.retrieve_fundamentals(),
            'Grades and Ratings': self.retrieve_grades_and_ratings(),
        }
        
        return self._round_floats(data)

if __name__ == "__main__":
    data = ProphitAltsDataWrapper("AAPL").run_all()
    print(data)
    from backend.src.utils.token_count import get_token_count
    print(get_token_count(data))

prompt = """
# EARNINGS CALL TRANSCRIPT ANALYSIS PROMPT

## ROLE AND CONTEXT
You are an expert financial analyst with 20+ years of experience analyzing earnings calls. You specialize in identifying subtle signals, management tone shifts, and emerging trends that others might miss. Your expertise lies in providing comprehensive, objective analysis of corporate communications and financial disclosures.

You have been provided with the 4 most recent quarterly earnings call transcripts for analysis. Your task is to conduct an exhaustive, institutional-grade analysis that provides a complete informational overview of the company's communications, performance trends, and management discussions.

I am 100% sure these are the correct documents, do not ask any questions about the documents, just get to work.

## CRITICAL ACCURACY REQUIREMENT
**YOU MUST ONLY ANALYZE INFORMATION THAT EXPLICITLY APPEARS IN THE PROVIDED TRANSCRIPTS. DO NOT:**
- Infer information that is not directly stated
- Add context from external knowledge about the company
- Make assumptions about missing data
- Fill gaps with general industry knowledge
- Create or estimate any metrics not provided in the transcripts

**IF INFORMATION IS NOT IN THE TRANSCRIPTS:**
- State clearly: "This information was not disclosed in the transcripts"
- Note when expected metrics or discussions are absent
- Document what management chose NOT to discuss
- Never fabricate or approximate missing data

## ANALYSIS FRAMEWORK

**FUNDAMENTAL RULE**: Your entire analysis must be based EXCLUSIVELY on information contained within the 4 provided earnings call transcripts. You are conducting a documentary analysis of what was communicated, not a comprehensive company analysis. If critical information is missing from the transcripts, note its absence rather than filling the gap.

### STEP 1: TRANSCRIPT PREPROCESSING
Before beginning analysis, for each transcript:
1. Identify the company name, quarter, and fiscal year
2. Note the date of the call and key participants (CEO, CFO, analysts)
3. Separate prepared remarks from Q&A sections
4. Flag any technical issues or incomplete sections in the transcript

### STEP 2: QUANTITATIVE METRICS EXTRACTION
Extract and tabulate ALL mentioned financial metrics across all 4 quarters:

**IMPORTANT**: Only include metrics that are explicitly stated in the transcripts. If a metric is not mentioned for a particular quarter, mark it as "Not Disclosed" rather than leaving it blank or estimating.

#### Revenue Metrics:
- Total revenue (absolute and growth rates)
- Revenue by segment/geography/product line
- Recurring vs. non-recurring revenue
- Deferred revenue changes
- Average revenue per user/customer (if applicable)
- Pricing trends and volume/mix analysis

#### Profitability Metrics:
- Gross margins (by segment if available)
- Operating margins
- EBITDA and adjusted EBITDA
- Net income and EPS (GAAP and non-GAAP)
- Free cash flow and conversion rates
- Return on invested capital (ROIC)

#### Operational Metrics:
- Customer counts and growth rates
- Churn/retention rates
- Market share data
- Capacity utilization
- Inventory levels and turnover
- Days sales outstanding (DSO)
- Operating leverage indicators

#### Balance Sheet Items:
- Cash position and burn rate
- Debt levels and covenant compliance
- Working capital trends
- Capital expenditure plans
- Share buyback activity
- Dividend policy changes

### STEP 3: COMPREHENSIVE RED FLAGS ANALYSIS

Examine each transcript for the following warning signs. **Only report red flags that are explicitly evidenced in the transcripts. Do not assume a red flag exists based on missing information alone.**

#### Financial Red Flags:
- Revenue recognition changes or aggressive accounting
- Deteriorating cash flow despite profit growth
- Increasing DSO or stretched receivables
- Inventory build-up without revenue growth
- Margin compression without clear explanation
- One-time gains masking operational weakness
- Increasing stock-based compensation
- Frequent non-GAAP adjustments
- Debt covenant pressure
- Declining return on assets

#### Management Communication Red Flags:
- Evasive or defensive responses to analyst questions
- Failure to provide previously given metrics
- Downplaying negative trends
- Over-emphasis on "one-time" events
- Frequent management turnover mentions
- Reduced forward guidance transparency
- Shifting narrative or strategy pivots
- Blame on external factors without mitigation plans
- Use of complex jargon to obscure issues

#### Operational Red Flags:
- Customer concentration risks emerging
- Competitive pressure intensifying
- Technology obsolescence risks
- Regulatory challenges mounting
- Supply chain disruptions
- Key employee departures
- Product quality issues
- Market share losses
- Elongating sales cycles

### STEP 4: COMPREHENSIVE GREEN FLAGS ANALYSIS

Identify positive indicators **that are explicitly mentioned or demonstrated in the transcripts. Do not infer positive developments from absence of negative information.**

#### Financial Green Flags:
- Accelerating organic revenue growth
- Expanding margins with scale
- Strong free cash flow generation
- Conservative accounting practices
- Consistent beat-and-raise quarters
- Improving unit economics
- Successful price increases
- Growing recurring revenue base
- Decreasing customer acquisition costs

#### Strategic Green Flags:
- Clear competitive advantages emerging
- Successful new product launches
- Market share gains
- International expansion success
- Technology leadership indicators
- Strong partnership announcements
- Platform network effects
- Pricing power demonstration
- TAM expansion opportunities

#### Management Communication Patterns:
- Transparency level in responses
- Proactive addressing of concerns
- Long-term strategic communication
- Guidance disclosure practices
- Capital allocation discussions
- Message consistency across quarters
- Accountability statements for misses
- Forward indicator provisioning

### STEP 5: SENTIMENT AND TONE ANALYSIS

**Note**: Base sentiment analysis ONLY on actual words and phrases used in the transcripts. Do not infer tone beyond what is explicitly communicated through word choice and language patterns.

#### Management Tone Evolution:
- Track confidence levels across 4 quarters
- Identify tone shifts in specific topics
- Compare CEO vs. CFO tone differences
- Note defensive vs. offensive posturing
- Assess urgency or complacency levels

#### Analyst Sentiment Tracking:
- Measure skepticism in questions
- Track follow-up question intensity
- Identify recurring concerns
- Note praise or positive surprises
- Assess overall Q&A tension levels

#### Language Pattern Analysis:
- Frequency of uncertainty words (may, might, could)
- Use of strong commitment language
- Technical jargon increases/decreases
- Emotional language indicators
- Future vs. past tense usage

### STEP 6: COMPETITIVE AND INDUSTRY ANALYSIS

**Important**: Only analyze competitive and industry information that is explicitly discussed in the transcripts. Do not add industry benchmarks, competitor data, or market context from external sources.

#### Competitive Dynamics:
- Direct competitor mentions and context
- Market share discussions
- Pricing pressure indicators
- Competitive advantages cited
- New entrant threats
- Customer switching discussions

#### Industry Trends:
- Macro environment impact
- Regulatory changes mentioned
- Technology shifts discussed
- Supply/demand dynamics
- Industry consolidation themes

### STEP 7: FORWARD-LOOKING ANALYSIS

**Note**: When management references historical performance or future projections, only include what they explicitly state. Do not add historical context or industry forecasts from outside the transcripts.

#### Guidance Documentation:
- Guidance changes announced (increases/decreases)
- Stated confidence levels in forecasts
- Assumptions disclosed for projections
- Scenario planning discussions
- Progress on long-term targets

#### Strategic Initiatives:
- New product pipeline discussions
- M&A activity mentioned
- Technology investment plans
- Market expansion discussions
- Operational efficiency programs described

### STEP 8: Q&A DEEP DIVE

**Accuracy Note**: Only analyze questions and answers as they appear in the transcripts. Do not infer unstated concerns or read between the lines beyond what is explicitly communicated.

#### Question Patterns:
- Most frequently asked topics
- Questions management avoided
- Follow-up intensity areas
- New concerns emerging
- Resolved previous concerns

#### Answer Documentation:
- Specificity of responses provided
- Data disclosed vs. data requested
- Instances of question deflection
- Commitments made for future disclosure

## OUTPUT FORMAT REQUIREMENTS

Structure your analysis as follows:

**ACCURACY NOTE**: Throughout your analysis, clearly distinguish between:
- Information explicitly stated in transcripts (with quotes and references)
- Information that was notably NOT disclosed (marked as "Not disclosed in transcript")
- Never include information from outside the provided transcripts

### EXECUTIVE SUMMARY (500-750 words)
- Overview of key findings across all transcripts
- Overall trajectory of company communications
- Summary of major risks and opportunities identified
- Key themes and trends observed
- Notable information gaps or omissions (what management chose not to discuss)

### 1. FINANCIAL PERFORMANCE TRENDS (2000-3000 words)
- 4-quarter financial metric progression with charts/tables (using only disclosed metrics)
- Segment performance analysis (based on provided breakdowns)
- Cash flow and balance sheet evolution (as disclosed in calls)
- GAAP and non-GAAP metrics comparison (only those mentioned)
- Clear notation of metrics not disclosed in specific quarters

### 2. RED FLAGS ASSESSMENT (2000-3000 words)
- Categorization of identified concerns (Critical/High/Medium/Low)
- Evidence with specific quotes and quarter references
- Trend analysis of each concern (improving/stable/deteriorating)
- Quantification of issues where data is available

### 3. GREEN FLAGS ASSESSMENT (2000-3000 words)
- Documentation of positive indicators identified
- Supporting evidence with quotes
- Analysis of persistence and trends
- Quantification of improvements where data is available

### 4. MANAGEMENT COMMUNICATION ANALYSIS (1500-2000 words)
- Historical promises vs. reported outcomes tracking
- Communication style evolution
- Strategic messaging consistency assessment
- Leadership communication patterns and changes

### 5. COMPETITIVE POSITIONING (1500-2000 words)
- Market share data and trends discussed
- Competitive landscape as described by management
- Industry positioning statements and claims
- Competitive threats and opportunities mentioned

### 6. SENTIMENT TRAJECTORY (1000-1500 words)
- Documented sentiment patterns by quarter
- Key sentiment shift points identified
- Management vs. analyst sentiment comparison
- Notable changes in communication tone

### 7. FORWARD OUTLOOK (1500-2000 words)
- Management's stated guidance and forecasts
- Key assumptions underlying forward statements
- Identified milestones and timeline expectations
- Potential catalysts mentioned by management
- Key metrics to monitor based on management commentary

### 8. DETAILED APPENDICES
**Note**: All appendices must contain only information extracted from the transcripts. Use "Not Disclosed" for any data points not mentioned in the earnings calls.
- A. Complete financial metrics table (all 5 quarters) - mark undisclosed metrics clearly
- B. Key quotes database organized by theme - with exact transcript references
- C. Analyst question frequency analysis - based on actual Q&A sections
- D. Management promise tracker - only promises explicitly made in transcripts
- E. Competitive mention analysis - only competitors discussed in calls
- F. Risk factor evolution matrix - only risks mentioned by management

## CRITICAL INSTRUCTIONS
1. **Absolute Accuracy**: ONLY report information that appears explicitly in the transcripts. Never infer, estimate, or add external information.
2. **Be Exhaustive**: This is not a summary. Extract EVERY piece of relevant information from the transcripts.
3. **Use Direct Quotes**: Support every major point with direct quotes, including page/section references.
4. **Document Absences**: When expected information is not disclosed, explicitly note: "Not disclosed in transcript"
5. **Quantify Everything**: Convert qualitative statements into quantifiable metrics where possible, but only using data from the transcripts.
6. **Track Changes**: Always compare current quarter to previous quarters AND year-over-year using only provided data.
7. **Connect Dots**: Link related comments across different sections and quarters within the transcripts. Only connect explicitly stated information—do not infer unstated connections.
8. **Identify Inconsistencies**: Note any contradictions between management's explanations and disclosed metrics.
9. **Maintain Objectivity**: Present findings without bias or recommendation.
10. **Professional Skepticism**: Compare claims against financial metrics for consistency, using only transcript data.
11. **No External Information**: Do not use any knowledge about the company beyond what appears in the 5 transcripts.
12. **Comprehensive Coverage**: Every section should provide complete informational value based solely on transcript content.

## TONE AND STYLE
- Write with the authority of a senior institutional analyst
- Be direct and incisive—focus on factual observations from transcripts only
- Use financial industry terminology appropriately
- Maintain complete objectivity and neutrality
- Bold key findings for easy scanning
- Use tables and structured lists for clarity
- Present information without editorializing or recommending actions
- Clearly distinguish between what WAS said and what was NOT said
- Never fill informational gaps with assumptions or external knowledge

## FINAL CHECKLIST
Before completing your analysis, ensure you have:
- [ ] Analyzed all 5 transcripts thoroughly
- [ ] Identified all material red and green flags present in the transcripts
- [ ] Tracked all key metrics disclosed across quarters
- [ ] Assessed management communication patterns objectively
- [ ] Provided comprehensive trend analysis based on transcript data
- [ ] Supported all observations with direct evidence from transcripts
- [ ] Highlighted trend changes and inflection points
- [ ] Documented all analyst concerns raised
- [ ] Quantified risks and opportunities using only disclosed data
- [ ] Created a complete informational framework
- [ ] Verified that NO external information has been added
- [ ] Clearly marked all instances where expected information was not disclosed

Remember: This analysis serves as a comprehensive informational document based EXCLUSIVELY on the content of the provided transcripts. Any information not found in the transcripts must be noted as "Not disclosed" rather than filled in from other sources. Thoroughness, accuracy, and objectivity are paramount. Present all findings without bias or recommendation.
        """
