"""Script to print unique ETF industries and subindustries."""

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker

def main():
    ms = MarketSession()
    
    try:
        # Query distinct industries and subindustries for ETFs
        results = ms.query(Ticker.industry, Ticker.sub_industry)\
            .filter(Ticker.is_etf == True)\
            .distinct()\
            .all()
            
        print(f"Found {len(results)} unique combinations.")
        print("-" * 50)
        
        # Organize by industry
        industry_map = {}
        for industry, sub_industry in results:
            if industry not in industry_map:
                industry_map[industry] = set()
            if sub_industry:
                industry_map[industry].add(sub_industry)
        
        # Print results
        for industry in sorted(industry_map.keys()):
            print(f"Industry: {industry}")
            sub_industries = sorted(list(industry_map[industry]))
            if sub_industries:
                print(f"  Sub-industries: {', '.join(sub_industries)}")
            else:
                print("  (No sub-industries)")
            print()
            
    finally:
        ms.close()

if __name__ == "__main__":
    main()
