from sqlalchemy import text
from datetime import datetime
import time

def analyze_query_performance(query, session):
    """
    Analyzes the performance of a SQLAlchemy query by printing its
    execution plan using EXPLAIN ANALYZE.

    Args:
        query (Query): The SQLAlchemy query object to analyze.
        session (Session): The database session to use.
    """
    # Compile the query to get the SQL string and params
    compiled_query = query.statement.compile(
        session.bind,
        compile_kwargs={"literal_binds": True}
    )
    
    # Construct the EXPLAIN ANALYZE query
    # Using 'text()' is important to ensure it's executed as raw SQL
    explain_query = text(f"EXPLAIN ANALYZE {compiled_query}")
    
    print("\n" + "="*80)
    print("QUERY PERFORMANCE ANALYSIS:")
    print(f"SQL: {compiled_query}")
    print("-" * 80)
    
    try:
        # Execute the EXPLAIN query and print the results
        result = session.execute(explain_query)
        print("Execution Plan:")
        for row in result:
            print(row[0])
    except Exception as e:
        print(f"Could not analyze query: {e}")
    finally:
        print("="*80 + "\n")


def time_query(query, session, iterations=3):
    """
    Times the execution of a query multiple times and reports statistics.
    Useful for identifying slow queries in your application.
    
    Args:
        query: The SQLAlchemy query object to time
        session: The database session to use
        iterations: Number of times to run the query (default: 3)
        
    Returns:
        dict: Timing statistics including min, max, avg, and total rows
    """
    times = []
    row_count = 0
    
    # Compile query once to avoid including compilation time
    compiled = query.statement.compile(session.bind, compile_kwargs={"literal_binds": True})
    
    print(f"\nTiming query ({iterations} iterations)...")
    print(f"SQL: {compiled}")
    
    for i in range(iterations):
        start = time.perf_counter()
        results = query.all()
        end = time.perf_counter()
        
        elapsed = (end - start) * 1000  # Convert to milliseconds
        times.append(elapsed)
        row_count = len(results)
        
        print(f"  Run {i+1}: {elapsed:.2f}ms")
    
    stats = {
        'min_ms': min(times),
        'max_ms': max(times),
        'avg_ms': sum(times) / len(times),
        'row_count': row_count,
        'query': str(compiled)
    }
    
    print(f"\nResults: {row_count} rows")
    print(f"Min: {stats['min_ms']:.2f}ms | Max: {stats['max_ms']:.2f}ms | Avg: {stats['avg_ms']:.2f}ms")
    
    # Warning for slow queries
    if stats['avg_ms'] > 1000:
        print("⚠️  WARNING: Query averaging over 1 second!")
    
    return stats


def check_index_usage(table_name, schema_name, session):
    """
    Checks which indexes are being used on a table and their effectiveness.
    This helps identify unused indexes (wasting space) or missing indexes.
    
    Args:
        table_name: Name of the table to check
        schema_name: Schema the table belongs to
        session: Database session
    """
    # Query to get index usage statistics
    index_usage_query = text("""
    SELECT 
        schemaname,
        relname as tablename,
        indexrelname as indexname,
        idx_scan as index_scans,
        idx_tup_read as tuples_read,
        idx_tup_fetch as tuples_fetched,
        pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
        CASE 
            WHEN idx_scan = 0 THEN 'UNUSED'
            WHEN idx_scan < 10 THEN 'RARELY USED'
            ELSE 'ACTIVE'
        END as usage_status
    FROM pg_stat_user_indexes
    WHERE schemaname = :schema AND relname = :table
    ORDER BY idx_scan DESC;
    """)
    
    print(f"\n{'='*80}")
    print(f"INDEX USAGE ANALYSIS: {schema_name}.{table_name}")
    print(f"{'='*80}")
    
    try:
        result = session.execute(
            index_usage_query, 
            {"schema": schema_name, "table": table_name}
        )
        
        rows = result.fetchall()
        if not rows:
            print(f"No indexes found for {schema_name}.{table_name}")
            return
        
        # Print results in a formatted table
        print(f"{'Index Name':<40} {'Scans':<10} {'Size':<10} {'Status':<15}")
        print("-" * 80)
        
        for row in rows:
            print(f"{row.indexname:<40} {row.index_scans:<10} {row.index_size:<10} {row.usage_status:<15}")
        
        # Summary
        unused_count = sum(1 for row in rows if row.usage_status == 'UNUSED')
        if unused_count > 0:
            print(f"\n ⚠️  Found {unused_count} unused index(es) that could be removed to save space.")
            
    except Exception as e:
        print(f"Error analyzing index usage: {e}")
    finally:
        print("="*80 + "\n")


if __name__ == "__main__":
    from app.db.core.db_config import MarketSession
    from app.db.core.market_data_models import Price, Ticker, FinancialRatio
    
    session = MarketSession()
    
    # Define a query to use for the examples
    price_query = session.query(Price).join(Ticker).filter(
        Ticker.ticker == 'SSB'
    )

    fundamental_query = session.query(FinancialRatio).join(Ticker).filter(
        Ticker.ticker == 'SSB'
    )

    query = price_query
    
    # --- Example 1: Analyze the execution plan ---
    # This shows HOW the database will run the query.
    analyze_query_performance(query, session)
    
    # --- Example 2: Time the query execution ---
    # This shows HOW FAST the query runs over several iterations.
    # The function itself handles executing the query.
    time_query(query, session, iterations=3)
    
    # --- Example 3: Check index usage on relevant tables ---
    # This helps you see if your indexes are effective.
    check_index_usage(table_name='prices', schema_name='price_data', session=session)
    check_index_usage(table_name='tickers', schema_name='ticker_universe', session=session)

    # It's good practice to close the session when done with the script.
    session.close()