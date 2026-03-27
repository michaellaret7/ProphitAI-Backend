import pandas as pd

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to lowercase."""
    column_mapping = {}
    for col in df.columns:
        lower_col = col.lower()
        if lower_col in ['high', 'low', 'close', 'open', 'volume']:
            column_mapping[col] = lower_col

    df = df.rename(columns=column_mapping)

    # Flatten multi-level columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df