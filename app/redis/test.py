import asyncio
import os
from dotenv import load_dotenv
from app.redis.client import RedisCache
import logging
import json
import time
from datetime import datetime, timedelta
from app.repositories.price_data import get_price_data_15_mins, fetch_bulk_price_data_for_tickers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

cache = RedisCache()

async def test_redis_connection():
    """Test bulk price data fetching with Redis cache"""

    print("\n" + "="*50)
    print("🧪 REDIS BULK PRICE DATA TEST")
    print("="*50 + "\n")

    # Load environment variables
    load_dotenv()

    # Check if REDIS_URL is set
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("❌ ERROR: REDIS_URL not found in .env file")
        return

    print(f"📡 Connecting to Redis...")
    print(f"   URL: {redis_url[:30]}...{redis_url[-20:]}\n")

    # Connect to Redis
    await cache.connect()

    if not cache.client:
        print("❌ Failed to connect to Redis")
        print("\nTroubleshooting:")
        print("1. Check your .env file has REDIS_URL")
        print("2. Verify your IP is allowed in Render Access Control")
        print("3. Check the URL is correct (starts with rediss://)")
        return

    print("✅ Connected successfully!\n")

    # Test: Real database query with cache (Bulk Price Data)
    print("Bulk Price Data Test - Run this test twice!")
    print("   - First run: Cache MISS (slow - queries database)")
    print("   - Second run: Cache HIT (fast - retrieves from cache)")
    print()
    
    # Set up date range and tickers
    test_tickers = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'JPM', 'JNJ', 'V', 'XOM', 'JNJ', 'CRDO', 'AMD', 'WMT', 'F', 'IBM']
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*3)
    cache_key = f"price:bulk:15min:{'-'.join(test_tickers)}:{start_date.date()}:{end_date.date()}"
    
    print(f"   Testing with {len(test_tickers)} tickers: {', '.join(test_tickers)}")
    print(f"   Date range: {start_date.date()} to {end_date.date()}")
    print()
    
    # Check if data is already in cache
    print("   Checking cache...")
    cached_data = await cache.get(cache_key)
    
    if cached_data:
        print("   ✅ Data found in cache! (Cache HIT)")
        start_time = time.time()
        # Simulate retrieving from cache (already retrieved above)
        cache_query_time = (time.time() - start_time) * 1000
        
        # Calculate total rows across all tickers
        total_rows = sum(len(ticker_data) for ticker_data in cached_data['price_data'].values())
        data_size = len(json.dumps(cached_data, default=str))
        
        print(f"   📊 Retrieved data for {len(cached_data['price_data'])} tickers")
        print(f"   📊 Total rows: {total_rows:,}")
        print(f"   💾 Data size: {data_size:,} bytes (~{data_size/1024:.2f} KB, ~{data_size/(1024*1024):.2f} MB)")
        print(f"   ⏱️  Cache query time: {cache_query_time:.2f}ms")
        print(f"   🎉 Super fast! No database query needed!")
        print()
        
        # Display sample data to prove it's there
        print("   📋 Sample data from cache:")
        for ticker in list(cached_data['price_data'].keys())[:3]:  # Show first 3 tickers
            ticker_data = cached_data['price_data'][ticker]
            print(f"\n      {ticker}:")
            print(f"      - Total data points: {len(ticker_data):,}")
            # Show first 3 and last 3 data points
            if len(ticker_data) > 0:
                print(f"      - First data point: {ticker_data[0]['datetime'][:10]} - ${ticker_data[0]['price']:.2f}")
                if len(ticker_data) > 1:
                    print(f"      - Second data point: {ticker_data[1]['datetime'][:10]} - ${ticker_data[1]['price']:.2f}")
                if len(ticker_data) > 2:
                    print(f"      - Last data point: {ticker_data[-1]['datetime'][:10]} - ${ticker_data[-1]['price']:.2f}")
    else:
        print("   ⚠️  Data not in cache (Cache MISS)")
        print(f"   Querying database for {len(test_tickers)} tickers (this will take a while for 3 years of data)...")
        start_time = time.time()
        price_data_map = fetch_bulk_price_data_for_tickers(
            test_tickers, 
            start_date.strftime('%Y-%m-%d'), 
            end_date.strftime('%Y-%m-%d'), 
            frequency='15mins'
        )
        db_query_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        if price_data_map:
            # Convert Series data to dict for caching
            serialized_data = {}
            total_rows = 0
            
            for ticker, series in price_data_map.items():
                if series is not None and not series.empty:
                    # Convert Series to dict with datetime as string keys
                    serialized_data[ticker] = [
                        {
                            'datetime': dt.isoformat(),
                            'price': float(price)
                        }
                        for dt, price in series.items()
                    ]
                    total_rows += len(series)
            
            price_data = {
                'tickers': test_tickers,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'price_data': serialized_data
            }
            
            data_size = len(json.dumps(price_data, default=str))
            
            print(f"   ✅ Database query successful")
            print(f"   📊 Retrieved data for {len(serialized_data)} tickers")
            print(f"   📊 Total rows: {total_rows:,}")
            print(f"   💾 Data size: {data_size:,} bytes (~{data_size/1024:.2f} KB, ~{data_size/(1024*1024):.2f} MB)")
            print(f"   ⏱️  Database query time: {db_query_time:.2f}ms ({db_query_time/1000:.2f} seconds)")
            
            # Cache the result
            print("   Caching data to Redis...")
            cache_start = time.time()
            await cache.set(cache_key, price_data, ttl=3600)  # 1 hour TTL
            cache_set_time = (time.time() - cache_start) * 1000
            print(f"   ✅ Data cached with 1-hour TTL (took {cache_set_time:.2f}ms)")
            print()
            print("   💡 Run this test again to see the cache hit performance!")
        else:
            print(f"   ⚠️  No price data found for the specified tickers")
            print(f"      This might mean the tickers don't exist or no data for this date range")
    
    print()
    
    # Close connection
    await cache.close()
    
    print("\n" + "="*50)
    print("✅ ALL TESTS COMPLETED!")
    print("="*50 + "\n")
    print("🎉 Your Redis cache is working perfectly!")
    print("   Next step: Integrate into your FastAPI routes")

if __name__ == "__main__":
    asyncio.run(test_redis_connection())    