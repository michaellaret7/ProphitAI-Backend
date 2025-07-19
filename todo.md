# Price Data Update Function Plan

## Objective
Create a function in `backend/src/db/jobs/price_table.py` that:
1. Loops through the dictionary from `create_last_price_dict()`
2. For each ticker, queries FMP API for 15-minute price data from last date to current time
3. Adds new data to the database (NOT replacing anything)

## TODO Items

- [x] 1. **Add method to update prices for all tickers**
   - Use the dictionary from `create_last_price_dict()`
   - Loop through each ticker_id and last_date
   - Call update method for each ticker

- [x] 2. **Add method to update prices for single ticker**
   - Get ticker symbol from ticker_id
   - Calculate date range (last_date to current time)
   - Fetch data from FMP API using `get_intraday_prices_for_ticker`
   - Process and insert new price records

- [x] 3. **Add method to bulk insert price data**
   - Convert FMP API response to Price model format
   - Use bulk insert for efficiency
   - Handle potential duplicates gracefully

- [x] 4. **Add main execution block updates**
   - After creating the dictionary, call the update function
   - Add progress reporting

## Technical Considerations
- Keep it simple - no complex threading initially
- Use existing FMP API methods
- Ensure timezone handling between API and database
- Add basic error handling for API failures

## Notes
- FMP API returns 15-minute interval data
- Must handle timezone conversions if needed
- Should skip if data is already current

## Review

### Changes Made

1. **Added `update_prices_for_single_ticker` method**:
   - Gets ticker symbol from ticker_id using database query
   - Calculates date range starting 15 minutes after last recorded date
   - Skips update if data is already current (within 15 minutes)
   - Fetches data from FMP API using existing `get_intraday_prices_for_ticker` method
   - Returns count of records inserted

2. **Added `_bulk_insert_prices` helper method**:
   - Converts FMP API response format to Price model format
   - Uses PostgreSQL's `INSERT ... ON CONFLICT DO NOTHING` to handle duplicates
   - Returns actual count of inserted records

3. **Added `update_all_ticker_prices` method**:
   - Loops through all tickers from `create_last_price_dict()`
   - Provides progress updates every 10 tickers
   - Tracks successful updates, total records, and errors
   - Prints summary at completion

4. **Added `test_update_first_10_tickers` method**:
   - Tests the update process on only the first 10 tickers
   - Shows which tickers will be tested with their symbols
   - Provides detailed progress for each ticker
   - Prints comprehensive test summary with average records per ticker

5. **Updated main execution block**:
   - Shows current state first
   - Runs the test method by default
   - Full update method is commented out but available

### Key Features
- **Thread pooling for performance** - Uses ThreadPoolExecutor with configurable workers (default 10)
- **Thread-safe operations** - Counters protected with locks for accurate tracking
- **Duplicate handling** - Uses ON CONFLICT DO NOTHING to prevent duplicates
- **Error handling** - Each ticker update wrapped in try-except with proper rollback
- **Progress reporting** - Updates every 50 tickers and comprehensive final summary
- **Efficient queries** - Single GROUP BY query for all last dates, bulk inserts for price data
- **No data replacement** - Only adds new data from last_date + 15 minutes onwards
- **Timezone consistency** - Converts FMP's EST timestamps to UTC to match existing data format

### Timezone Conversion Update
- Added pytz library import for timezone handling
- Modified `_bulk_insert_prices` to convert EST timestamps from FMP to UTC
- Process: Parse datetime → Localize to EST → Convert to UTC → Remove timezone info for storage
- Ensures all price data in the database remains consistently in UTC format

### Thread Pooling Implementation
- Added `ThreadPoolExecutor` with configurable `max_workers` parameter (default: 10)
- Created thread-safe wrapper method `_update_ticker_thread_safe` with locking
- Each ticker update runs in its own thread with its own database session
- Thread-safe counters track progress across all threads
- No tickers will be skipped - the executor ensures all tasks complete
- Significantly faster than sequential processing while maintaining data integrity
- Progress reporting every 50 tickers with timing statistics

### Code Cleanup
- Removed test method and test queries
- Streamlined main execution block for production use
- Ready to run full update with simple command execution
