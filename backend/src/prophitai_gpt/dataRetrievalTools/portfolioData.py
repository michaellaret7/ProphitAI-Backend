from backend.src.utils.ib_utils import connect_to_ib, disconnect_from_ib, get_ib
import pandas as pd


def get_portfolio_data():
    """
    Retrieves current portfolio positions and data from Interactive Brokers using IB Insync.
    
    Returns:
        pd.DataFrame: DataFrame containing portfolio positions and data
    """
    ib = get_ib()
    
    if ib is None:
        return pd.DataFrame()  # Return empty DataFrame if connection failed
    
    # Get portfolio data
    portfolio = ib.portfolio()
    
    # Convert portfolio data to DataFrame
    portfolio_data = []
    for position in portfolio:
        data = {
            'symbol': position.contract.symbol,
            'secType': position.contract.secType,
            'exchange': position.contract.exchange,
            'currency': position.contract.currency,
            'position': position.position,
            'marketPrice': position.marketPrice,
            'marketValue': position.marketValue,
            'averageCost': position.averageCost,
            'unrealizedPNL': position.unrealizedPNL
        }
        portfolio_data.append(data)
    
    df = pd.DataFrame(portfolio_data)
    
    return df

def format_portfolio_grid(df):
    """
    Format portfolio data as a horizontal grid with key metrics.
    
    Args:
        df: Portfolio DataFrame
        
    Returns:
        str: Formatted grid as string
    """
    if df.empty:
        return "No positions in portfolio."
        
    # Select and rename the most important columns
    if 'symbol' in df.columns and 'position' in df.columns:
        display_df = df[['symbol', 'position', 'marketPrice', 'marketValue', 'averageCost', 'unrealizedPNL']]
        
        # Format numeric columns and create a new clean dataframe
        formatted_data = []
        for _, row in display_df.iterrows():
            # Format numeric values with commas for thousands
            shares = int(row['position'])
            price = row['marketPrice']
            value = row['marketValue']
            cost = row['averageCost']
            pnl = row['unrealizedPNL']
            
            formatted_row = {
                'Symbol': row['symbol'],
                'Shares': f"{shares:,}",
                'Price': f"${price:,.2f}",
                'Value': f"${value:,.2f}",
                'Cost': f"${cost:,.2f}",
                'P/L': f"-${abs(pnl):,.2f}" if pnl < 0 else f"+${pnl:,.2f}"
            }
            formatted_data.append(formatted_row)
            
        # Create a new DataFrame with the formatted data
        clean_df = pd.DataFrame(formatted_data)
        
        # Sort by value (descending)
        # Extract numeric value from the Value column for sorting
        clean_df['SortValue'] = display_df['marketValue']
        clean_df = clean_df.sort_values(by='SortValue', ascending=False)
        clean_df = clean_df.drop('SortValue', axis=1)
        
        # Force the output to be printed as a fixed-width grid without code block markers
        result = "PORTFOLIO HOLDINGS\n\n"
        
        # Calculate column widths based on the longest value in each column
        col_widths = {}
        for col in clean_df.columns:
            # Use exact width of the longest item in the column
            col_widths[col] = max(len(col), clean_df[col].astype(str).map(len).max())
            
        # Add header row with pipes
        result += "| "
        for col in clean_df.columns:
            result += col.ljust(col_widths[col]) + " | "
        result += "\n"
        
        # Add separator row
        result += "|"
        for col in clean_df.columns:
            result += "-" * (col_widths[col] + 2) + "|"
        result += "\n"
        
        # Add data rows
        for _, row in clean_df.iterrows():
            result += "| "
            for col in clean_df.columns:
                value = str(row[col])
                # Right-align numeric columns, left-align text
                if col == 'Symbol':
                    result += value.ljust(col_widths[col]) + " | "
                else:
                    result += value.rjust(col_widths[col]) + " | "
            result += "\n"
            
        return result
    else:
        return df.to_string()