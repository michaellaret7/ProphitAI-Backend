import json
from src.data.PortfolioData import get_portfolio_holdings, analyze_portfolio_correlations, calculate_portfolio_metrics, calculate_monthly_portfolio_metrics, calculate_monthly_stock_metrics, analyze_portfolio_diversification, analyze_portfolio_correlations
from src.utils.ib_utils import connect_to_ib, disconnect_from_ib, get_ib
from openai import OpenAI
import numpy as np
import os
from datetime import datetime
import psycopg2
import pandas as pd
import re
import time 
import sys
import random
import itertools
import threading
import math
import curses


# Initialize IB connection function
def initialize_ib_connection():
    """
    Establishes a connection to Interactive Brokers and returns the connection object.
    
    Returns:
        The IB connection object or None if connection fails
    """
    try:
        print("Establishing connection to Interactive Brokers...")
        ib = get_ib()  # Using the get_ib function from ib_utils
        if ib:
            print("Connection to Interactive Brokers established successfully")
        else:
            print("Failed to establish connection to Interactive Brokers")
        return ib
    except Exception as e:
        print(f"Error establishing connection to Interactive Brokers: {e}")
        return None

# Close IB connection function
def close_ib_connection(ib):
    """
    Properly closes the connection to Interactive Brokers.
    
    Args:
        ib: The IB connection object to close
    """
    try:
        if ib and hasattr(ib, 'isConnected') and ib.isConnected():
            print("Closing connection to Interactive Brokers...")
            disconnect_from_ib()  # Using the disconnect_from_ib function from ib_utils
            print("Connection to Interactive Brokers closed successfully")
    except Exception as e:
        print(f"Error closing connection to Interactive Brokers: {e}")

# Initialize empty data structures
positions = []
formatted_output = "No connection to Interactive Brokers"
metrics = {}
monthly_results = {}
aapl_results = {}
diversification = {}
correlations = "No correlation data available"

# Variables to track if data has been fetched
_data_fetched = False

def format_portfolio_positions(positions_data):
    """
    Transform raw portfolio positions into LLM-friendly format
    """
    # Check if positions_data is a tuple (raw output from run())
    if isinstance(positions_data, tuple) and len(positions_data) >= 1:
        # Extract the actual positions list from the tuple
        positions_data = positions_data[0]
    
    # Convert raw positions data to structured format
    positions_json = []
    
    for position in positions_data:
        positions_json.append({
            "symbol": position["contract"].symbol,
            "quantity": position["position"],
            "avg_cost": position["averageCost"],
            "market_value": position["marketValue"],
            "current_price": position["marketPrice"],
            "unrealized_pnl": position["unrealizedPNL"],
            "account": position["account"]
        })
    
    # Determine the maximum width for each column
    col_data = {
        "symbol": {"content": [p["contract"].symbol for p in positions_data], "align": "left", "header": "Symbol"},
        "quantity": {"content": [f"{p['position']:,.2f}" for p in positions_data], "align": "right", "header": "Quantity"},
        "avg_cost": {"content": [f"${p['averageCost']:,.2f}" for p in positions_data], "align": "right", "header": "Avg Cost"},
        "market_value": {"content": [f"${p['marketValue']:,.2f}" for p in positions_data], "align": "right", "header": "Market Value"},
        "current_price": {"content": [f"${p['marketPrice']:,.2f}" for p in positions_data], "align": "right", "header": "Current Price"},
        "unrealized_pnl": {"content": [f"${p['unrealizedPNL']:,.2f}" for p in positions_data], "align": "right", "header": "Unrealized P&L"}
    }
    
    # Calculate widths - consider both header and content width
    widths = {}
    for col, data in col_data.items():
        content_width = max(len(item) for item in data["content"])
        header_width = len(data["header"])
        widths[col] = max(content_width, header_width) + 2  # Add padding
    
    # Build table
    rows = []
    
    # Header row
    header_cells = []
    for col, data in col_data.items():
        if data["align"] == "left":
            header_cells.append(data["header"].ljust(widths[col]))
        else:
            header_cells.append(data["header"].rjust(widths[col]))
    rows.append(f"| {' | '.join(header_cells)} |")
    
    # Separator row with correct alignment indicators
    separator_cells = []
    for col, data in col_data.items():
        if data["align"] == "left":
            separator_cells.append(":" + "-" * (widths[col] - 1))
        else:
            separator_cells.append("-" * (widths[col] - 1) + ":")
    rows.append(f"| {' | '.join(separator_cells)} |")
    
    # Data rows
    for i in range(len(positions_data)):
        cells = []
        for col, data in col_data.items():
            content = data["content"][i]
            if data["align"] == "left":
                cells.append(content.ljust(widths[col]))
            else:
                cells.append(content.rjust(widths[col]))
        rows.append(f"| {' | '.join(cells)} |")
    
    # Generate summary statistics
    total_value = sum(p["marketValue"] for p in positions_data)
    total_pnl = sum(p["unrealizedPNL"] for p in positions_data)
    
    # Create position summary
    summary = {
        "total_positions": len(positions_data),
        "total_market_value": total_value,
        "total_unrealized_pnl": total_pnl,
        "percent_pnl": (total_pnl / total_value) * 100 if total_value > 0 else 0
    }
    
    # Format summary as a table with consistent widths
    # Prepare summary data
    summary_rows = [
        {"metric": "**Total Positions**", "value": f"{summary['total_positions']}"},
        {"metric": "**Total Market Value**", "value": f"${summary['total_market_value']:,.2f}"},
        {"metric": "**Total Unrealized P&L**", "value": f"${summary['total_unrealized_pnl']:,.2f}"},
        {"metric": "**Percent P&L**", "value": f"{summary['percent_pnl']:.2f}%"}
    ]
    
    # Calculate width needed for each column
    metric_width = max(len(row["metric"]) for row in summary_rows) + 2
    value_width = max(len(row["value"]) for row in summary_rows) + 2
    
    # Build summary table
    summary_table = "\n\n### Portfolio Summary\n\n"
    summary_table += f"| {'Metric'.ljust(metric_width)} | {'Value'.ljust(value_width)} |\n"
    summary_table += f"| {':' + '-' * (metric_width - 1)} | {':' + '-' * (value_width - 1)} |\n"
    
    for row in summary_rows:
        summary_table += f"| {row['metric'].ljust(metric_width)} | {row['value'].ljust(value_width)} |\n"
    
    # Combine tables - no longer combining
    positions_table = "\n".join(rows)
    
    # Return combined format
    return {
        "positions_json": positions_json,
        "positions_table": positions_table,
        "summary_table": summary_table,
        "summary": summary,
        "formatted_output": formatted_output
    }

def extract_account_info(formatted_output):
    """
    Extracts and formats CASH BALANCES, ACCOUNT METRICS, and ALLOCATION SUMMARY 
    into a clean table format.
    
    Args:
        formatted_output: The full formatted output string from run_account_data()
        
    Returns:
        A string containing the formatted tables
    """
    # Split the output into lines
    output_lines = formatted_output.split('\n')
    
    # Initialize section trackers
    sections = {
        "CASH BALANCES": [],
        "ACCOUNT METRICS": [],
        "ALLOCATION SUMMARY": []
    }
    
    current_section = None
    
    # Extract the sections we want
    for line in output_lines:
        # Identify section headers (with or without emojis)
        if any(section in line for section in sections.keys()):
            for section in sections.keys():
                if section in line:
                    current_section = section
                    break
        elif current_section and line.strip() and "---" not in line:
            # Skip separator lines and add content lines to the current section
            sections[current_section].append(line.strip())
    
    # Add risk metrics section if provided
    if metrics is not None:
        sections["PORTFOLIO RISK METRICS"] = []
        # Format the metrics into table rows
        for key, value in metrics.items():
            # Format the metric name to be more readable
            readable_key = " ".join(word.capitalize() for word in key.split('_'))
            # Format numeric values
            if isinstance(value, (int, float)):
                formatted_value = f"{value:.4f}" if isinstance(value, float) else str(value)
                sections["PORTFOLIO RISK METRICS"].append(f"{readable_key} | {formatted_value}")
    
    # Find the max widths across ALL sections for consistency
    max_desc_width = 0
    max_value_width = 0
    
    # First pass to find maximum widths
    for section, lines in sections.items():
        for line in lines:
            if '|' in line:
                parts = [part.strip() for part in line.split('|')]
                if len(parts) >= 2:
                    max_desc_width = max(max_desc_width, len(parts[0]))
                    max_value_width = max(max_value_width, len(parts[1]))
    
    # Add some padding
    max_desc_width += 2
    max_value_width += 2
    
    # Add header lengths to consideration
    max_desc_width = max(max_desc_width, len("Description"))
    max_value_width = max(max_value_width, len("Value"))
    
    # Format the tables
    result = []
    
    # Add each section as a clean table
    for section, lines in sections.items():
        # Add section header
        result.append(f"\n### {section}")
        result.append("")
        
        # Format header
        result.append(f"| {'Description'.ljust(max_desc_width)} | {'Value'.ljust(max_value_width)} |")
        result.append(f"| {'-' * max_desc_width} | {'-' * max_value_width} |")
        
        # Format rows - using the consistent max widths
        for line in lines:
            if '|' in line:
                parts = [part.strip() for part in line.split('|')]
                if len(parts) >= 2:
                    result.append(f"| {parts[0].ljust(max_desc_width)} | {parts[1].rjust(max_value_width)} |")
        
        result.append("")
    
    return "\n".join(result)

def format_portfolio_metrics(metrics):
    """Format the overall portfolio metrics into a neat table."""
    output = "PORTFOLIO METRICS\n\n"
    
    # Check if we have position weights info
    if 'using_position_weights' in metrics:
        output += f"Using position market value weights for portfolio returns calculation\n\n"
    
    # Format the main metrics
    output += f"Total Return: {metrics['total_return']*100:.2f}%\n"
    output += f"Annualized Return: {metrics['annualized_return']*100:.2f}%\n"
    output += f"Market Total Return (SPY): {metrics['market_total_return']*100:.2f}%\n"
    output += f"Market Annualized Return (SPY): {metrics['market_annualized_return']*100:.2f}%\n"
    output += f"Volatility (annualized): {metrics['volatility']*100:.2f}%\n"
    output += f"Beta: {metrics['beta']:.2f}\n"
    output += f"Alpha: {metrics['alpha']*100:.2f}%\n"
    output += f"Historical VaR (99%): {metrics['historical_var_pct']*100:.2f}% (${metrics['historical_var_amount']:.2f})\n"
    output += f"Parametric VaR (99%): {metrics['parametric_var_pct']*100:.2f}% (${metrics['parametric_var_amount']:.2f})\n"
    output += f"Maximum Drawdown: {metrics['max_drawdown']*100:.2f}%\n"
    output += f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}\n"
    output += f"Calmar Ratio: {metrics['calmar_ratio']:.2f}\n"
    output += f"Sortino Ratio: {metrics['sortino_ratio']:.2f}\n"
    
    return output

def format_stock_metrics(metrics):
    """Format the individual stock metrics into a neat table."""
    output = "INDIVIDUAL STOCK METRICS\n\n"
    
    # Get all stock symbols
    stock_metrics = metrics.get('stock_metrics', {})
    symbols = list(stock_metrics.keys())
    
    if not symbols:
        return output + "No individual stock metrics available.\n"
    
    # Determine column widths based on content (symbol width)
    symbol_width = max(8, max(len(symbol) for symbol in symbols))
    
    # Metrics to display and their formatting
    metrics_to_display = [
        ("Total Return", lambda x: f"{x['total_return']*100:.2f}%"),
        ("Annualized Return", lambda x: f"{x['annualized_return']*100:.2f}%"),
        ("Volatility", lambda x: f"{x['volatility']*100:.2f}%"),
        ("Beta", lambda x: f"{x['beta']:.2f}"),
        ("Alpha", lambda x: f"{x['alpha']*100:.2f}%"),
        ("Historical VaR (99%)", lambda x: f"{x.get('var_pct', 0)*100:.2f}%"),
        ("Maximum Drawdown", lambda x: f"{x['max_drawdown']*100:.2f}%"),
        ("Sharpe Ratio", lambda x: f"{x['sharpe_ratio']:.2f}"),
        ("Calmar Ratio", lambda x: f"{x['calmar_ratio']:.2f}"),
        ("Sortino Ratio", lambda x: f"{x['sortino_ratio']:.2f}")
    ]
    
    # Determine the width needed for each column based on the actual formatted values
    # First, format all values to see how wide each will be
    formatted_values = {}
    for metric_name, format_func in metrics_to_display:
        formatted_values[metric_name] = []
        for symbol in symbols:
            try:
                formatted_values[metric_name].append(format_func(stock_metrics[symbol]))
            except:
                formatted_values[metric_name].append("N/A")
    
    # Calculate max width needed for each symbol's column
    column_widths = {}
    for symbol_idx, symbol in enumerate(symbols):
        # Initialize with the symbol width
        column_widths[symbol] = len(symbol)
        
        # Check each metric's formatted width for this symbol
        for metric_name in formatted_values:
            val_width = len(formatted_values[metric_name][symbol_idx])
            column_widths[symbol] = max(column_widths[symbol], val_width)
    
    # Add some padding
    for symbol in column_widths:
        column_widths[symbol] += 1
    
    # Define the metric name column width
    metric_name_width = max(20, max(len(metric_name) for metric_name, _ in metrics_to_display))
    
    # Create the header row with proper widths
    header = f"{'Metric':<{metric_name_width}} | " + " | ".join(f"{symbol:<{column_widths[symbol]}}" for symbol in symbols)
    output += header + "\n"
    output += "-" * len(header) + "\n"
    
    # Add each metric row with proper column widths
    for metric_idx, (metric_name, _) in enumerate(metrics_to_display):
        row = f"{metric_name:<{metric_name_width}} | "
        values_row = []
        
        for symbol_idx, symbol in enumerate(symbols):
            value = formatted_values[metric_name][symbol_idx]
            values_row.append(f"{value:<{column_widths[symbol]}}")
            
        row += " | ".join(values_row)
        output += row + "\n"
    
    return output

def format_monthly_performance(monthly_results):
    """Format the monthly portfolio performance into a neat table."""
    output = "MONTHLY PORTFOLIO PERFORMANCE ANALYSIS\n\n"
    
    # Get monthly metrics and sort by date
    monthly_metrics = monthly_results.get('monthly_metrics', {})
    sorted_months = sorted(monthly_metrics.keys())
    
    if not sorted_months:
        return output + "No monthly performance data available.\n"
    
    # Determine column widths for better alignment
    month_width = max(10, max(len(month) for month in sorted_months))
    return_width = 8
    spy_width = 8
    alpha_width = 9
    beta_width = 6
    vol_width = 7
    maxdd_width = 7
    sharpe_width = 8
    sortino_width = 8
    
    # Create the header with proper widths
    header = (f"{'Month':<{month_width}} | {'Return':<{return_width}} | {'vs SPY':<{spy_width}} | "
             f"{'Alpha':<{alpha_width}} | {'Beta':<{beta_width}} | {'Vol':<{vol_width}} | {'MaxDD':<{maxdd_width}} | "
             f"{'Sharpe':<{sharpe_width}} | {'Sortino':<{sortino_width}}")
    output += header + "\n"
    output += "-" * len(header) + "\n"
    
    # Add each month's data
    for month in sorted_months:
        data = monthly_metrics[month]
        row = (
            f"{month:<{month_width}} | "
            f"{data['total_return']*100:6.2f}%  | "
            f"{data['relative_performance']*100:6.2f}%  | "
            f"{data['alpha']*100:7.2f}%  | "
            f"{data['beta']:4.2f}  | "
            f"{data['volatility']*100:5.2f}%  | "
            f"{data['max_drawdown']*100:5.2f}%  | "
            f"{data['sharpe_ratio']:6.2f}  | "
            f"{data.get('sortino_ratio', 0):6.2f}"
        )
        output += row + "\n"
    
    # Add summary statistics
    output += "\n\nMONTHLY SUMMARY STATISTICS\n\n"
    
    positive_months = sum(1 for month in monthly_metrics.values() if month['total_return'] > 0)
    outperforming_months = sum(1 for month in monthly_metrics.values() if month['relative_performance'] > 0)
    total_months = len(monthly_metrics)
    
    output += f"Total Months Analyzed: {total_months}\n"
    if total_months > 0:
        output += f"Positive Return Months: {positive_months} ({positive_months/total_months*100:.1f}%)\n"
        output += f"Months Outperforming SPY: {outperforming_months} ({outperforming_months/total_months*100:.1f}%)\n\n"
    
        # Find best and worst months
        best_month = max(monthly_metrics.items(), key=lambda x: x[1]['total_return'])
        worst_month = min(monthly_metrics.items(), key=lambda x: x[1]['total_return'])
        
        output += f"Best Month: {best_month[0]} with {best_month[1]['total_return']*100:.2f}% return\n"
        output += f"Worst Month: {worst_month[0]} with {worst_month[1]['total_return']*100:.2f}% return\n"
    
    return output

def format_stock_analysis(symbol, monthly_results=None, stock_metrics=None):
    """Format the analysis for a specific stock."""
    output = f"STOCK ANALYSIS FOR {symbol}\n\n"
    
    # Check if we have valid input data
    if not monthly_results or not stock_metrics:
        return output + f"No data available for {symbol}.\n"
    
    # For AAPL specifically, check if the data might be under 'aapl_results' in monthly_results
    if symbol.upper() == "AAPL" and hasattr(monthly_results, 'get'):
        if monthly_results.get('aapl_results'):
            monthly_results = monthly_results.get('aapl_results')
    
    # Format the monthly performance table
    # Check all possible structures for monthly stock data
    stock_monthly = {}
    
    # Try different possible locations and structures for finding the stock data
    if isinstance(monthly_results, dict):
        # Check if stock_monthly is a direct key
        if 'stock_monthly' in monthly_results and symbol in monthly_results['stock_monthly']:
            stock_monthly = monthly_results['stock_monthly'][symbol]
        # Check if symbol is a direct key
        elif symbol in monthly_results and isinstance(monthly_results[symbol], dict):
            stock_monthly = monthly_results[symbol]
        # Check if it's in a list form
        elif symbol in monthly_results and isinstance(monthly_results[symbol], list) and len(monthly_results[symbol]) > 0:
            # Try to convert list to dict if possible
            try:
                stock_monthly = {f"Month_{i+1}": item for i, item in enumerate(monthly_results[symbol])}
            except:
                pass
        # For AAPL, it might be directly under monthly_results instead of as a key
        elif symbol.upper() == "AAPL" and isinstance(monthly_results, dict) and any(
            key.startswith('20') for key in monthly_results.keys()
        ):
            # The monthly_results itself might be the AAPL data
            stock_monthly = monthly_results
    
    # Debug section in format_stock_analysis
    if not stock_monthly and symbol.upper() == "AAPL":
        output += f"DEBUG: Could not find monthly data for {symbol}. Available keys in monthly_results:\n"
        if isinstance(monthly_results, dict):
            key_list = list(monthly_results.keys())
            output += f"Keys: {', '.join(str(k) for k in key_list[:10] if k is not None)}\n"
            
            # Look for any keys related to AAPL
            aapl_related_keys = [k for k in key_list if k is not None and 'aapl' in str(k).lower()]
            if aapl_related_keys:
                output += f"AAPL related keys: {', '.join(str(k) for k in aapl_related_keys)}\n"
    
    if stock_monthly:
        output += f"MONTHLY PERFORMANCE FOR {symbol}\n\n"
        
        # Sort months chronologically
        sorted_months = sorted(stock_monthly.keys())
        
        # Ensure we have data to analyze
        if not sorted_months:
            output += f"No monthly data available for {symbol}.\n"
            return output
        
        # Determine column widths
        month_width = max(10, max(len(str(month)) for month in sorted_months))
        
        # Create header with proper widths
        header = (f"{'Month':<{month_width}} | {'Return':<8} | {'vs SPY':<8} | {'Alpha':<9} | "
                 f"{'Beta':<6} | {'Volatility':<10} | {'MaxDD':<8} | {'Sharpe':<8}")
        output += header + "\n"
        output += "-" * len(header) + "\n"
        
        for month in sorted_months:
            data = stock_monthly[month]
            
            # Handle different key naming conventions and ensure numeric values
            try:
                return_val = float(data.get('return', data.get('total_return', 0)))
                vs_spy = float(data.get('vs_spy', data.get('relative_performance', 0)))
                alpha = float(data.get('alpha', 0))
                beta = float(data.get('beta', 0))
                volatility = float(data.get('volatility', 0))
                max_drawdown = float(data.get('max_drawdown', 0))
                sharpe_ratio = float(data.get('sharpe_ratio', 0))
                
                row = (
                    f"{str(month):<{month_width}} | "
                    f"{return_val*100:6.2f}%  | "
                    f"{vs_spy*100:6.2f}%  | "
                    f"{alpha*100:7.2f}%  | "
                    f"{beta:4.2f}  | "
                    f"{volatility*100:8.2f}%  | "
                    f"{max_drawdown*100:6.2f}%  | "
                    f"{sharpe_ratio:6.2f}"
                )
                output += row + "\n"
            except (TypeError, ValueError) as e:
                # Skip any rows with invalid data
                continue
        
        # Add summary statistics
        output += "\nMONTHLY SUMMARY STATISTICS\n\n"
        
        # Get return and vs_spy values accounting for different key naming
        returns = []
        vs_spy_vals = []
        
        for data in stock_monthly.values():
            try:
                ret = float(data.get('return', data.get('total_return', 0)))
                vs_s = float(data.get('vs_spy', data.get('relative_performance', 0)))
                returns.append(ret)
                vs_spy_vals.append(vs_s)
            except (TypeError, ValueError):
                pass
        
        positive_months = sum(1 for r in returns if r > 0)
        outperforming_months = sum(1 for r in vs_spy_vals if r > 0)
        total_months = len(returns)
        
        if total_months > 0:
            output += f"Total Months Analyzed: {total_months}\n"
            output += f"Positive Return Months: {positive_months} ({positive_months/total_months*100:.1f}%)\n"
            output += f"Months Outperforming SPY: {outperforming_months} ({outperforming_months/total_months*100:.1f}%)\n\n"
            
            # Find best and worst months based on return safely
            if returns:
                # Find index of best and worst returns
                best_idx = returns.index(max(returns))
                worst_idx = returns.index(min(returns))
                
                # Get the corresponding months
                best_month_key = list(stock_monthly.keys())[best_idx]
                worst_month_key = list(stock_monthly.keys())[worst_idx]
                
                # Get the actual return values
                best_return = returns[best_idx]
                worst_return = returns[worst_idx]
                
                output += f"Best Month: {best_month_key} with {best_return*100:.2f}% return\n"
                output += f"Worst Month: {worst_month_key} with {worst_return*100:.2f}% return\n"
    
    # Add overall metrics
    overall_metrics = None
    if symbol in stock_metrics:
        overall_metrics = stock_metrics[symbol]
    
    if overall_metrics:
        output += "\nOVERALL METRICS FOR " + symbol + "\n\n"
        output += f"Total Return: {overall_metrics.get('total_return', 0)*100:.2f}%\n"
        output += f"Annualized Return: {overall_metrics.get('annualized_return', 0)*100:.2f}%\n"
        output += f"Volatility: {overall_metrics.get('volatility', 0)*100:.2f}%\n"
        output += f"Beta: {overall_metrics.get('beta', 0):.2f}\n"
        output += f"Alpha: {overall_metrics.get('alpha', 0)*100:.2f}%\n"
        output += f"Maximum Drawdown: {overall_metrics.get('max_drawdown', 0)*100:.2f}%\n"
        output += f"Sharpe Ratio: {overall_metrics.get('sharpe_ratio', 0):.2f}\n"
        output += f"Calmar Ratio: {overall_metrics.get('calmar_ratio', 0):.2f}\n"
        output += f"Sortino Ratio: {overall_metrics.get('sortino_ratio', 0):.2f}\n"
    else:
        output += "\nNo overall metrics available for " + symbol + "\n"
    
    return output

def format_diversification(diversification):
    """Format the portfolio diversification analysis."""
    output = "PORTFOLIO DIVERSIFICATION ANALYSIS\n\n"
    
    # Format sector exposure
    output += "SECTOR EXPOSURE\n\n"
    
    # Determine column widths
    sector_exposure = diversification.get('sector_exposure', {})
    sector_width = max(25, max(len(sector) for sector in sector_exposure.keys())) if sector_exposure else 25
    weight_width = 10
    value_width = 15
    positions_width = 40
    
    # Create header with proper widths
    header = (f"{'Sector':<{sector_width}} | {'Weight':<{weight_width}} | {'Value':<{value_width}} | {'Positions':<{positions_width}}")
    output += header + "\n"
    output += "-" * len(header) + "\n"
    
    for sector, data in sector_exposure.items():
        positions_str = ", ".join(data.get('positions', []))
        row = (f"{sector:<{sector_width}} | {data.get('weight', 0)*100:7.2f}%     | "
               f"${data.get('value', 0):13,.2f} | {positions_str}")
        output += row + "\n"
    
    # Format industry exposure
    output += "\nINDUSTRY EXPOSURE\n\n"
    
    # Determine column widths
    industry_exposure = diversification.get('industry_exposure', {})
    industry_width = max(25, max(len(industry) for industry in industry_exposure.keys())) if industry_exposure else 25
    sector_ind_width = max(20, max(len(data.get('sector', '')) for data in industry_exposure.values())) if industry_exposure else 20
    
    # Create header with proper widths
    header = (f"{'Industry':<{industry_width}} | {'Sector':<{sector_ind_width}} | {'Weight':<{weight_width}} | "
              f"{'Value':<{value_width}} | {'Positions':<{positions_width}}")
    output += header + "\n"
    output += "-" * len(header) + "\n"
    
    for industry, data in industry_exposure.items():
        positions_str = ", ".join(data.get('positions', []))
        sector = data.get('sector', '')
        row = (f"{industry:<{industry_width}} | {sector:<{sector_ind_width}} | {data.get('weight', 0)*100:7.2f}%     | "
               f"${data.get('value', 0):13,.2f} | {positions_str}")
        output += row + "\n"
    
    # Format sub-industry exposure
    output += "\nSUB-INDUSTRY EXPOSURE\n\n"
    
    # Determine column widths
    subcategory_exposure = diversification.get('subcategory_exposure', {})
    subcategory_width = max(27, max(len(subcategory) for subcategory in subcategory_exposure.keys())) if subcategory_exposure else 27
    industry_sub_width = max(24, max(len(data.get('industry', '')) for data in subcategory_exposure.values())) if subcategory_exposure else 24
    
    # Create header with proper widths
    header = (f"{'Sub-Industry':<{subcategory_width}} | {'Industry':<{industry_sub_width}} | {'Weight':<{weight_width}} | "
              f"{'Value':<{value_width}} | {'Positions':<{positions_width}}")
    output += header + "\n"
    output += "-" * len(header) + "\n"
    
    for subcategory, data in subcategory_exposure.items():
        positions_str = ", ".join(data.get('positions', []))
        industry = data.get('industry', '')
        row = (f"{subcategory:<{subcategory_width}} | {industry:<{industry_sub_width}} | {data.get('weight', 0)*100:7.2f}%     | "
               f"${data.get('value', 0):13,.2f} | {positions_str}")
        output += row + "\n"
    
    # Format individual stock classifications
    output += "\nINDIVIDUAL STOCK CLASSIFICATIONS\n\n"
    
    # Determine column widths
    classifications = diversification.get('classifications', {})
    symbol_width = max(8, max(len(symbol) for symbol in classifications.keys())) if classifications else 8
    sector_cls_width = max(24, max(len(data.get('sector', '')) for data in classifications.values())) if classifications else 24
    industry_cls_width = max(22, max(len(data.get('industry', '')) for data in classifications.values())) if classifications else 22
    subcategory_cls_width = max(30, max(len(data.get('subcategory', '')) for data in classifications.values())) if classifications else 30
    
    # Create header with proper widths
    header = (f"{'Symbol':<{symbol_width}} | {'Sector':<{sector_cls_width}} | {'Industry':<{industry_cls_width}} | "
              f"{'Subcategory':<{subcategory_cls_width}}")
    output += header + "\n"
    output += "-" * len(header) + "\n"
    
    for symbol, data in sorted(classifications.items()):
        sector = data.get('sector', '')
        industry = data.get('industry', '')
        subcategory = data.get('subcategory', '')
        row = (f"{symbol:<{symbol_width}} | {sector:<{sector_cls_width}} | {industry:<{industry_cls_width}} | "
               f"{subcategory}")
        output += row + "\n"
    
    return output

def format(ib_connection=None):
    """
    Format all portfolio data for LLM consumption
    
    Args:
        ib_connection: The IB connection object to use for data retrieval
    
    Returns:
        account_info, positions_table, formatted_diversification, portfolio_metrics, 
        stock_metrics, monthly_performance, correlations
    """
    global positions, formatted_output, metrics, monthly_results, aapl_results, diversification, correlations, _data_fetched
    
    try:
        # Use provided connection or create a new one
        active_ib = ib_connection if ib_connection is not None else initialize_ib_connection()
        
        # Only fetch data if we have an active connection and data hasn't been fetched yet
        if active_ib and not _data_fetched:
            print("Fetching portfolio data...")
            positions, formatted_output = get_portfolio_holdings(active_ib, print_output=False)
            
            if positions:
                symbols = [p['contract'].symbol for p in positions]
                
                # Calculate portfolio metrics
                metrics = calculate_portfolio_metrics(active_ib, symbols, printOutput=False)
                
                # Calculate monthly portfolio metrics
                monthly_results = calculate_monthly_portfolio_metrics(active_ib, symbols, print_output=False)
                
                # Run individual stock analysis for AAPL
                aapl_results = calculate_monthly_stock_metrics(active_ib, "AAPL", printOutput=False)
                
                # Analyze portfolio diversification
                diversification = analyze_portfolio_diversification(active_ib, print_output=False)
                
                # Analyze portfolio correlations
                correlations = analyze_portfolio_correlations(active_ib, symbols, print_output=False)
                
                # Mark data as fetched to avoid duplicate calls
                _data_fetched = True
                
                # Close the connection if we created it here
                if ib_connection is None:
                    close_ib_connection(active_ib)
        
        # Format the data
        formatted_pos = format_portfolio_positions(positions)
        account_info = extract_account_info(formatted_pos["formatted_output"])
        portfolio_metrics = format_portfolio_metrics(metrics)
        stock_metrics = format_stock_metrics(metrics)
        monthly_performance = format_monthly_performance(monthly_results)
        formatted_diversification = format_diversification(diversification)
        positions_table = formatted_pos.get("positions_table", "")
    except Exception as e:
        print(f"Error in format function: {e}")
        account_info = "Unable to extract account information"
        positions_table = "Unable to format positions table"
        formatted_diversification = "Unable to format diversification"
        portfolio_metrics = "Unable to format portfolio metrics"
        stock_metrics = "Unable to format stock metrics"
        monthly_performance = "Unable to format monthly performance"
    
    return account_info, positions_table, formatted_diversification, portfolio_metrics, stock_metrics, monthly_performance, correlations