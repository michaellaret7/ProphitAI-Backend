"""Shared database utility functions.

Provides high-performance bulk insert via PostgreSQL COPY and
SQLAlchemy object serialization helpers.
"""
import io
import csv


def bulk_insert_with_copy(session, table_name, data_to_insert, ordered_columns):
    """
    Performs a bulk insert using PostgreSQL's COPY command for high performance.

    IMPORTANT: Does NOT commit - lets the calling code manage the transaction.
    NOTE: All timestamps should be in UTC timezone for consistency.

    Args:
        session: SQLAlchemy session object
        table_name: Full table name including schema (e.g., 'price_data.prices')
        data_to_insert: List of dictionaries containing the data to insert
        ordered_columns: List of column names in the order they appear in data_to_insert

    Raises:
        Exception: If COPY operation fails, exception is re-raised for transaction handling
    """
    if not data_to_insert:
        print("No new data to insert.")
        return

    print(f"Preparing to insert {len(data_to_insert):,} records using COPY.")

    string_buffer = io.StringIO()
    writer = csv.writer(string_buffer)

    for row_dict in data_to_insert:
        writer.writerow([row_dict.get(col) for col in ordered_columns])

    string_buffer.seek(0)

    raw_connection = session.connection().connection
    cursor = raw_connection.cursor()

    try:
        # Quote column names to preserve case sensitivity in PostgreSQL
        quoted_columns = ','.join([f'"{col}"' for col in ordered_columns])
        copy_sql = f"COPY {table_name} ({quoted_columns}) FROM STDIN WITH (FORMAT CSV)"
        cursor.copy_expert(sql=copy_sql, file=string_buffer)
        print("✅ Bulk insertion prepared (will commit with session).")
    except Exception as e:
        print(f"❌ Error during COPY: {e}")
        raise  # Let the session handle rollback
    finally:
        cursor.close()


def serialize_sqlalchemy_obj(obj):
        """Convert SQLAlchemy object to dictionary"""
        if obj is None:
            return None

        result = {}
        for column in obj.__table__.columns:
            value = getattr(obj, column.name)
            # Convert datetime/date objects to strings
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            # Convert Decimal to float
            elif hasattr(value, 'is_finite'):
                value = float(value)
            # Convert UUID to string
            elif hasattr(value, 'hex'):  # UUID objects have a hex attribute
                value = str(value)
            result[column.name] = value
        return result
