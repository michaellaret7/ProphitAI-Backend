from sqlalchemy import text
from app.db.core.db_config import MarketSession

def get_cache_hit_ratio(session):
    """
    Calculates the cache hit ratio for the database.
    A ratio of >99% is ideal, indicating data is served from memory, not disk.
    
    Args:
        session: The database session to use.
    """
    cache_query = text("""
        SELECT
          'Cache Hit Ratio' as metric,
          sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as ratio
        FROM
          pg_statio_user_tables;
    """)
    
    print(f"\n{'='*80}")
    print("DATABASE HEALTH CHECK: Cache Hit Ratio")
    print(f"{'='*80}")
    
    try:
        result = session.execute(cache_query).first()
        if result and result.ratio is not None:
            ratio = result.ratio * 100
            print(f"Overall Cache Hit Ratio: {ratio:.2f}%")
            if ratio < 99.0:
                print("⚠️  WARNING: Cache hit ratio is below 99%. Consider increasing DB memory.")
            else:
                print("✅  Cache performance is excellent.")
        else:
            print("Could not calculate cache hit ratio. No table activity found.")
            
    except Exception as e:
        print(f"Error calculating cache hit ratio: {e}")
    finally:
        print("="*80 + "\n")


def get_table_and_index_bloat(session):
    """
    Identifies table and index bloat, which are un-vacuumed dead records.
    High bloat can slow down queries and waste space.
    
    Args:
        session: The database session to use.
    """
    # This query is adapted from the Heroku pg-extras library
    bloat_query = text("""
    WITH constants AS (
      SELECT current_setting('block_size')::numeric AS bs, 23 AS hdr, 4 AS ma
    ), bloat_info AS (
      SELECT
        ma,bs,schemaname,tablename,
        (datawidth+(hdr+ma-(case when hdr%ma=0 THEN ma ELSE hdr%ma END)))::numeric AS datahdr,
        (maxfracsum*(nullhdr+ma-(case when nullhdr%ma=0 THEN ma ELSE nullhdr%ma END))) AS nullhdr2
      FROM (
        SELECT
          schemaname, tablename, hdr, ma, bs,
          SUM((1-null_frac)*avg_width) AS datawidth,
          MAX(null_frac) AS maxfracsum,
          hdr+(
            SELECT 1+count(*)/8
            FROM pg_stats s2
            WHERE null_frac<>0 AND s2.schemaname = s.schemaname AND s2.tablename = s.tablename
          ) AS nullhdr
        FROM pg_stats s, constants
        GROUP BY 1,2,3,4,5
      ) AS foo
    ), table_bloat AS (
      SELECT
        schemaname, tablename, cc.relpages, bs,
        CEIL((cc.reltuples*((datahdr+ma-
          (CASE WHEN datahdr%ma=0 THEN ma ELSE datahdr%ma END))+nullhdr2+4))/(bs-20::float)) AS otta
      FROM bloat_info
      JOIN pg_class cc ON cc.relname = bloat_info.tablename
      JOIN pg_namespace nn ON cc.relnamespace = nn.oid AND nn.nspname = bloat_info.schemaname AND nn.nspname <> 'information_schema'
    ), index_bloat AS (
      SELECT
        schemaname, tablename, bs,
        COALESCE(c2.relname,'?') AS iname, COALESCE(c2.reltuples,0) AS ituples, COALESCE(c2.relpages,0) AS ipages,
        COALESCE(CEIL((c2.reltuples*(datahdr-12))/(bs-20::float)),0) AS iotta
      FROM bloat_info
      JOIN pg_class cc ON cc.relname = bloat_info.tablename
      JOIN pg_namespace nn ON cc.relnamespace = nn.oid AND nn.nspname = bloat_info.schemaname AND nn.nspname <> 'information_schema'
      JOIN pg_index i ON indrelid = cc.oid
      JOIN pg_class c2 ON c2.oid = i.indexrelid
    )
    SELECT
      type, schemaname, object_name, bloat, pg_size_pretty(raw_waste) as waste
    FROM
    (SELECT
      'table' as type,
      schemaname,
      tablename as object_name,
      ROUND(CASE WHEN otta=0 THEN 0.0 ELSE table_bloat.relpages/otta::numeric END,1) AS bloat,
      CASE WHEN relpages < otta THEN '0' ELSE (bs*(table_bloat.relpages-otta)::bigint)::bigint END AS raw_waste
    FROM
      table_bloat
        UNION
    SELECT
      'index' as type,
      schemaname,
      tablename || '::' || iname as object_name,
      ROUND(CASE WHEN iotta=0 OR ipages=0 THEN 0.0 ELSE ipages/iotta::numeric END,1) AS bloat,
      CASE WHEN ipages < iotta THEN '0' ELSE (bs*(ipages-iotta))::bigint END AS raw_waste
    FROM
      index_bloat) bloat_summary
    WHERE raw_waste > 1024*1024 -- Only show waste > 1MB
    ORDER BY raw_waste DESC, bloat DESC
    LIMIT 20;
    """)

    print(f"\n{'='*80}")
    print("DATABASE HEALTH CHECK: Table and Index Bloat (>1MB waste)")
    print(f"{'='*80}")
    
    try:
        result = session.execute(bloat_query)
        rows = result.fetchall()
        
        if not rows:
            print("✅  No significant table or index bloat found.")
            return

        print(f"{'Type':<8} {'Schema':<20} {'Object Name':<50} {'Bloat Factor':<15} {'Wasted Space'}")
        print("-" * 120)

        for row in rows:
            print(f"{row.type:<8} {row.schemaname:<20} {row.object_name:<50} {row.bloat:<15.1f} {row.waste}")
            
    except Exception as e:
        print(f"Error checking for database bloat: {e}")
    finally:
        print("="*80 + "\n")

def vacuum_table(session, schema_name, table_name, full=True, analyze=True):
    """
    Performs a VACUUM operation on a specific table.

    Args:
        session: The database session to use.
        schema_name (str): The name of the schema the table belongs to.
        table_name (str): The name of the table to vacuum.
        full (bool): Whether to perform a VACUUM FULL (locks table, reclaims more space).
        analyze (bool): Whether to also run ANALYZE (updates statistics for the query planner).
    """
    # VACUUM cannot run inside a transaction, so we need to get the raw
    # DBAPI connection and set it to autocommit mode.
    connection = session.connection().connection
    isolation_level = connection.isolation_level
    connection.set_isolation_level(0) # 0 = AUTOCOMMIT

    try:
        command = "VACUUM"
        if full:
            command += " FULL"
        if analyze:
            command += " ANALYZE"
        
        # Use f-string for schema and table names as they are controlled inputs, not user inputs.
        full_command = text(f"{command} {schema_name}.{table_name};")

        print(f"\nRunning: {full_command}")
        session.execute(full_command)
        session.commit() # Necessary to conclude the operation
        print(f"✅  Successfully vacuumed {schema_name}.{table_name}")

    except Exception as e:
        print(f"❌  Error vacuuming table {schema_name}.{table_name}: {e}")
        session.rollback()
    finally:
        # Restore the original isolation level
        connection.set_isolation_level(isolation_level)
        print("-" * 40)


