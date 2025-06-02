import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Any, Dict, Optional
from backend.src.utils.retrieve_portfolio_from_db import retrieve_portfolio_information_from_db
from .backtest_helpers import (
    get_historical_data_for_all_tickers,
    calculate_portfolio_returns,
    prepare_portfolio_json_from_db
)

def backtest(portfolio_json: Dict[str, Any]):
    """
    Runs a backtest for a given portfolio JSON configuration.

    Args:
        portfolio_json: Dictionary containing the portfolio definition (e.g., json, json2, etc.)
    """
    # Get historical data for all tickers for the given portfolio
    print(f"\n📊 Fetching historical data for portfolio...")
    # Make sure get_historical_data_for_all_tickers returns dataframes or None
    historical_data, portfolio_value = get_historical_data_for_all_tickers(portfolio_json)

    # --- Initial Data Check ---
    if not historical_data:
        print("❌ Failed to fetch any historical data. Cannot proceed.")
        return
    if portfolio_value is None: # portfolio_value is returned by get_historical_data_for_all_tickers
        print("⚠️ Failed to fetch portfolio value, using default $1,000,000.")
        portfolio_value = 1000000

    # Check if SPY data is present, needed for comparison plot
    if "SPY" not in historical_data or historical_data["SPY"] is None or historical_data["SPY"].empty:
         print("⚠️ SPY historical data not found or empty. Comparison plot will exclude SPY.")

    # Disable IBKR connection in this offline mode
    # connect_to_ib = lambda *args, **kwargs: None

    # Get current holdings (optional, for comparison - uses default account)
    print("\n💼 Skipping live IBKR holdings fetch (offline mode)...")
    current_holdings = None # Logic for current_holdings remains, using None


    print("\n🔍 Summary of historical data fetched:")
    valid_data_count = 0
    for ticker, data in historical_data.items():
        # Check if data is a DataFrame and not empty
        if isinstance(data, pd.DataFrame) and not data.empty:
            print(f"  {ticker}: {len(data)} bars retrieved")
            valid_data_count +=1
        # Allow None or empty for SPY if fetch failed, but note it
        elif ticker == "SPY" and (data is None or data.empty):
             print(f"  {ticker}: Data missing or empty.")
        elif data is not None: # If not None and not DataFrame/empty
             print(f"  {ticker}: Data retrieved but not in expected format or empty.")
        # else: data is None (already handled for SPY)


    if valid_data_count == 0:
        print("❌ No valid historical data retrieved for any ticker. Cannot proceed with backtest.")
        return

    # Calculate portfolio returns using the provided portfolio json
    print("\n📈 Calculating portfolio returns...")
    # Pass the potentially modified portfolio_value
    portfolio_values, allocation_dict = calculate_portfolio_returns(portfolio_json, historical_data, portfolio_value)

    if portfolio_values is None or portfolio_values.empty:
         print("❌ Failed to calculate portfolio returns. Cannot generate plot.")
         return # Exit if calculation failed

    # --- Plotting and Metrics ---
    print("\n📊 Portfolio Performance Summary:")
    print(f"Initial Portfolio Value: ${portfolio_values['value'].iloc[0]:,.2f}")
    final_val = portfolio_values['value'].iloc[-1]
    print(f"Final Portfolio Value: ${final_val:,.2f}")

    # Ensure final value is not NaN before calculating total return
    if pd.isna(portfolio_values['cumulative_return'].iloc[-1]):
         print("⚠️ Final cumulative return is NaN. Cannot calculate Total Return.")
         total_return_pct = np.nan
    else:
         total_return_pct = portfolio_values['cumulative_return'].iloc[-1] * 100
         print(f"Total Return: {total_return_pct:.2f}%")


    # Print daily returns information
    print("\n📅 Daily Returns Summary:")
    print(f"Mean Daily Return: {portfolio_values['daily_return'].mean() * 100:.4f}%")
    print(f"Std Dev of Daily Returns: {portfolio_values['daily_return'].std() * 100:.4f}%")
    print(f"Min Daily Return: {portfolio_values['daily_return'].min() * 100:.4f}%")
    print(f"Max Daily Return: {portfolio_values['daily_return'].max() * 100:.4f}%")

    # Print portfolio allocation information (using the final dict from calculation)
    print("\n💰 Portfolio Allocation Used (Normalized, After Data Checks):")
    if allocation_dict:
        for ticker, allocation in allocation_dict.items():
            print(f"{ticker}: {allocation*100:.2f}%")
    else:
        print("  No allocations were used in the calculation (likely due to missing data).")


    # Recalculate metrics based on returned portfolio_values DataFrame
    # (Metrics calculation is now inside calculate_portfolio_returns, just print them here)
    num_days = len(portfolio_values)
    trading_days_per_year = 252

    if num_days > 1:
        total_return_cumulative = portfolio_values['cumulative_return'].iloc[-1]
        if pd.notna(total_return_cumulative):
             ann_return = (1 + total_return_cumulative) ** (trading_days_per_year / num_days) - 1
        else:
             ann_return = np.nan # If total return is NaN, annualized is NaN
    elif num_days == 1:
        ann_return = portfolio_values['cumulative_return'].iloc[-1]
    else:
        ann_return = 0.0

    if num_days > 1:
        ann_volatility = portfolio_values['daily_return'].std() * np.sqrt(trading_days_per_year)
    else:
        ann_volatility = 0.0

    if pd.notna(ann_return) and pd.notna(ann_volatility) and ann_volatility > 1e-9:
        sharpe_ratio = ann_return / ann_volatility
    else:
        sharpe_ratio = np.nan # Sharpe is NaN if ann_return or ann_volatility is NaN or volatility is zero

    max_drawdown = portfolio_values['drawdown'].min() * 100

    # Get max drawdown date - convert to readable format
    try:
        # Ensure drawdown series is not all zeros before finding idxmin
        if not (portfolio_values['drawdown'] == 0).all():
            min_idx = portfolio_values['drawdown'].idxmin()
            max_drawdown_date = min_idx.strftime('%Y-%m-%d') if isinstance(min_idx, pd.Timestamp) else "Date not found"
        else:
            max_drawdown_date = "N/A (No drawdown)"
    except Exception as e:
        print(f"Error getting drawdown date: {e}")
        max_drawdown_date = "Date calculation error"

    print("\n📈 Calculated Metrics:")
    print(f"Annualized Return: {ann_return*100:.2f}%" if pd.notna(ann_return) else "Annualized Return: N/A")
    print(f"Annualized Volatility: {ann_volatility*100:.2f}%" if pd.notna(ann_volatility) else "Annualized Volatility: N/A")
    print(f"Sharpe Ratio: {sharpe_ratio:.2f}" if pd.notna(sharpe_ratio) else "Sharpe Ratio: N/A")
    print(f"Maximum Drawdown: {max_drawdown:.2f}%")
    print(f"Maximum Drawdown Date: {max_drawdown_date}")

    # --- Plotting ---
    print("\n🖼️ Generating performance plot...")
    fig = go.Figure()

    # Add optimized portfolio cumulative returns trace
    fig.add_trace(
        go.Scatter(
            x=portfolio_values.index,
            y=portfolio_values['cumulative_return'] * 100,
            mode='lines',
            name='Optimized Portfolio',
            line=dict(color='#2ecc71', width=2)
        )
    )

    # Add SPY cumulative returns trace
    if 'SPY' in historical_data and isinstance(historical_data['SPY'], pd.DataFrame) and not historical_data['SPY'].empty:
        spy_data = historical_data['SPY']
        if 'date' in spy_data.columns and 'close' in spy_data.columns:
            spy_df = pd.DataFrame({'close': spy_data['close'].values}, index=pd.to_datetime(spy_data['date']))
            spy_df = spy_df.reindex(portfolio_values.index).ffill().bfill() # Align dates

            if not spy_df.empty and not spy_df['close'].isnull().all():
                 # Remove deprecated fill_method
                 spy_returns = spy_df['close'].pct_change().fillna(0)
                 spy_cumulative = (1 + spy_returns).cumprod() - 1

                 fig.add_trace(
                     go.Scatter(
                         x=spy_df.index,
                         y=spy_cumulative * 100,
                         mode='lines',
                         name='SPY Returns',
                         line=dict(color='#3498db', width=2)
                     )
                 )
        else:
            print("  SPY data missing expected 'date' or 'close' columns.")
    # else: Already printed warning about missing SPY earlier


    # --- Calculate and add current portfolio returns if available ---
    if current_holdings:
        print("\n🔄 Calculating returns for current portfolio holdings (for comparison plot)...")
        # Filter out holdings with zero shares or market value
        valid_holdings = {
            symbol: data for symbol, data in current_holdings.items()
            if data.get('shares', 0) != 0 and data.get('market_value', 0) != 0
        }

        if not valid_holdings:
             print("  No valid current holdings (with non-zero shares and market value) found.")
        else:
            symbols_to_fetch = list(valid_holdings.keys())
            print(f"  Fetching historical data for {len(symbols_to_fetch)} current holding symbols: {', '.join(symbols_to_fetch)}")

            # --- Fetch data for current holdings ONCE ---
            current_holdings_data = {}
            # ib_conn_plot = connect_to_ib() # Connect once for this plotting task
            # if ib_conn_plot:
            #     try:
            #         for symbol in symbols_to_fetch:
            #             print(f"    Fetching for {symbol}...")
            #             data = get_ib_historical_data(ib_conn_plot, symbol)
            #             if isinstance(data, pd.DataFrame) and not data.empty:
            #                 current_holdings_data[symbol] = data
            #             else:
            #                 print(f"    ⚠️ Failed to get valid data for {symbol}")
            #     except Exception as e:
            #          print(f"    ❌ Error fetching data for current holdings: {e}")
            # else:
            #      print("  ⚠️ Could not connect to IB to fetch data for current holdings plot.")
            # --- End data fetching ---


            if not current_holdings_data:
                 print("  ⚠️ Failed to fetch historical data for any current holdings. Cannot plot comparison.")
            else:
                # --- Calculate returns using fetched data ---
                current_portfolio_df = pd.DataFrame(index=portfolio_values.index) # Initialize DataFrame for current returns
                all_current_returns = pd.DataFrame(index=portfolio_values.index) # Store weighted returns per symbol
                total_current_value = sum(abs(holding.get('market_value', 0)) for holding in valid_holdings.values()) # Recalculate total value using only valid holdings

                calculation_successful = False
                if total_current_value > 1e-9: # Check again in case valid_holdings changed
                    print("  Calculating weighted returns for current holdings...")
                    for symbol, holding_data in current_holdings_data.items():
                         # Holding info (shares, market value) is from valid_holdings
                         holding_info = valid_holdings[symbol]
                         market_value = holding_info.get('market_value', 0)
                         weight = market_value / total_current_value # Use signed value

                         if 'date' in holding_data.columns and 'close' in holding_data.columns:
                             symbol_df = pd.DataFrame({'close': holding_data['close'].values}, index=pd.to_datetime(holding_data['date']))
                             symbol_df = symbol_df.reindex(portfolio_values.index).ffill().bfill() # Align dates

                             if not symbol_df.empty and not symbol_df['close'].isnull().all():
                                 # Remove deprecated fill_method
                                 symbol_returns = symbol_df['close'].pct_change().fillna(0)
                                 weighted_returns = symbol_returns * weight
                                 all_current_returns[symbol] = weighted_returns # Store weighted returns per symbol
                                 calculation_successful = True # Mark success if at least one symbol processed
                         else:
                              print(f"    ⚠️ Data for current holding {symbol} missing 'date' or 'close'.")

                    if calculation_successful:
                        # Sum weighted returns across all symbols for each day
                        current_portfolio_df['returns'] = all_current_returns.sum(axis=1, skipna=True) # Sum returns, skip NaNs
                        current_portfolio_df['returns'] = current_portfolio_df['returns'].fillna(0) # Fill any remaining NaNs from sum
                        current_portfolio_df['cumulative'] = (1 + current_portfolio_df['returns']).cumprod() - 1

                        # Add the trace for current portfolio
                        fig.add_trace(
                            go.Scatter(
                                x=current_portfolio_df.index,
                                y=current_portfolio_df['cumulative'] * 100,
                                mode='lines',
                                name='Current Portfolio (Estimate)',
                                line=dict(color='#e74c3c', width=2)
                            )
                        )
                        print("  Current portfolio comparison returns calculated and added to plot.")
                    else:
                         print("  ⚠️ No valid returns could be calculated for any current holdings symbols.")

                else: # total_current_value is 0 or near-zero
                    print("  ⚠️ Total market value of valid current holdings is zero, cannot calculate comparison returns.")
                # --- End return calculation ---


    # Update layout for a clean, professional look
    fig.update_layout(
        title='Portfolio Performance Comparison',
        height=600,
        showlegend=True,
        xaxis_title='Date',
        yaxis_title='Cumulative Returns (%)',
        hovermode='x unified',
        template='plotly_white',
        legend_title_text='Portfolio',
        margin=dict(t=50, l=50, r=50, b=50),
        yaxis=dict(
            tickformat='.1f', # Format y-axis ticks
            gridcolor='lightgrey',
            gridwidth=1,
            zeroline=True, zerolinecolor='grey', zerolinewidth=1
        ),
        xaxis=dict(
            gridcolor='lightgrey',
            gridwidth=1,
            showgrid=True # Ensure x-axis grid is shown
        )
    )

    # Display the plot
    print("\n🖼️ Displaying performance plot...")
    fig.show()

if __name__ == "__main__":
    assumed_initial_portfolio_value = 10_000.0

    test_schema = "portfolio_twenty"
    table_name = "final_portfolio"
    print(f"🔄 Retrieving portfolio information from DB: {test_schema}.{table_name}...")
    portfolio_df = retrieve_portfolio_information_from_db(test_schema, table_name)

    if portfolio_df is not None and not portfolio_df.empty:
        print(f"✅ Successfully retrieved {len(portfolio_df)} records from the database.")
        print("🔄 Preparing portfolio JSON from DataFrame...")
        portfolio_to_backtest = prepare_portfolio_json_from_db(portfolio_df, assumed_initial_portfolio_value)

        if portfolio_to_backtest:
            print(f"🚀 Running backtest for generated portfolio from DB data...")
            # For debugging, you can print the generated JSON:
            # import json
            # print("Generated Portfolio JSON:", json.dumps(portfolio_to_backtest, indent=2))
            backtest(portfolio_to_backtest)
        else:
            print("❌ Failed to prepare portfolio JSON from DataFrame. Backtest aborted.")
    elif portfolio_df is not None and portfolio_df.empty:
        print(f"ℹ️ No data found in {test_schema}.{table_name}. Cannot run backtest.")
    else:
        print(f"❌ Failed to retrieve portfolio data from {test_schema}.{table_name}. Backtest aborted.")

