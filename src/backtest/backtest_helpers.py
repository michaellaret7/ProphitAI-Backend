import pandas as pd
import numpy as np
from typing import Any, Dict, Tuple, Optional # Added Optional as it's used by get_current_portfolio_holdings implicitly

def get_portfolio_value_from_json(portfolio):
    """Return summed numeric market_value in USD or default $1,000,000."""
    total = 0.0
    for pos in portfolio.get("final_portfolio", []):
        mv = pos.get("market_value")
        if isinstance(mv, (int, float)):
            total += float(mv)
        elif isinstance(mv, str):
            mv_clean = mv.replace("$", "").replace(",", "").strip()
            try:
                total += float(mv_clean)
            except ValueError:
                continue
    return total if total > 0 else 1_000_000

def get_historical_data_for_all_tickers(portfolio) -> Tuple[Dict[str, pd.DataFrame], float]:
    """
    Fetch daily closing prices for all tickers in the portfolio (plus SPY) from
    the internal Postgres price databases. No Interactive Brokers dependency.

    Returns
    -------
    Tuple[Dict[str, pd.DataFrame], float]
        A mapping of ticker -> price dataframe and the estimated portfolio value.
    """
    from src.portfolio_optimization.phase_two.data_retrieval import get_daily_closing_prices # LOCAL IMPORT
    results: dict[str, pd.DataFrame] = {}

    # Always include SPY for benchmark comparison
    print("\n📊 Getting historical data for SPY…")
    results["SPY"] = get_daily_closing_prices("SPY")

    for position in portfolio.get("final_portfolio", []):
        ticker = position.get("ticker")
        if not ticker or ticker.upper() == "CASH":
            continue
        print(f"\n📊 Getting historical data for {ticker}…")
        results[ticker] = get_daily_closing_prices(ticker)

    portfolio_value = get_portfolio_value_from_json(portfolio)
    return results, portfolio_value

def calculate_portfolio_returns(portfolio: Dict[str, Any], historical_data: Dict[str, pd.DataFrame], initial_investment: float) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, float]]]:
    """
    Calculate portfolio returns over time based on historical data and allocation percentages

    Args:
        portfolio: Dictionary containing portfolio data
        historical_data: Dictionary with tickers as keys and historical data as values
        initial_investment: Actual portfolio value from IBKR

    Returns:
        Tuple containing (portfolio_values DataFrame, allocation_dict) or (None, None) if error
    """
    # Create dictionaries to store shares and allocations for each ticker
    # shares_dict = {} # This variable was unused
    allocation_dict = {}

    # Handle duplicate tickers by combining their allocations and shares
    combined_allocations = {}

    # Filter out CASH positions from allocation calculation if present
    portfolio_items = [pos for pos in portfolio.get("final_portfolio", []) if pos.get("position_type", "").upper() != "CASH"]

    if not portfolio_items:
        print("⚠️ Portfolio contains no non-cash positions to calculate returns.")
        return None, None


    for position in portfolio_items:
        ticker = position.get("ticker")
        allocation_str = position.get("allocation", "0%")
        position_type = position.get("position_type", "LONG").upper()

        if not ticker:
            print(f"⚠️ Skipping position with missing ticker: {position}")
            continue

        try:
            allocation = float(allocation_str.strip("%")) / 100
        except ValueError:
            print(f"⚠️ Skipping position with invalid allocation format for {ticker}: {allocation_str}")
            continue


        # Adjust allocation sign based on position type
        if position_type == "SHORT":
            allocation *= -1

        if ticker in combined_allocations:
            combined_allocations[ticker] += allocation
        else:
            combined_allocations[ticker] = allocation

    # Use the combined values
    allocation_dict = combined_allocations

    if not allocation_dict:
         print("⚠️ No valid allocations found after processing portfolio.")
         return None, None

    # Normalize allocations based on absolute values to handle long/short mix
    total_exposure = sum(abs(v) for v in allocation_dict.values())
    if total_exposure > 1e-9: # Use tolerance for floating point comparison
        for ticker in allocation_dict:
            allocation_dict[ticker] /= total_exposure
    else:
        print("⚠️ Total absolute allocation is zero or near-zero, cannot normalize.")
        # Proceeding with potentially zero allocations, which might lead to zero returns.

    # Create a combined DataFrame for all ticker prices
    all_data = pd.DataFrame()

    # First, check if we have data for all tickers in allocation_dict
    missing_data = []
    valid_tickers = list(allocation_dict.keys()) # Tickers we actually need data for

    for ticker in valid_tickers:
        if ticker not in historical_data or historical_data[ticker] is None or historical_data[ticker].empty:
            missing_data.append(ticker)

    if missing_data:
        print(f"⚠️ Missing historical data for required tickers: {', '.join(missing_data)}")
        # Decide if partial calculation is allowed or return error
        # For now, let's try to proceed with available data, but warn user
        print("⚠️ Proceeding with backtest using only available ticker data.")
        # Remove missing tickers from allocation_dict to avoid errors later
        for ticker in missing_data:
            del allocation_dict[ticker]
        valid_tickers = list(allocation_dict.keys()) # Update valid tickers
        if not valid_tickers:
             print("❌ No historical data available for any allocated ticker. Cannot calculate returns.")
             return None, None


    # Combine all close prices into one DataFrame for valid tickers
    print(" assembling historical data frame...")
    for ticker in valid_tickers:
        data = historical_data[ticker]
        if 'date' in data.columns and 'close' in data.columns:
            try:
                # Ensure date is datetime and set as index
                date_index = pd.to_datetime(data['date'])
                temp_series = pd.Series(data['close'].values, index=date_index, name=ticker)
                if all_data.empty:
                     all_data = temp_series.to_frame()
                else:
                     all_data = pd.merge(all_data, temp_series.to_frame(), left_index=True, right_index=True, how='outer')
            except Exception as e:
                 print(f" Error processing data for {ticker}: {e}")
        else:
             print(f"⚠️ Data for {ticker} is missing 'date' or 'close' column.")


    if all_data.empty:
        print("❌ No valid historical data could be assembled into DataFrame.")
        return None, None

    # Ensure all_data has a proper datetime index and sort
    all_data = all_data.sort_index()

    # Fill missing values (e.g., holidays, different start dates)
    # Forward fill first, then backfill for any remaining NaNs at the beginning
    all_data = all_data.ffill().bfill()

    # Double-check if any NaNs remain after filling (shouldn't happen ideally)
    if all_data.isnull().values.any():
        print("⚠️ Warning: NaNs remain in price data after ffill/bfill. Check data sources.")
        # Option: Drop rows with any NaNs, but might lose data points
        # all_data = all_data.dropna()
        # If dropping leads to empty dataframe, return error
        # if all_data.empty:
        #    print("❌ Dataframe became empty after dropping NaNs.")
        #    return None, None


    print(f"📊 Assembled data spans from {all_data.index.min()} to {all_data.index.max()} for {len(valid_tickers)} tickers.")

    # Calculate portfolio values over time
    portfolio_values = pd.DataFrame(index=all_data.index)
    portfolio_values['value'] = 0.0  # Initialize with float

    print(f"💵 Using initial investment value: ${initial_investment:,.2f}")
    initial_ticker_values = {} # Stores {'ticker': {'shares': float, 'initial_day': datetime}}

    # Calculate initial shares based on first available price for each ticker
    print(" calculating initial shares based on first price...")
    for ticker in valid_tickers:
        if ticker not in all_data.columns: # Should not happen if logic above is correct, but check
            print(f" Ticker {ticker} unexpectedly not in all_data columns.")
            continue

        first_valid_idx = all_data[ticker].first_valid_index()
        if first_valid_idx is not None:
            initial_price = all_data.loc[first_valid_idx, ticker]
            if initial_price > 1e-9: # Avoid division by zero or tiny numbers
                allocation = allocation_dict.get(ticker, 0) # Get allocation safely
                # Use absolute allocation for share calculation magnitude
                adjusted_shares = (initial_investment * abs(allocation)) / initial_price
                # Apply sign based on original allocation (long/short)
                if allocation < 0:
                    adjusted_shares *= -1

                initial_ticker_values[ticker] = {
                    'shares': adjusted_shares,
                    'initial_day': first_valid_idx
                }
                # print(f"  {ticker}: Calculated {adjusted_shares:.4f} shares at ${initial_price:.2f} on {first_valid_idx.date()}")
            else:
                print(f"⚠️ Initial price for {ticker} on {first_valid_idx.date()} is zero or near-zero. Cannot calculate shares.")
                # Remove ticker from allocation_dict and valid_tickers if shares cannot be calculated?
                # Or assign 0 shares? Let's assign 0 shares for now.
                initial_ticker_values[ticker] = {'shares': 0.0, 'initial_day': first_valid_idx}
        else:
             print(f"⚠️ No valid price data found for {ticker} in the assembled data.")
             # Ticker effectively has 0 shares if no price data exists


    # Calculate daily portfolio value based on fixed shares and daily prices
    print(" calculating daily portfolio value...")
    for day in all_data.index:
        day_value = 0.0
        for ticker, initial_info in initial_ticker_values.items():
             shares = initial_info['shares']
             if abs(shares) > 1e-9 and ticker in all_data.columns: # Check if shares != 0 and ticker exists
                 current_price = all_data.loc[day, ticker]
                 # Check if current_price is NaN (can happen if bfill didn't cover start)
                 if pd.notna(current_price):
                     day_value += shares * current_price
                 # else: price is NaN, contribution is 0 for this day

        portfolio_values.loc[day, 'value'] = day_value


    # Ensure the first value is based on the actual initial investment if possible
    # The calculated value on the first day might differ slightly due to using first available prices
    # Option 1: Use calculated first day value (current implementation)
    # Option 2: Force first day value to be initial_investment
    # portfolio_values.iloc[0, portfolio_values.columns.get_loc('value')] = initial_investment

    # Handle cases where calculated value might be zero or negative if logic allows
    if (portfolio_values['value'] <= 1e-9).all():
         print("⚠️ Portfolio value remained zero or near-zero throughout the backtest period.")
         # Return empty results or handle as appropriate
         # return None, None # Let's allow it to proceed and show flat return for now

    # Calculate daily returns (use .loc to avoid potential SettingWithCopyWarning)
    # Remove deprecated fill_method
    portfolio_values['daily_return'] = portfolio_values['value'].pct_change()

    # Handle the first day's return (which is NaN after pct_change)
    portfolio_values.loc[portfolio_values.index[0], 'daily_return'] = 0.0

    # Fill any other NaNs that might arise (e.g., if value was 0 then became non-zero)
    portfolio_values['daily_return'] = portfolio_values['daily_return'].fillna(0)

    # Calculate cumulative returns with proper geometric compounding
    portfolio_values['cumulative_return'] = (1 + portfolio_values['daily_return']).cumprod() - 1

    # Verify consistency between value and returns (optional check)
    # calculated_values = initial_investment * (1 + portfolio_values['cumulative_return'])
    # value_discrepancy = np.abs(portfolio_values['value'] - calculated_values)
    # if (value_discrepancy > 1).any():  # Allow $1 tolerance
    #     print("⚠️ Warning: Value/return mismatch detected - check calculation logic")
    #     print("   Max discrepancy: ${:.2f}".format(value_discrepancy.max()))


    # --- Calculate Metrics ---
    print(" calculating performance metrics...")
    # Improved drawdown calculation
    portfolio_values['peak'] = portfolio_values['value'].cummax()
    # Avoid division by zero if peak is zero
    portfolio_values['drawdown'] = np.where(portfolio_values['peak'] > 1e-9,
                                           (portfolio_values['value'] - portfolio_values['peak']) / portfolio_values['peak'],
                                           0.0) # Set drawdown to 0 if peak is 0

    # Fill any potential NaNs/Infs arising from edge cases in drawdown calculation
    portfolio_values['drawdown'] = portfolio_values['drawdown'].replace([np.inf, -np.inf], np.nan).fillna(0)

    # Annualized return
    num_days = len(portfolio_values)
    trading_days_per_year = 252
    if num_days > 1:
         # Use the last cumulative return for CAGR calculation
         total_return_cumulative = portfolio_values['cumulative_return'].iloc[-1]
         # CAGR formula: (Ending Value / Beginning Value)^(1 / Num Years) - 1
         # (1 + total_return_cumulative)^(trading_days_per_year / num_days) - 1
         ann_return = (1 + total_return_cumulative) ** (trading_days_per_year / num_days) - 1
    elif num_days == 1:
         ann_return = portfolio_values['cumulative_return'].iloc[-1] # Total return if only 1 day
    else: # num_days == 0
         ann_return = 0.0

    # Calculate annualized volatility
    if num_days > 1:
        ann_volatility = portfolio_values['daily_return'].std() * np.sqrt(trading_days_per_year)
    else:
        ann_volatility = 0.0 # No volatility if <= 1 day

    # Calculate Sharpe ratio (assuming risk-free rate = 0)
    if ann_volatility > 1e-9:
        sharpe_ratio = ann_return / ann_volatility
    else:
        sharpe_ratio = 0.0 # Or np.nan, depending on desired output for zero volatility

    # Ensure no NaN values in the final 'value' (use last valid if needed)
    if pd.isna(portfolio_values['value'].iloc[-1]):
        last_valid_value = portfolio_values['value'].ffill().iloc[-1]
        portfolio_values.loc[portfolio_values.index[-1], 'value'] = last_valid_value


    print(f"📊 Portfolio calculated for {num_days} days")
    # Return calculated values and the allocation dict used (might have changed if data was missing)
    return portfolio_values, allocation_dict

def prepare_portfolio_json_from_db(portfolio_df: pd.DataFrame, total_portfolio_value: float = 1_000_000.0) -> Optional[Dict[str, Any]]:
    """
    Converts portfolio data from a DataFrame (ticker, allocation %) to the JSON
    format expected by the backtest function, calculating shares.

    Args:
        portfolio_df (pd.DataFrame): DataFrame with 'ticker' and 'allocation' columns.
                                     Allocation is a percentage (e.g., 6.500 for 6.5%).
        total_portfolio_value (float): The total initial value of the portfolio.

    Returns:
        dict: Portfolio in the JSON structure required by the backtest function.
              Returns None if essential data is missing or DataFrame is empty.
    """
    from src.portfolio_optimization.phase_two.data_retrieval import get_daily_closing_prices # LOCAL IMPORT
    if portfolio_df is None or portfolio_df.empty:
        print("⚠️ Portfolio DataFrame is empty or None. Cannot prepare JSON.")
        return None

    final_portfolio_list = []
    # Ensure 'ticker' column exists
    if 'ticker' not in portfolio_df.columns:
        print("⚠️ 'ticker' column missing in portfolio DataFrame.")
        return None
    # Ensure 'allocation' column exists
    if 'allocation' not in portfolio_df.columns:
        print("⚠️ 'allocation' column missing in portfolio DataFrame.")
        return None

    tickers_for_price_fetch = [ticker for ticker in portfolio_df['ticker'].unique() if pd.notna(ticker)]

    if not tickers_for_price_fetch:
        print("⚠️ No valid tickers found in portfolio DataFrame.")
        return None

    print("📊 Fetching initial prices for share calculation...")
    initial_prices = {}
    for ticker in tickers_for_price_fetch:
        price_data = get_daily_closing_prices(ticker)
        if price_data is not None and not price_data.empty and 'close' in price_data.columns:
            # Ensure there's at least one row before trying iloc[0]
            if not price_data['close'].empty:
                first_price = price_data['close'].iloc[0]
                if pd.notna(first_price) and first_price > 1e-9:
                    initial_prices[ticker] = first_price
                else:
                    print(f"⚠️ Could not get a valid first price for {ticker}. Skipping for share calculation.")
            else:
                print(f"⚠️ 'close' column is empty for {ticker}. Skipping for share calculation.")
        else:
            print(f"⚠️ No price data or invalid format for {ticker}. Skipping for share calculation.")


    for index, row in portfolio_df.iterrows():
        ticker = row.get('ticker')
        allocation_percent = row.get('allocation') # e.g., 6.500

        if pd.isna(ticker) or pd.isna(allocation_percent):
            print(f"⚠️ Skipping row with missing ticker or allocation: {row.to_dict()}")
            continue

        shares_str = "0"
        if ticker in initial_prices:
            current_price = initial_prices[ticker]
            try:
                alloc_float = float(allocation_percent)
                monetary_allocation = total_portfolio_value * (alloc_float / 100.0)
                if current_price > 1e-9:
                    calculated_shares = monetary_allocation / current_price
                    shares_str = str(int(round(calculated_shares)))
                else:
                    print(f"ℹ️ Initial price for {ticker} is zero or near-zero. Shares set to 0.")
            except ValueError:
                print(f"⚠️ Invalid allocation format for {ticker}: {allocation_percent}. Shares set to 0.")
        else:
            print(f"ℹ️ Shares for {ticker} defaulted to 0 (missing initial price). Backtest will rely on allocation percentage.")

        final_portfolio_list.append({
            "ticker": str(ticker),
            "position_type": "LONG",
            "shares": shares_str,
            "allocation": f"{float(allocation_percent):.2f}%" # Ensure allocation is formatted
        })

    if not final_portfolio_list:
        print("❌ Could not construct any valid portfolio items from the DataFrame.")
        return None

    return {"final_portfolio": final_portfolio_list} 