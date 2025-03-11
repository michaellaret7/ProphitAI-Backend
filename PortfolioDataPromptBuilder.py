import json
from PortfolioData import get_portfolio_holdings, analyze_portfolio_correlations, connect_to_ib, calculate_portfolio_metrics, calculate_monthly_portfolio_metrics, calculate_monthly_stock_metrics, analyze_portfolio_diversification, analyze_portfolio_correlations
from openai import OpenAI
import numpy as np
import os
from datetime import datetime
import psycopg2
import pandas as pd
import re
OpenAI_API_KEY = "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"
Sonar_API_KEY = "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"
# Initialize clients
api_key = os.environ.get("OPENAI_API_KEY", OpenAI_API_KEY)
client = OpenAI(
    api_key=api_key,
)

ib = connect_to_ib()

positions, formatted_output = get_portfolio_holdings(ib, print_output=False)

if positions:
    symbols = [p['contract'].symbol for p in positions]
    
    # Calculate portfolio metrics - printing handled internally
    metrics = calculate_portfolio_metrics(ib, symbols, printOutput=False)
    
    # Calculate monthly portfolio metrics - printing handled internally
    monthly_results = calculate_monthly_portfolio_metrics(ib, symbols, print_output=False)

# Run individual stock analysis for AAPL - printing handled internally
aapl_results = calculate_monthly_stock_metrics(ib, "AAPL", printOutput=False)

# Analyze portfolio diversification - printing handled internally
diversification = analyze_portfolio_diversification(ib, print_output=False)

# Analyze portfolio correlations - printing handled internally
correlations = analyze_portfolio_correlations(ib, symbols, print_output=False)

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

# Function to query energy stocks from database
def query_energy_stocks():
    """Query energy stocks from the database."""
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host="demo-postgres.ctemwoy8mbzw.us-east-1.rds.amazonaws.com",
            database="equity_sector_energy",
            user="postgres",
            password="ml1710402!",
            port="5432"
        )
        
        # Create a cursor
        cursor = conn.cursor()
        
        # Execute the query to get coal and consumable fuels stocks
        cursor.execute("""
            SELECT ticker, short_name, sector, industry, sub_industry, p_e, price_d_1, market_cap, 
                   ebitda_t12m, net_debt_to_ebitda_lf, alpha_m_3, beta_m_3
            FROM oil__gas_and_consumable_fuels.coal_and_consumable_fuels
            ORDER BY market_cap DESC
            LIMIT 15
        """)
        
        # Fetch the results
        results = cursor.fetchall()
        
        # Get column names from cursor description
        columns = [desc[0] for desc in cursor.description]
        
        # Create a list of dictionaries
        energy_stocks = []
        for row in results:
            stock_dict = {}
            for i, col in enumerate(columns):
                stock_dict[col] = row[i]
            energy_stocks.append(stock_dict)
        
        # Close the cursor and connection
        cursor.close()
        conn.close()
        
        return energy_stocks
        
    except Exception as e:
        print(f"Error querying energy stocks: {e}")
        # Return a fallback list if there's an error
        return [
            {"ticker": "BTU", "short_name": "PEABODY ENERGY CORP", "sub_industry": "Coal & Consumable Fuels", "p_e": 4.82, "market_cap": 3200000000, "alpha_m_3": 0.45, "beta_m_3": 0.92},
            {"ticker": "ARLP", "short_name": "ALLIANCE RESOURCE", "sub_industry": "Coal & Consumable Fuels", "p_e": 5.31, "market_cap": 2900000000, "alpha_m_3": 0.38, "beta_m_3": 0.85},
            {"ticker": "CEIX", "short_name": "CONSOL ENERGY INC", "sub_industry": "Coal & Consumable Fuels", "p_e": 4.95, "market_cap": 2400000000, "alpha_m_3": 0.41, "beta_m_3": 0.89}
        ]


def free_search(system_prompt, user_prompt):
    messages = [
        {
            "role": "system",
            "content": (
                system_prompt
            ),
        },
        {   
            "role": "user",
            "content": (
                user_prompt
            ),
        },
    ]

    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="sonar-deep-research",
        messages=messages,
    )
    # Store full response in a variable
    full_response = response.choices[0].message.content
    # Print in a readable format
    print("Complete response:")
    print(full_response)
    return full_response  # Return the response so it can be used by the tool


def equity_research_analyst():
    date = datetime.now().strftime("%Y-%m-%d")

    system_prompt = """
    You are a professional financial analyst specializing in equity markets. Provide comprehensive, data-driven analysis of the stock market with the following characteristics:
1. Use reliable financial sources including market data providers, SEC filings, earnings reports, analyst research, and expert commentary
2. Include relevant quantitative data such as index levels, trading volumes, market breadth, sector performance, and valuation metrics
3. Analyze market trends across different market caps, sectors, investment styles, and geographic regions
4. Explain technical concepts clearly but maintain sophisticated financial analysis
5. Discuss macroeconomic factors affecting equity markets including monetary policy, inflation, employment, and economic growth
6. Structure your response with clear sections covering different timeframes and market segments
7. Include diverse perspectives on market outlook from leading institutions and strategists
"""

    user_prompt = f"""
GOAL: Provide comprehensive equity market analysis across multiple timeframes (1w, 1m, 3m, 6m) for portfolio optimization.

IMPORTANT:
THIS IS THE DATE TODAY: {date}

Conduct a detailed analysis of the current state of the equity market with specific focus on:

1. RECENT DEVELOPMENTS (PAST WEEK):
   - Major price movements and trading patterns in major indices (S&P 500, Nasdaq, Dow Jones, Russell 2000)
   - Sector rotation and leadership changes
   - Key earnings reports, economic data releases, or news that impacted markets
   - Notable changes in market sentiment indicators (VIX, put/call ratios, sentiment surveys)

2. MONTH-LONG TRENDS (PAST 30 DAYS):
   - Performance comparison across sectors, market caps, and investment styles (growth vs. value)
   - Fund flows into different market segments and ETFs
   - Changes in market breadth and participation
   - Shifts in institutional positioning and retail investor activity
   - International market performance and correlation with US markets

3. QUARTERLY PERSPECTIVE (PAST 3 MONTHS):
   - Earnings season results and guidance trends
   - Valuation changes and comparison to historical averages
   - Monetary policy impacts on equity markets
   - Market technical indicators and their signals
   - Significant corporate actions (M&A, buybacks, dividends)
   - Performance of thematic and factor-based investments

4. OUTLOOK AND STRATEGIC CONSIDERATIONS:
   - Key catalysts and risk factors for the equity market in coming weeks
   - Sector and industry opportunities
   - Consensus earnings expectations and their implications
   - Technical levels to watch across major indices

Please include specific data points, charts when relevant, and cite your sources. Prioritize accuracy and depth of analysis over general commentary.
    """

    messages = [
        {
            "role": "system",
            "content": (
                system_prompt
            ),
        },
        {   
            "role": "user",
            "content": (
                user_prompt
            ),
        },
    ]

    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="sonar-deep-research",
        messages=messages,
    )
    # Store full response in a variable
    full_response = response.choices[0].message.content

    # Remove the thinking process using regex
    cleaned_content = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL)

    # Print in a readable format
    print("Complete response:")
    print(full_response)
    print("Cleaned response:")
    print(cleaned_content)
    return full_response  # Return the response so it can be used by the tool

equity_research_analyst()

def commodities_analyst():
    date = datetime.now().strftime("%Y-%m-%d")

    system_prompt = """
    You are an expert commodities analyst with deep knowledge of global markets. You prioritize clarity, detail, and data-backed reasoning in your explanations. Always ground your conclusions in the provided context. If needed information is absent, acknowledge the gap rather than guessing.
    """

    user_prompt = f"""
    GOAL / OBJECTIVE:
    Provide a structured, data-driven analysis of how commodities are influenced by fundamental supply and demand factors, weather events, economic indicators, geopolitical risks, currency movements, policy changes, and technological shifts.

    IMPORTANT:
    THIS IS THE DATE TODAY: {date}
    
    USER MESSAGE (PROMPT):
    Please read the following reference on commodity market drivers and produce a well-organized, multi-paragraph report that covers:
    1. An overview of the key categories affecting commodities (supply/demand fundamentals, weather impacts, economic data, geopolitical risks, currency/financial factors, policy/regulatory influences, and technological trends).
    2. How these factors interact and reinforce or offset each other across different commodity classes (energy, metals, agriculture, etc.).
    3. Real or hypothetical scenarios illustrating potential market responses (e.g., how a strong dollar might affect oil prices, or how a drought impacts grain supplies).
    4. A brief forward-looking perspective on which factors appear most significant for the near-term commodity outlook.

    CONTEXT (REFERENCE MATERIAL):
    ----------------------------------------------------------------
    Commodities are influenced by a complex mix of fundamental supply and demand dynamics, weather
    conditions, economic data, geopolitical events, and policy decisions. The importance of each factor
    depends on the specific commodity (e.g., oil, natural gas, agricultural products, metals). Below is a
    breakdown of the most critical drivers:

    1. Supply and Demand Fundamentals
    • Production Levels - Changes in mining, drilling, or agricultural output affect supply.
    • Global Consumption Trends - Industrial activity, energy demand, and consumer behavior impact
    prices.
    • Inventory Levels (EIA, DOE, USDA, LME, COMEX Reports) - Storage and stockpile levels provide
    insight into current supply/demand balances.

    2. Weather and Natural Events
    • Agricultural Commodities (Corn, Wheat, Soybeans, Coffee, Cocoa, Sugar)
    --> Droughts, floods, frosts, and hurricanes can drastically impact crop yields.
    --> El Niño and La Niña influence rainfall and temperatures globally.
    --> Disease outbreaks (e.g., African Swine Fever affecting soybean demand in China).
    • Energy Markets (Oil, Natural Gas, Coal)
    --> Hurricanes affecting Gulf of Mexico oil and gas production.
    --> Cold winters increase natural gas demand (heating), while hot summers boost electricity use.
    --> Water shortages can impact hydropower generation and mining.
    • Metals & Mining
    --> Natural disasters or labor strikes can shut down mines (copper, iron ore, gold, etc.).
    --> Geological constraints impact long-term supply.

    3. Economic Data & Growth Indicators
    • GDP Growth (China, U.S., EU) - Higher economic activity increases demand for industrial metals,
    energy, and agricultural commodities.
    • Manufacturing and Industrial Production (PMIs, ISM, Durable Goods Orders) - A strong
    manufacturing sector signals increased raw material consumption.
    • Employment & Consumer Spending - Affects fuel demand (gasoline, diesel) and consumption of
    food/agriculture commodities.

    4. Geopolitical & Supply Chain Risks
    • OPEC+ Decisions (Oil) - Production quotas set by OPEC+ impact crude oil supply and prices.
    • Sanctions and Trade Restrictions - U.S. sanctions on Russian oil, metals, or agricultural products
    shift trade flows.
    • Tariffs and Trade Wars - U.S.-China trade tensions affecting soybean exports/imports.
    • Shipping & Logistics Disruptions
    - Red Sea/Suez Canal disruptions impacting energy and metals.
    - Panama Canal drought slowing commodity shipments.
    - Port strikes and supply chain bottlenecks.

    5. Currency & Financial Market Movements
    • U.S. Dollar Strength - Since most commodities are priced in USD, a stronger dollar makes them
    more expensive for foreign buyers.
    • Interest Rates & Inflation - Higher rates increase the cost of holding non-yielding assets like gold,
    while inflationary pressures often support commodity prices.
    • Speculative Positioning (COT Reports, Hedge Fund Flows) - Large spec positions in futures
    markets drive volatility.

    6. Policy & Regulation
    • Environmental Regulations (Carbon Taxes, Emissions Caps) - Restrictions on fossil fuel emissions
    impact coal, oil, and natural gas demand.
    • Biofuel Mandates (Ethanol, Biodiesel) - Policies requiring biofuel blending affect corn and soybean
    demand.
    • Mining & Drilling Restrictions - ESG-driven constraints on mining (lithium, cobalt) and fossil fuel
    production.
    • Government Stockpiling & Strategic Reserves (SPR Releases, China's Grain Reserves) - Governments manage strategic commodity reserves, impacting market balance.

    7. Alternative Energy & Technological Shifts
    • EV and Battery Metals Demand (Lithium, Cobalt, Nickel, Copper) - Growth in electric vehicle
    adoption increases demand for critical minerals.
    • Green Energy Transition (Solar, Wind, Hydrogen) - Shifts in energy consumption patterns impact
    fossil fuel demand.
    • AI & Semiconductor Boom (Rare Earths, Silver, Copper) - Increased tech sector demand drives
    specific commodity markets.

    8. War, Conflict & Cybersecurity Risks
    • Russia-Ukraine War (Wheat, Corn, Oil, Natural Gas, Palladium) - Major disruptions in global grain
    and energy markets.
    • Middle East Tensions (Oil, Gold, Safe Haven Demand) - Conflicts in the region can lead to oil price
    spikes.
    • Cyberattacks on Infrastructure (Pipelines, Power Grids) - Potential for disruptions to oil, gas, and
    power markets.
    ----------------------------------------------------------------

    INSTRUCTIONS:
    1. Provide an in depth overview of the main categories driving commodity markets.
    2. Summarize how these factors intersect (e.g., how weather events affect supply, how currency movements alter global trade flows, etc.).
    3. Give at least one example scenario (hypothetical or based on known patterns) illustrating how a particular driver might affect prices.
    4. Offer a forward-looking perspective on which factors are likely to be especially influential in the near term.
    5. Organize your response clearly, with headings or bullet points where appropriate.
    6. If any detail is missing from the context, note that explicitly rather than fabricating information.

    END OF PROMPT
    """

    messages = [
        {
            "role": "system",
            "content": (
                system_prompt
            ),
        },
        {   
            "role": "user",
            "content": (
                user_prompt
            ),
        },
    ]

    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="sonar-deep-research",
        messages=messages,
    )
    # Store full response in a variable
    full_response = response.choices[0].message.content
    # Print in a readable format
    print("Complete response:")
    print(full_response)
    return full_response  # Return the response so it can be used by the tool

def etf_analyst():
    date = datetime.now().strftime("%Y-%m-%d")

    system_prompt = """You are a leading ETF strategist with 20+ years experience across asset management and investment research. Your expertise includes:

- ETF structure, mechanics, and liquidity analysis
- Performance and tracking efficiency evaluation
- Factor, thematic, and sector ETF evaluation
- ETF portfolio construction techniques
- Total cost analysis including expense ratios, tracking error, and trading costs

Focus on identifying optimal ETF selections for various portfolio objectives. Evaluate both strategic and tactical ETF opportunities across asset classes."""

    user_prompt = f"""
GOAL: Provide comprehensive ETF market analysis across multiple timeframes (1w, 1m, 3m, 6m) for portfolio optimization.

IMPORTANT:
THIS IS THE DATE TODAY: {date}

FORMAT:

1. EXECUTIVE SUMMARY
   - Current ETF market conditions and key investment themes
   - Strategic recommendations and major opportunities/risks

2. ETF MARKET OVERVIEW
   - Broad ETF category flows and performance (equity, fixed income, commodity, multi-asset)
   - New product developments and industry trends
   - AUM growth and distribution patterns
   - Liquidity conditions and trading volumes

3. EQUITY ETF ANALYSIS
   - U.S., international, and emerging market ETF performance
   - Factor ETF rotation (value, growth, quality, momentum, min vol)
   - Sector and industry ETF relative performance
   - Market cap spectrum (large, mid, small) and style box analysis

4. FIXED INCOME ETF ANALYSIS
   - Government, corporate, high yield, and municipal ETF performance
   - Duration-based ETF strategies and interest rate sensitivity
   - Credit quality spectrum performance
   - Active vs. passive fixed income ETF comparison

5. SPECIALTY ETF ANALYSIS
   - Thematic ETF performance (technology, ESG, infrastructure, etc.)
   - Alternative strategy ETFs (options overlay, covered call, etc.)
   - Commodity and real asset ETFs
   - Multi-asset and allocation ETFs

6. ETF TECHNICAL FACTORS
   - Premium/discount patterns and trends
   - Creation/redemption activity
   - Securities lending revenue potential
   - Trading costs and execution efficiency

7. ETF STRUCTURAL ANALYSIS
   - ETF construction methodologies and impact on performance
   - Index methodologies and rebalancing effects
   - Tax efficiency comparisons
   - Expense ratio trends and competitive landscape

8. STRATEGIC APPLICATIONS
   - Core-satellite portfolio construction with ETFs
   - Factor rotation strategies
   - Tactical asset allocation implementation
   - Risk management applications

9. ETF OPPORTUNITIES
   - Underutilized or overlooked ETF strategies
   - Relative value opportunities between similar ETFs
   - New product innovations worth considering
   - Unique exposures available through ETFs

10. OUTLOOK
    - Top ETF recommendations by category with rationale
    - Expected performance scenarios
    - Key risks to monitor for recommended ETFs
    - Implementation guidance and position sizing

REQUIREMENTS:
- Include precise numerical data (performance figures, expense ratios, flows)
- Compare similar ETFs on multiple metrics
- Provide specific ticker recommendations with rationale
- Assess tracking error and index replication quality
- Highlight liquidity considerations and trading guidance
- Use reliable sources (Bloomberg, ETF issuer data, major research firms)
- Current date: March 7th, 2025
- Distinguish between strategic and tactical ETF recommendations
- Consider tax implications where relevant
- Address potential hidden risks in ETF structures
    """

    messages = [
        {
            "role": "system",
            "content": (
                system_prompt
            ),
        },
        {   
            "role": "user",
            "content": (
                user_prompt
            ),
        },
    ]

    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="sonar-deep-research",
        messages=messages,
    )
    # Store full response in a variable
    full_response = response.choices[0].message.content
    # Print in a readable format
    print("Complete response:")
    print(full_response)
    return full_response  # Return the response so it can be used by the tool

def treasuries_analyst():
    date = datetime.now().strftime("%Y-%m-%d")
    
    system_prompt = """
You are an expert macroeconomic analyst with a specialization in U.S. Treasury markets and yield curves. You have deep knowledge of factors affecting Treasury yields—such as inflation, Federal Reserve policy, geopolitical risks, and market positioning. You prioritize clarity, detail, and data-driven reasoning in your analysis. Always cite relevant points from the provided context to ground your conclusions in facts. 
    """

    user_prompt = f"""
GOAL / OBJECTIVE:
Provide a structured, data-driven analysis of how treasuries are influenced by economic indicators, geopolitical risks, currency movements, policy changes, and technological shifts.

Please analyze the following text and produce a well-structured, data-driven report on the behavior of U.S. Treasuries and rates, focusing on:
1. How recent economic data (inflation, employment, wages, growth) has influenced government bond performance.  
2. Specific behavior of the 2s10s yield curve (the yield differential between 2-year and 10-year Treasury notes) during these periods.  
3. Historical tendencies versus current data and outlook for the 2s10s curve.  
4. Upcoming factors that may impact Treasury rates, including but not limited to:
   - Tariffs
   - Inflation data
   - "Flight to quality" (potential equity sell-off)
   - Bond issuance
   - Passive flows (central bank and mutual fund activity, rebalancing)
   - CTA/technical drivers

IMPORTANT:
- The date is {date} (REMEMBER THIS WHEN DOING YOUR RESEARCH)

CONTEXT:
----------------------------------------------------------------
US Treasuries/rates
Government bond performance as it relates to the recent economic data, especially inflation, wages in 
employment and growth. How did the 2s10s curve (yield differential between the 2 year and 10 year 
treasury yield) behave during these periods. How should the curve behave given historical tendencies and 
given the current data and outlook?
Upcoming factors potentially impacting rates:
- Tariffs
- Inflation data
- "flight to quality" - Further Equity selloff
- Bond issuance
- Passive flows (central bank purchases/sales, mutual fund purchases/sales, fund rebalancing)
- CTA/technical.

The U.S. Treasury market is influenced by a range of factors, broadly categorized into economic data,
Federal Reserve policy, geopolitical risks, fiscal policy and supply dynamics, and global demand for safe-
haven assets. Here are the key drivers:

1. Economic Data and Inflation
• Inflation (CPI, PCE Deflator) - Higher inflation typically leads to higher yields as investors demand 
  greater compensation for eroded purchasing power.
• Employment Data (Non-Farm Payrolls, Unemployment Rate, JOLTS, Initial Jobless Claims) -
  Strong job growth suggests economic strength and potential inflationary pressures, impacting Fed 
  policy expectations.
• GDP Growth - Faster economic growth can lead to higher Treasury yields, while weak growth 
  supports lower yields.
• Consumer and Business Confidence (Consumer Confidence, ISM, PMIs) - These indicators gauge 
  economic sentiment and can signal future growth trends.

2. Federal Reserve Policy
• FOMC Rate Decisions & Forward Guidance - Changes in the Fed Funds rate directly influence 
  short-term Treasury yields, while guidance on future policy impacts the yield curve.
• Quantitative Easing (QE) / Quantitative Tightening (QT) - The Fed's balance sheet policy affects 
  supply and demand for Treasuries.
• Dot Plot & Summary of Economic Projections - Provides insights into policymakers' expectations 
  for future rates.

3. Treasury Issuance and Fiscal Policy
• U.S. Budget Deficit & Debt Issuance - Larger deficits often require more Treasury issuance, 
  potentially pushing yields higher.
• Treasury Refunding Announcements - The quarterly refunding schedule provides insight into future 
  issuance and market absorption capacity.
• Spending Bills & Stimulus Programs - Government spending plans impact future supply and 
  inflation expectations.

4. Geopolitical Risks & Global Uncertainty
• War and International Conflicts - Events like Russia-Ukraine, Middle East tensions, or China-
  Taiwan concerns can trigger flight-to-quality moves into Treasuries.
• Trade Wars & Tariffs - U.S.-China tensions, for example, can impact global growth and Treasury 
  demand.
• Energy Prices & Commodity Shocks - Rising oil prices can fuel inflation, affecting yields.

5. Foreign Demand and Currency Movements
• Demand from Foreign Central Banks (China, Japan, Europe, Middle East) - Key buyers of 
  Treasuries can influence yields by increasing or decreasing their purchases.
• U.S. Dollar Strength & Treasury Demand - A strong dollar can reduce foreign demand for 
  Treasuries, while a weaker dollar may attract buyers.
• Sovereign Debt Market Comparisons - Relative yields vs. German Bunds or JGBs influence foreign 
  investor appetite.

6. Market Liquidity & Positioning
• Hedge Fund and Dealer Positioning - Large speculative positioning in futures or options markets 
  can drive short-term volatility.
• Liquidity Conditions - If market depth declines, small shifts in supply/demand can cause outsized 
  moves.
• Repo Market Stress - Disruptions in funding markets can spill over into Treasury yields.

7. Credit & Risk Sentiment
• Corporate Bond Spreads - Wider credit spreads often lead to a bid for Treasuries as investors seek 
  safety.
• Equity Market Volatility (VIX, Risk-Off Moves) - Stock selloffs usually drive Treasury rallies (lower 
  yields).
• Banking Sector Stress (e.g., SVB, Credit Suisse Issues) - Concerns about financial stability often 
  trigger Treasury buying.
----------------------------------------------------------------

INSTRUCTIONS:
1. Provide an in depth and detailed overview of the overall context (recent economic data, inflation, employment, etc.).
2. Discuss how these data points have influenced the 2s10s yield curve historically and in the current environment.
3. Cite and connect the relevant points from the context above to explain the underlying drivers (Fed policy, geopolitical risk, etc.).
4. Identify and evaluate the upcoming factors (tariffs, inflation data, etc.) that could impact rates.
5. Conclude with a forward-looking perspective, highlighting future market positioning and risk sentiment.
6. Present your answer in an organized, multi-paragraph format. Where appropriate, use bullet points or brief subheadings for clarity.
7. If any information is unclear or not provided in the context, acknowledge the gap rather than guessing or fabricating data.
8. Be as detailed as possible in your analysis.
    """

    messages = [
        {
            "role": "system",
            "content": (
                system_prompt
            ),
        },
        {   
            "role": "user",
            "content": (
                user_prompt
            ),
        },
    ]

    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="sonar-deep-research",
        messages=messages,
    )
    # Store full response in a variable
    full_response = response.choices[0].message.content
    # Print in a readable format
    print("Complete response:")
    print(full_response)
    return full_response  # Return the response so it can be used by the tool

def foreign_exchange_analyst():
    date = datetime.now().strftime("%Y-%m-%d")
    
    system_prompt = """
You are an expert FX strategist with deep knowledge of currency valuation models and global monetary dynamics. You prioritize clarity, detail, and factual grounding in your analyses. If information is missing, acknowledge that rather than guessing or inventing data.
    """

    user_prompt = f"""
GOAL / OBJECTIVE:
Provide a structured, data-driven analysis of how foreign exchange (FX) rates—particularly the U.S. Dollar (USD)—are influenced by various valuation methodologies (PPP, IRP, fundamental analysis, technical approaches) and key market drivers such as Federal Reserve policy, macroeconomic data, global risk sentiment, and geopolitical events.

IMPORTANT:
- The date is {date} (REMEMBER THIS WHEN DOING YOUR RESEARCH)

Please analyze the following reference materials on currency valuation and the drivers of the U.S. Dollar, then produce a well-structured report that addresses:
1. A concise overview of the main FX valuation methods (e.g., PPP, IRP, fundamental, technical/sentiment).
2. Key drivers specifically influencing the U.S. Dollar (Fed policy, inflation data, interest rate differentials, geopolitical risk, etc.).
3. How these valuation models and drivers might interplay in the short, medium, and long term.
4. An outlook on which factors may be most significant for USD performance in the near future.

CONTEXT (REFERENCE MATERIAL):
-----------------------------------------------------------------------------------------------
FX/Currencies:
The U.S. Dollar Index (DXY), which measures the USD against a basket of major currencies (EUR, JPY, GBP, CAD, SEK, CHF), is influenced by a combination of economic data, Federal Reserve policy, global risk sentiment, and geopolitical events. Here are the main valuation methodologies:

1. Parity Conditions-Based Valuation
   - Purchasing Power Parity (PPP)
     --> Based on the "law of one price," stating that identical goods should have the same price across countries when converted into a common currency.
     --> The exchange rate should adjust so that a basket of goods costs the same in different countries.
     --> Used as a long-term valuation tool.

   - Interest Rate Parity (IRP)
     --> Links exchange rate movements to interest rate differentials.
     --> The forward exchange rate should be set to prevent arbitrage between interest rate differences across countries.
     --> Used to explain forward rate premiums/discounts.

   - Real Exchange Rate (RER) Approach
     --> Adjusts the nominal exchange rate for inflation differentials.
     --> If a country's real exchange rate is overvalued, its currency might depreciate in the future.

   - Monetary Model
     --> Relates exchange rates to differences in money supply growth, inflation, and output between countries.
     --> More relevant for long-term FX valuation.

2. Fundamental Analysis-Based Valuation
   - Balance of Payments (BoP) Model
     --> Examines trade balances, capital flows, and foreign reserves.
     --> Persistent trade surpluses lead to currency appreciation, while deficits lead to depreciation.

   - Asset Market Approach
     --> Considers interest rates, bond yields, and equity markets.
     --> Capital inflows into a country's bonds and equities support currency appreciation.

   - Behavioral Equilibrium Exchange Rate (BEER)
     --> Uses econometric models to determine whether a currency is overvalued or undervalued.
     --> Includes factors like productivity, terms of trade, and net foreign assets.

   - Debt Sustainability Approach
     --> Evaluates a country's external debt levels.
     --> Countries with unsustainable debt levels often face currency depreciation.

3. Market-Based (Technical & Sentiment) Valuation
   - Real Effective Exchange Rate (REER)
     --> A trade-weighted index that measures a currency's relative strength against a basket of currencies, adjusted for inflation.

   - FX Forward and Options Market Pricing
     --> Forward rates incorporate market expectations of future exchange rate movements.
     --> Options pricing (e.g., risk reversals) can signal expected volatility and directional bias.
   - Technical Analysis
     --> Uses price charts, historical trends, and momentum indicators to forecast FX movements.
     --> Common tools: moving averages, Fibonacci retracements, Bollinger bands.
   - Market Sentiment Indicators
     --> CFTC Commitment of Traders (COT) report tracks speculative positioning.
     --> Carry trade flows indicate risk appetite and currency demand.

Which Model Is Best?
   - Long-term: PPP, balance of payments, monetary models.
   - Medium-term: BEER, REER, asset market approach.
   - Short-term: Market-based (technical, sentiment, and positioning).

Below are the key drivers of the U.S. dollar's movements:

1. Federal Reserve Policy & Interest Rates
   - Fed Funds Rate & Forward Guidance - Higher interest rates increase the appeal of the dollar by offering better returns.
   - FOMC Meetings & Dot Plot - Market expectations for future rate hikes/cuts impact the dollar.
   - Quantitative Tightening (QT) & Liquidity - Reducing the Fed's balance sheet strengthens the USD by tightening money supply.
   - Key Reports: FOMC Meeting Minutes, Fed Chair Speeches, Inflation & Employment Data

2. Inflation & Economic Data
   - Inflation (CPI, PCE Deflator) - Higher inflation can push the Fed to tighten policy, boosting the dollar.
   - Employment Reports (Non-Farm Payrolls, Unemployment Rate, Jobless Claims) - A strong labor market supports Fed rate hikes.
   - GDP Growth - Stronger economic growth attracts capital inflows into the U.S.
   - Retail Sales & Consumer Confidence - Consumer spending strength signals economic health, affecting USD demand.
   - ISM Manufacturing & Services PMI - Indicators of expansion/contraction influencing USD sentiment.
   - Key Reports: CPI, Core PCE Price Index, Non-Farm Payrolls, GDP Reports

3. Global Interest Rate Differentials
   - U.S. vs. Global Rate Spreads - If the Fed keeps rates higher than other central banks (ECB, BoJ, BoE), USD appreciates.
   - Central Bank Divergence - A hawkish Fed vs. a dovish ECB/BoJ strengthens the USD.
   - Key Reports: ECB, BoE, BoJ, RBA, PBoC Policy Statements; U.S. Treasury Yields vs. Global Bonds

4. Geopolitical & Risk Sentiment
   - Safe-Haven Flows - Global uncertainty (wars, banking crises) boosts demand for the U.S. dollar.
   - Conflict & War (Russia-Ukraine, Middle East, China-Taiwan) - Geopolitical risks drive investors into USD as a safe haven.
   - Sanctions & Trade Wars (U.S.-China, Tariffs, Export Bans) - Disruptions impact global trade flows and USD demand.
   - Debt Ceiling & U.S. Fiscal Policy - Government shutdowns or deficit concerns influence USD stability.
   - Key Events: War & Political Instability, U.S.-China Trade Relations, U.S. Debt Ceiling & Government Shutdowns

5. Global Liquidity & Financial Market Conditions
   - Equity Market Volatility (VIX Index, Stock Market Selloffs) - When risk-off sentiment rises, USD strengthens.
   - Banking System Stress (Credit Crunch, Dollar Shortages) - A shortage of USD liquidity increases demand for the greenback.
   - Commodity Prices & Inflation Expectations - Rising oil/gas prices can either boost or weaken USD, depending on the inflation impact.
   - Key Reports: VIX Index, LIBOR/SOFR, Dollar Funding Costs

6. U.S. Trade & Current Account Balance
   - Trade Balance (Exports vs. Imports) - A wider U.S. trade deficit can weaken the USD.
   - U.S. Current Account Deficit - A large deficit suggests more dollars flowing out, potentially weakening the USD.
   - Foreign Exchange Reserves & Central Bank USD Holdings - China, Japan, and others adjusting their FX reserves can impact USD demand.
   - Key Reports: U.S. Trade Balance, Treasury International Capital (TIC) Data

7. Emerging Market & Global Currency Trends
   - China's Yuan (CNY) & Emerging Market Currencies - Weakness in EM currencies often strengthens the dollar.
   - Capital Flight & De-Dollarization Trends - Global shifts away from USD reliance can impact demand over time.
   - BRICS & Alternative Reserve Currencies - Any effort to reduce USD's dominance in global trade could weaken demand.
   - Key Reports: BRICS Currency Initiatives, IMF SDR Allocation
-----------------------------------------------------------------------------------------------

INSTRUCTIONS:
1. Summarize the primary valuation approaches (PPP, IRP, fundamental, and technical/sentiment) used for FX.
2. Highlight the main macro drivers of the U.S. Dollar, referencing Fed policy, inflation, global rates, geopolitical risk, etc.
3. Illustrate how these valuation models and drivers interact over different time horizons (short, medium, long term).
4. Conclude with a short forward-looking assessment on which factors may be most impactful in the near-term USD outlook.
5. If any detail is missing or unclear, note it explicitly rather than fabricating information.
6. Organize your response clearly with headings or bullet points.
    """

    messages = [
        {
            "role": "system",
            "content": (
                system_prompt
            ),
        },
        {   
            "role": "user",
            "content": (
                user_prompt
            ),
        },
    ]

    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="sonar-deep-research",
        messages=messages,
    )
    # Store full response in a variable
    full_response = response.choices[0].message.content
    # Print in a readable format
    print("Complete response:")
    print(full_response)
    return full_response  # Return the response so it can be used by the tool

def ig_credit_analyst():
    date = datetime.now().strftime("%Y-%m-%d")
    
    system_prompt = """
You are an expert credit analyst specializing in U.S. Investment Grade (IG) corporate bonds. You have deep knowledge of credit fundamentals, spread analysis, interest rate dynamics, and market technicals. You prioritize clarity, detail, and factual grounding in your analyses. If information is missing, acknowledge that rather than guessing or inventing data.
    """

    user_prompt = f"""
GOAL / OBJECTIVE:
Provide a structured, data-driven analysis of U.S. Investment Grade (IG) Credit Bonds, focusing on the key drivers that influence their performance, pricing, and spread dynamics.

IMPORTANT:
- The date is {date} (REMEMBER THIS WHEN DOING YOUR RESEARCH)

Please analyze the following reference materials on IG credit markets and produce a well-structured report that addresses:
1. A comprehensive overview of the main factors influencing IG corporate bond performance.
2. Current market conditions and trends in the IG credit space.
3. How various factors (company fundamentals, interest rates, economic data, etc.) interplay to affect IG bond valuations.
4. An outlook on which factors may be most significant for IG credit performance in the near future.

CONTEXT (REFERENCE MATERIAL):
-----------------------------------------------------------------------------------------------
CORPORATE CREDIT
U.S. Investment Grade (IG) Credit Bonds are influenced by a mix of macro factors, credit-specific metrics,
market liquidity, and global risk sentiment. Here are the most important drivers:

1. Company credit ratings
Individual company spreads are first and foremost influenced by a company's rating which is influenced
and determined by rating agencies' reviews of a company's financials after every earnings release with
ongoing monitoring.

Corporate Fundamentals & Credit Metrics
• Earnings Reports (Revenue, EBITDA, Free Cash Flow) - Strong corporate earnings support credit quality and reduce default risk.
• Debt-to-EBITDA & Leverage Ratios - Higher leverage raises concerns over creditworthiness.
• Interest Coverage Ratios - Indicates a company's ability to service debt.
• Ratings Agency Actions (Moody's, S&P, Fitch) - Downgrades or upgrades impact bond pricing and spreads.

Key Reports:
• Corporate Earnings Releases
• Ratings Agency Announcements

2. Interest Rates & Federal Reserve Policy
• Fed Funds Rate & Forward Guidance - IG credit spreads tighten when the Fed signals stability or cuts rates, while hikes increase borrowing costs.
• Treasury Yield Curve (10Y, 2Y, 30Y Yields, Inversions) - IG bonds are priced off risk-free Treasury rates, with higher yields raising corporate borrowing costs.
• Quantitative Tightening (QT) & Fed Balance Sheet Reduction - Fed selling Treasuries and MBS reduces market liquidity, which can widen credit spreads.

Key Reports:
• FOMC Meeting Minutes
• Fed Dot Plot & SEP (Summary of Economic Projections)
• Treasury Yield Movements

3. Credit Spreads & Market Liquidity
• Investment Grade Credit Spreads (OAS, CDX IG Index, BBB vs. A Spreads) - Widening spreads indicate risk-off sentiment.
• Primary Market Issuance (New Bond Supply) - Large new issuance can temporarily widen spreads.
• Bond Market Liquidity (Bid-Ask Spreads, Dealer Inventories) - Thin liquidity can exacerbate credit spread movements.

Key Indicators:
• Bloomberg Barclays U.S. IG Corporate Bond Index
• ICE BofA Investment Grade OAS

4. Economic Data & Growth Outlook
• GDP Growth - A strong economy supports corporate revenues and IG bond demand.
• Inflation (CPI, PCE Deflator) - High inflation leads to tighter monetary policy, pressuring IG bonds.
• Employment & Wage Growth (Non-Farm Payrolls, JOLTS, Unemployment Rate) - Strong labor markets imply economic resilience but could lead to rate hikes.

Key Reports:
• GDP Growth
• CPI & PCE Inflation Reports
• Non-Farm Payrolls (NFP)

5. Geopolitical & Market Risk Sentiment
• Geopolitical Tensions (Russia-Ukraine, Middle East, China-Taiwan) - Flight-to-quality moves can impact IG spreads.
• U.S. Fiscal Policy & Debt Ceiling Concerns - Increased Treasury issuance for deficit funding can crowd out corporate bond demand.
• Banking Sector Stability (Financial Conditions, Credit Markets) - Stress in the banking sector can lead to wider IG spreads.

Key Indicators:
• VIX (Market Volatility)
• Treasury Issuance Announcements

6. Global Demand & Foreign Investment
• Foreign Central Bank & Sovereign Wealth Fund Purchases - High demand from global investors (China, Japan, EU) tightens spreads.
• Relative Yields (U.S. IG vs. Euro Credit, EM Bonds) - U.S. IG attracts capital if it offers better risk-adjusted returns.
• Hedging Costs for Foreign Investors - FX hedging costs impact overseas demand for U.S. IG bonds.

Key Reports:
• TIC Data (Foreign Holdings of U.S. Bonds)
• Relative Yield Comparisons (U.S. vs. European IG Credit)

7. Sector-Specific Credit Risks
• Financials (Bank & Insurance IG Bonds) - Heavily influenced by financial stability, regulations, and Fed policy.
• Tech & High-Growth Names - Sensitive to rate hikes as they rely on low-cost funding.
• Energy & Industrials - Commodity price fluctuations impact creditworthiness.

Key Reports:
• Sector-Specific Earnings Reports
• Industry Credit Spreads
-----------------------------------------------------------------------------------------------

INSTRUCTIONS:
1. Summarize the key drivers influencing U.S. Investment Grade corporate bond performance.
2. Analyze current market conditions for IG credit based on the most recent data.
3. Explain how company fundamentals, macroeconomic factors, and market technicals interact to affect IG bond valuations.
4. Discuss sector-specific trends and differences in the IG credit space.
5. Provide a forward-looking assessment on which factors may be most impactful for IG credit in the near term.
6. If any detail is missing or unclear, note it explicitly rather than fabricating information.
7. Organize your response clearly with headings or bullet points.
    """

    messages = [
        {
            "role": "system",
            "content": (
                system_prompt
            ),
        },
        {   
            "role": "user",
            "content": (
                user_prompt
            ),
        },
    ]

    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="sonar-deep-research",
        messages=messages,
    )
    # Store full response in a variable
    full_response = response.choices[0].message.content
    # Print in a readable format
    print("Complete response:")
    print(full_response)
    return full_response  # Return the response so it can be used by the tool

def high_yield_analyst():
    date = datetime.now().strftime("%Y-%m-%d")
    
    system_prompt = """
You are an expert fixed-income strategist with deep knowledge of both U.S. high-yield bond markets and emerging market (EM) debt. You prioritize clarity, detail, and factual grounding in your analysis. If information is missing, acknowledge that rather than fabricating data.
    """

    user_prompt = f"""
GOAL / OBJECTIVE:
Provide a structured, data-driven analysis of how the key drivers of U.S. high-yield (HY) bonds may apply to or differ within emerging markets (EM) high-yield debt, focusing on factors such as credit spreads, default risks, liquidity conditions, and macroeconomic influences.

IMPORTANT:
- The date is {date} (REMEMBER THIS WHEN DOING YOUR RESEARCH)

Please use the reference material below on U.S. high-yield (HY) bonds to analyze how these drivers and metrics might apply within emerging markets. Specifically:
1. Summarize the primary risk factors, credit metrics, and market conditions affecting HY bonds in the U.S.
2. Discuss which of these factors might behave differently or be of particular relevance when looking at EM high-yield debt.
3. Identify any additional considerations unique to emerging markets (e.g., sovereign risk, currency fluctuations, political instability).
4. Conclude with a brief outlook on EM high-yield markets, referencing both global and local influences.

CONTEXT (REFERENCE MATERIAL):
----------------------------------------------------------------
HIGH YIELD BONDS  
U.S. High Yield (HY) Bonds: Key Market Drivers  
High-yield (HY) bonds (junk bonds) are more sensitive to credit risk, liquidity, and economic growth
expectations than investment-grade bonds. Here are the most important factors impacting HY bonds:

1. Credit Spreads & Risk Premiums  
   - High Yield Spreads (OAS, CDX HY Index, B vs. CCC Spreads) - Wider spreads indicate higher credit risk and market stress.  
   - Credit Default Swap (CDS) Index for High Yield - Rising CDS prices suggest increasing default concerns.  
   - Yield Curve (10Y vs. 2Y, Treasury Rates) - Rising Treasury yields make HY bonds less attractive relative to safer alternatives.  

   Key Indicators:
   - ICE BofA U.S. High Yield OAS
   - CDX HY Index
   - Bloomberg Barclays U.S. HY Bond Index

2. Federal Reserve Policy & Interest Rates  
   - Fed Funds Rate & Forward Guidance - Higher rates increase borrowing costs, making it harder for weaker firms to refinance.
   - Liquidity & Quantitative Tightening (QT) - Fed balance sheet reductions drain liquidity, affecting HY funding.
   - Yield Differentials (HY vs. IG Bonds) - If HY yields rise significantly over IG, it signals market risk aversion.

   Key Reports:
   - FOMC Meeting Minutes
   - Treasury Yield Curves
   - Fed's Financial Stability Reports

3. Corporate Fundamentals & Default Risk  
   - Earnings & Revenue Growth - Weak earnings pressure debt repayment ability.
   - Debt Maturities & Refinancing Risks - Many HY firms rely on rolling over debt; rate hikes make refinancing harder.
   - Leverage Ratios (Debt-to-EBITDA, Interest Coverage) - Highly leveraged companies are more vulnerable in rising rate environments.
   - Ratings Downgrades (Moody's, S&P, Fitch) - Fallen angels (IG to HY downgrades) increase supply and widen spreads.

   Key Reports:
   - Moody's & S&P Default Rate Forecasts
   - Corporate Earnings & Guidance
   - Distressed Debt Ratios

4. Economic Growth & Recession Risk  
   - GDP Growth Trends - Slowdowns hurt lower-rated firms first, increasing default risks.
   - ISM Manufacturing & Services PMI - A contraction signals economic stress for leveraged firms.
   - Consumer Spending & Retail Sales - HY issuers in consumer sectors are sensitive to demand shifts.
   - Housing Market Strength (NAHB, New Home Sales) - Impacts homebuilders, a key HY sector.

   Key Reports:
   - GDP Growth Data
   - ISM Manufacturing & Services PMI
   - Retail Sales & Consumer Confidence

5. Market Liquidity & Fund Flows  
   - High-Yield ETF & Mutual Fund Flows (HYG, JNK) - Inflows support HY, while outflows indicate risk-off sentiment.
   - Dealer Market Liquidity (Bid-Ask Spreads) - A stressed HY market can see spreads widen due to lack of liquidity.
   - Leveraged Loan Market Trends - Rising defaults in leveraged loans can spill over to HY bonds.

   Key Indicators:
   - HYG & JNK ETF Flows
   - Leveraged Loan Default Rates
   - Bid-Ask Spreads in HY Market

6. Geopolitical & Market Risk Sentiment  
   - Risk-Off Events (War, Sanctions, Political Uncertainty) - Investors flee riskier HY assets in favor of Treasuries.
   - Banking System Stability (Credit Crunch, Financial Conditions Index) - HY bonds underperform in periods of financial instability.
   - Stock Market Correlation (S&P 500 & Russell 2000) - HY bonds tend to track equity markets closely.

   Key Events:
   - VIX Index (Market Volatility)
   - Global Geopolitical Tensions
   - U.S. Debt Ceiling & Fiscal Policy

7. Sector-Specific Risks  
   - Energy (Oil & Gas HY Bonds) - Dependent on oil prices and production levels.
   - Retail & Consumer Discretionary - Vulnerable to weak consumer demand and economic slowdowns.
   - Technology & Communications - Rate-sensitive due to high leverage in growth sectors.

   Key Reports:
   - Sector-Specific HY Spread Indices
   - Commodity Price Movements (Oil, Gas, Metals)
----------------------------------------------------------------

INSTRUCTIONS:
1. Organize your response clearly, using headings or bullet points to address the listed items (1-4).
2. Ground your analysis in the context of the U.S. HY bond drivers, then connect them to emerging markets where relevant.
3. If any EM-specific data or factors are missing from the reference, acknowledge the gap rather than guessing.
4. Provide a succinct conclusion with a near-term outlook for EM high-yield bonds.
    """

    messages = [
        {
            "role": "system",
            "content": (
                system_prompt
            ),
        },
        {   
            "role": "user",
            "content": (
                user_prompt
            ),
        },
    ]

    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="sonar-deep-research",
        messages=messages,
    )
    # Store full response in a variable
    full_response = response.choices[0].message.content
    # Print in a readable format
    print("Complete response:")
    print(full_response)
    return full_response  # Return the response so it can be used by the tool

def emerging_market_analyst():
    date = datetime.now().strftime("%Y-%m-%d")
    
    system_prompt = """
You are an expert emerging markets analyst with deep knowledge of the intersection between global macro forces and local EM conditions. You prioritize clarity, detail, and factual grounding in your assessments. If any information is missing, acknowledge that rather than guessing or inventing data.
    """

    user_prompt = f"""
GOAL / OBJECTIVE:
Provide a well-structured, data-driven analysis of how emerging markets (EM) equities and bonds are influenced by both global macro drivers (e.g., U.S. rates, risk sentiment, commodity prices, currency strength) and domestic fundamentals (growth, inflation, policy, political stability).

IMPORTANT:
- The date is {date} (REMEMBER THIS WHEN DOING YOUR RESEARCH)

Using the reference material below on emerging markets drivers, please create a clear, structured report addressing the following:
1. Summarize the global macro factors impacting EM (U.S. interest rates, risk appetite, commodity prices, USD strength, global liquidity).
2. Explain how domestic fundamentals (growth, inflation, monetary/fiscal policy, political stability) shape EM equity and bond performance.
3. Compare the differing dynamics between EM equities and EM bonds (local vs. hard currency debt), citing key market indicators.
4. Conclude with a brief near-term outlook on EM assets, noting any potential risks or catalysts to watch.

CONTEXT (REFERENCE MATERIAL):
---------------------------------------------------------------------------------------------------
EMERGING MARKETS
Emerging markets (EM) equity and bond prices are driven by a combination of global and domestic
factors, including macroeconomic conditions, monetary policy, investor sentiment, and political risks.
Here's a breakdown of the key drivers:

1. Global Macro and External Factors
   - U.S. Interest Rates & Federal Reserve Policy
     • Higher U.S. rates attract capital to U.S. assets, strengthening the dollar and leading to EM capital outflows.
     • Lower rates push investors toward riskier EM assets in search of yield.
   - Global Risk Appetite & Market Sentiment
     • Risk-on environments (growth optimism, low volatility) lead to EM inflows.
     • Risk-off episodes (crises, geopolitical risks) trigger EM outflows.
   - Commodity Prices
     • Many EM economies are commodity exporters (Brazil, Russia, South Africa, Indonesia). Rising commodity prices support their economies and assets, while falling prices hurt them.
   - U.S. Dollar Strength
     • A strong dollar increases the burden of dollar-denominated EM debt, pressuring bond yields and equity valuations.
     • A weaker dollar generally boosts EM assets as financing conditions improve.
   - Global Liquidity & Capital Flows
     • Quantitative easing (QE) by major central banks fuels liquidity-driven rallies in EM.
     • Quantitative tightening (QT) reduces liquidity and puts pressure on EM asset prices.

2. Domestic Economic Fundamentals
   - Growth & Inflation
     • Strong GDP growth typically supports equities and bonds.
     • High inflation erodes bond returns and increases rate hike risks.
   - Monetary & Fiscal Policy
     • Central bank rate cuts boost equities and bonds; rate hikes can dampen asset prices.
     • Fiscal deficits and excessive government borrowing weaken currencies and raise bond yields.
   - Currency Stability & FX Reserves
     • A stable currency attracts investment; depreciation raises funding costs.
     • Higher FX reserves provide a buffer against capital flight.

3. Political & Structural Factors
   - Geopolitical Risks & Sovereign Stability
     • Political instability, policy unpredictability, and geopolitical tensions increase risk premia.
     • Strong institutions and reforms enhance investor confidence.
   - Credit Ratings & Default Risks
     • Downgrades increase borrowing costs and trigger bond outflows.
     • Improvements in fiscal discipline lead to yield compression.

4. EM Equities vs. Bonds - Key Distinctions
   - Equities
     • More sensitive to domestic economic growth and corporate earnings.
     • Benefit from currency depreciation if companies are export-oriented.
     • Higher beta to global risk sentiment than bonds.
     • Dividend yields provide some income buffer during market turbulence.
   - Local Currency Bonds
     • Most sensitive to domestic inflation, monetary policy, and currency stability.
     • Offer higher yields but carry currency risk for foreign investors.
     • Benefit from interest rate cuts and disinflation.
   - Hard Currency (USD) Bonds
     • Less sensitive to local currency volatility but highly impacted by U.S. rate movements.
     • Sovereign spreads reflect country-specific default risk perceptions.
     • Benefit from improving credit fundamentals and global risk appetite.

5. Key Market Indicators to Watch
   - EM Equity Indices: MSCI EM, MSCI EM ex-China
   - Bond Indices: JPM EMBI Global Diversified (hard currency), JPM GBI-EM (local currency)
   - Currency Index: JPM EM Currency Index
   - Fund Flows: EM equity and bond fund flows (IIF data)
   - Positioning: CFTC positioning data for EM currencies
   - Credit Default Swaps (CDS): 5-year sovereign CDS spreads
   - Implied Volatility: EM FX volatility and equity volatility (VXEEM)

---------------------------------------------------------------------------------------------------

INSTRUCTIONS:
1. Organize your response with clear sections addressing each of the requested four topics.
2. Back your analysis with references to the market drivers and indicators mentioned in the context material.
3. If any information is missing, acknowledge the gap rather than inventing data.
4. Include a balanced perspective on EM opportunities and risks, considering both bullish and bearish factors.
5. Present your answer in an organized, multi-paragraph format with appropriate headings and bullet points.
    """

    messages = [
        {
            "role": "system",
            "content": (
                system_prompt
            ),
        },
        {   
            "role": "user",
            "content": (
                user_prompt
            ),
        },
    ]

    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="sonar-deep-research",
        messages=messages,
    )
    # Store full response in a variable
    full_response = response.choices[0].message.content
    # Print in a readable format
    print("Complete response:")
    print(full_response)
    return full_response  # Return the response so it can be used by the tool

def optimize():

    current_date = datetime.now().strftime('%Y-%m-%d')

    current_time = datetime.now().strftime('%H:%M:%S')
    
    try:
        # Use existing functionality if available
        formatted_pos = format_portfolio_positions(positions)
        account_info = extract_account_info(formatted_pos["formatted_output"])
        portfolio_metrics = format_portfolio_metrics(metrics)
        stock_metrics = format_stock_metrics(metrics)
        monthly_performance = format_monthly_performance(monthly_results)
        formatted_diversification = format_diversification(diversification)
        positions_table = formatted_pos.get("positions_table", "")
    except:
        account_info = "Unable to extract account information"
        positions_table = "Unable to format positions table"
        formatted_diversification = "Unable to format diversification"
        portfolio_metrics = "Unable to format portfolio metrics"
        stock_metrics = "Unable to format stock metrics"
        monthly_performance = "Unable to format monthly performance"
    

    # Create the content string with proper f-string interpolation
    content = f"""
Analyze the provided portfolio data and recommend specific actions to improve returns and reduce risk. 
REMEMBER THE CURRENT DATE IS {current_date} 

------------------------------------------------------------------------------------------------------

### Portfolio Positions:

{positions_table}

### Account Information:

{account_info}

### Portfolio Metrics:

{portfolio_metrics}

### Stock Metrics:

{stock_metrics}

### Monthly Performance:

{monthly_performance}

### Diversification:

{formatted_diversification}

### Correlation Matrix:

{correlations}

------------------------------------------------------------------------------------------------------

### Directions:
1. Analyze the current portfolio positions, account information, portfolio metrics, stock metrics, monthly performance, diversification, and correlation matrix
2. Identify the most significant issues affecting portfolio performance (concentration risk, underperforming assets, etc.)
3. Recommend specific actions with exact positions and quantities:
- Which specific positions should be reduced or sold completely
- Which specific positions should be increased
- New long positions that should be added (with specific tickers and allocation amounts) YOU CAN CHOOSE ANY STOCK FROM ANY SECTOR OR INDUSTRY OR SUBINDUSTRY AND FROM ANY COUNTRY, AS LONG AS ITS A GOOD INVESTMENT AND WILL MAKE MONEY
- New short positions that should be added (with specific tickers and allocation amounts) YOU CAN CHOOSE ANY STOCK FROM ANY SECTOR OR INDUSTRY OR SUBINDUSTRY AND FROM ANY COUNTRY, AS LONG AS ITS A GOOD INVESTMENT AND WILL MAKE MONEY
- Exact percentage adjustments to each position
4. Explain how each recommendation will improve the portfolio's return potential
5. Provide a clear implementation plan 
6. Quantify the expected improvement in key metrics (volatility, returns, diversification)

### ACTIONS YOU ARE ALLOWED TO TAKE:
1. BUY NEW ASSETS
2. SHORT NEW ASSETS
3. REDUCE EXISTING POSITIONS
4. INCREASE EXISTING POSITIONS
4. HOLD POSITIONS (DO NOT CHANGE)

### ASSETS YOU ARE ALLOWED TO BUY:
1. STOCKS/EQUITIES
2. BONDS
3. EXCHANGE TRADED FUNDS (ETFS)
4. COMMODITIES
5. REAL ESTATE INVESTMENT TRUSTS (REITs)
6. FOREIGN EXCHANGE

### FORMAT YOUR RESPONSE WITH THESE SECTIONS(BE CONCISE AND TO THE POINT):
1. Portfolio Assessment
2. Key Issues
3. Specific Recommendations (with exact position sizes and tickers)
4. Implementation Plan
5. Expected Outcome

### ONCE YOU HAVE FINISHED YOUR ANALYSIS, PLEASE PROVIDE THE NEW PORTFOLIO WITH YOUR SUGGESTED CHANGES IN THIS FORMAT(PRINT THIS HORIZONTALLY IN A TABLE):
Stock Ticker: New Position Size | Quantity | New Allocation | New Market Value

### THEN I WANT THE EXACT TRADE EXECUTION INSTRUCTIONS IN THIS FORMAT:
Trade Action: [action(buy/sell/hold)] | Ticker: [ticker] | Quantity: [quantity]

### THIS IS THE FORMAT YOU SHOULD USE(THESE ARE EXAMPLES):
• SELL 'SOME STOCK' (100 shares) --> entire position
• SELL 'SOME STOCK' (50 shares) --> reduce from 100 → 50
• HOLD 'SOME STOCK' (50 shares)
• BUY 'SOME STOCK' (500 shares)

### RULES:
1. NO HALLUCINATIONS, IF THERE IS SOMETHING YOU DO NOT KNOW OR IF THERE IS DATA MISSING, SAY YOU DO NOT KNOW, AND PROCEED LOGICALLY.
2. BE VERY SPECIFIC AND EXACT WITH YOUR RECOMMENDATIONS.
3. BE SUCCUINCT AND CONCISE, BUT MAKE SURE TO EXPLAIN YOUR REASONING.
4. BE SUCCESSFUL AND MAKE MONEY.
5. BE CREATIVE IN YOUR STRATEGIES AND THINK OUTSIDE THE BOX.
6. KEEP 10% OF THE PORTFOLIO IN CASH.
7. None of the positions should be less than $10,000
"""
    
    # Call the OpenAI API with tool calling ability
    try:
        # Get API key from environment or use the hardcoded one as fallback
        api_key = os.environ.get("OPENAI_API_KEY", OpenAI_API_KEY)
        client = OpenAI(api_key=api_key)
        
        # Define tools
        energy_stocks_tool = {
            "type": "function",
            "function": {
                "name": "query_energy_stocks",
                "description": "Get a list of energy stocks from the coal and consumable fuels industry",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

        search_tool = {
            "type": "function",
            "function": {
                "name": "free_search",
                "description": "Search the internet for critical investment information that will enhance portfolio optimization. Construct DETAILED and SPECIFIC search queries to get the highest quality information. Follow these guidelines for effective searches:\n\n1. Be specific about the information you need (e.g., instead of 'tech stocks' use 'semiconductor industry outlook 2025 and top mid-cap opportunities')\n2. Include relevant timeframes in your query\n3. Target specific sectors, industries, or market segments\n4. Request numerical data like P/E ratios, growth rates, or market projections\n5. Break complex research needs into multiple focused searches\n\nYou should conduct AT LEAST 3-5 searches on different topics before making final recommendations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Detailed, specific search query to find high-quality investment information. Include timeframes, metrics, sectors, or specific market segments."
                        }
                    },
                    "required": ["query"]
                }
            }
        }
        
        equity_research_tool = {
            "type": "function",
            "function": {
                "name": "equity_research_analyst",
                "description": "Generate a comprehensive equity research report that provides actionable insights into the global equity market. The report covers market trends, sector performance, geopolitical events, investor sentiment, emerging opportunities, key risks, market valuation, and investment styles.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        commodities_research_tool = {
            "type": "function",
            "function": {
                "name": "commodities_analyst",
                "description": "Generate a comprehensive commodities market analysis covering energy, metals, and agricultural markets. The report includes supply-demand fundamentals, price trends, physical market dynamics, inventory levels, forward curves, and geopolitical factors affecting commodity prices.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        etf_research_tool = {
            "type": "function",
            "function": {
                "name": "etf_analyst",
                "description": "Generate a comprehensive ETF market analysis covering equity, fixed income, commodity, and specialty ETFs. The report includes performance analysis, structural considerations, liquidity conditions, and specific ETF recommendations with rationale.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        treasuries_tool = {
            "type": "function",
            "function": {
                "name": "treasuries_analyst",
                "description": "Generate a comprehensive US Treasury market analysis covering yield curves, interest rate trends, and macroeconomic factors. The report includes analysis of recent economic data's impact on government bonds, behavior of the 2s10s yield curve, and upcoming factors likely to influence Treasury rates.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        foreign_exchange_tool = {
            "type": "function",
            "function": {
                "name": "foreign_exchange_analyst",
                "description": "Generate a comprehensive foreign exchange market analysis covering currency valuation methodologies and key drivers of the U.S. Dollar. The report includes analysis of parity conditions, fundamental analysis, market-based valuation, and how these models interact over different time horizons.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        ig_credit_tool = {
            "type": "function",
            "function": {
                "name": "ig_credit_analyst",
                "description": "Generate a comprehensive analysis of U.S. Investment Grade (IG) credit markets covering corporate fundamentals, interest rates, credit spreads, economic conditions, and sector-specific trends. The report examines key drivers affecting IG bond performance and provides outlook for credit markets.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        high_yield_tool = {
            "type": "function",
            "function": {
                "name": "high_yield_analyst",
                "description": "Generate a comprehensive analysis of high yield bonds and emerging market debt, comparing U.S. high yield factors with emerging market considerations. The report covers credit spreads, default risks, liquidity conditions, and macroeconomic influences affecting these higher-yielding fixed income assets.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        emerging_markets_tool = {
            "type": "function",
            "function": {
                "name": "emerging_market_analyst",
                "description": "Generate a comprehensive analysis of emerging markets (EM) equities and bonds, examining both global macro drivers and domestic fundamentals. The report covers the interplay between U.S. rates, risk sentiment, commodity prices, local economic conditions, and political factors that influence EM asset performance.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        # Helper function to process tool responses
        def process_tool_call(tool_call):
            function_name = tool_call.function.name
            
            # Get the appropriate response based on the tool called
            tool_response = ""
            if function_name == "query_energy_stocks":
                print(f"*** TOOL USED: query_energy_stocks ***")
                
                # Query real energy stocks from the database
                energy_stocks = query_energy_stocks()
                
                # Format the response
                energy_response = "Here are coal and consumable fuels stocks from your database that you could consider for your portfolio:\n\n"
                
                for i, stock in enumerate(energy_stocks, 1):
                    energy_response += f"{i}. {stock['ticker']} ({stock['short_name']}) - {stock['sub_industry']}, P/E: {stock['p_e']}, Market Cap: ${stock['market_cap']:.2f}, Alpha (3m): {stock['alpha_m_3']}, Beta (3m): {stock['beta_m_3']}\n"
                
                energy_response += "\nThese stocks represent the coal and consumable fuels sub-industry within the energy sector. They typically have lower P/E ratios than other sectors and varying levels of market volatility as indicated by their beta values. Their alpha values show their performance relative to the market benchmark over the last 3 months."
                
                energy_response += "\n\nKey metrics explanation:"
                energy_response += "\n- P/E: Price-to-earnings ratio, lower values may indicate better value"
                energy_response += "\n- Market Cap: Total market value of the company's shares"
                energy_response += "\n- Alpha (3m): Excess return relative to benchmark over 3 months (positive is better)"
                energy_response += "\n- Beta (3m): Volatility relative to market over 3 months (>1 means more volatile than market)"
                
                energy_response += "\n\nFor more detailed information about specific coal stocks or other investment options, you can use the web_search tool. Consider searching for recent financial performance, growth projections, and analyst ratings for the most promising coal stocks."
                
                tool_response = energy_response
                
            elif function_name == "free_search":
                function_args = json.loads(tool_call.function.arguments)
                query = function_args.get("query")
                print(f"*** TOOL USED: free_search for query: '{query}' ***")
                
                # Use the search function to get information from the web
                system_prompt = """You are a financial research analyst with 20+ years of experience who provides comprehensive, data-rich investment analysis. 
                Your responses should include specific numbers, trends, metrics, and expert insights. 
                Include relevant data points like P/E ratios, growth rates, market caps, dividend yields, sector-specific metrics, and comparative statistics whenever available. 
                Structure your response with clear sections and emphasize actionable insights that would help with portfolio construction. Be thorough, precise, and quantitative."""
                
                # Call the search function (it will print the full response internally)
                try:
                    search_response = free_search(system_prompt, query)
                except Exception as e:
                    print(f"Error during web search: {e}")
                    search_response = f"I attempted to search for information about '{query}' but encountered an error. Please try a different search query or continue with the available information."
                
                # Format the response appropriately
                tool_response = f"Web Search Results for: '{query}'\n\n{search_response}\n\nNOTE: This information should be incorporated into your portfolio analysis. You should conduct additional searches on other topics to build a comprehensive view before making final recommendations."
            
            elif function_name == "equity_research_analyst":
                print(f"*** TOOL USED: equity_research_analyst ***")
                
                # Call the equity research analyst function
                try:
                    research_report = equity_research_analyst()
                except Exception as e:
                    print(f"Error generating equity research report: {e}")
                    research_report = "I attempted to generate a comprehensive equity research report but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Equity Research Report:\n\n{research_report}\n\nNOTE: This comprehensive market analysis should form the foundation of your portfolio optimization strategy. Consider how these trends, opportunities, and risks impact your investment decisions."
            
            elif function_name == "commodities_analyst":
                print(f"*** TOOL USED: commodities_analyst ***")
                
                # Call the commodities analyst function
                try:
                    research_report = commodities_analyst()
                except Exception as e:
                    print(f"Error generating commodities research report: {e}")
                    research_report = "I attempted to generate a comprehensive commodities market analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Commodities Market Analysis:\n\n{research_report}\n\nNOTE: Use this commodities market analysis to inform your allocation to energy, metals, agriculture, and other commodity-related assets. Consider both direct commodity exposure and indirect exposure through equities in commodity-producing companies."
            
            elif function_name == "etf_analyst":
                print(f"*** TOOL USED: etf_analyst ***")
                
                # Call the ETF analyst function
                try:
                    research_report = etf_analyst()
                except Exception as e:
                    print(f"Error generating ETF research report: {e}")
                    research_report = "I attempted to generate a comprehensive ETF market analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"ETF Market Analysis:\n\n{research_report}\n\nNOTE: Use this ETF analysis to identify optimal vehicles for implementing your asset allocation and tactical views. Consider both the underlying exposures and structural characteristics of recommended ETFs."
            
            elif function_name == "treasuries_analyst":
                print(f"*** TOOL USED: treasuries_analyst ***")
                
                # Call the treasuries analyst function
                try:
                    research_report = treasuries_analyst()
                except Exception as e:
                    print(f"Error generating treasuries research report: {e}")
                    research_report = "I attempted to generate a comprehensive US Treasury market analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"US Treasury Market Analysis:\n\n{research_report}\n\nNOTE: Use this US Treasury market analysis to inform your allocation to government bonds and Treasury securities. Consider how the current interest rate environment affects both your fixed income holdings and other asset classes."
            
            elif function_name == "foreign_exchange_analyst":
                print(f"*** TOOL USED: foreign_exchange_analyst ***")
                
                # Call the foreign exchange analyst function
                try:
                    research_report = foreign_exchange_analyst()
                except Exception as e:
                    print(f"Error generating foreign exchange research report: {e}")
                    research_report = "I attempted to generate a comprehensive foreign exchange market analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Foreign Exchange Market Analysis:\n\n{research_report}\n\nNOTE: Use this foreign exchange analysis to inform your allocation to foreign currencies and currency-hedged assets. Consider how the current exchange rate environment affects both your foreign currency holdings and other asset classes."
            
            elif function_name == "ig_credit_analyst":
                print(f"*** TOOL USED: ig_credit_analyst ***")
                
                # Call the IG credit analyst function
                try:
                    research_report = ig_credit_analyst()
                except Exception as e:
                    print(f"Error generating IG credit research report: {e}")
                    research_report = "I attempted to generate a comprehensive Investment Grade (IG) credit market analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Investment Grade Credit Market Analysis:\n\n{research_report}\n\nNOTE: Use this IG credit analysis to inform your allocation to investment grade corporate bonds. Consider how credit fundamentals, interest rates, and market technicals affect both your fixed income holdings and other asset classes."
            
            elif function_name == "high_yield_analyst":
                print(f"*** TOOL USED: high_yield_analyst ***")
                
                # Call the high yield analyst function
                try:
                    research_report = high_yield_analyst()
                except Exception as e:
                    print(f"Error generating high yield research report: {e}")
                    research_report = "I attempted to generate a comprehensive high yield and emerging markets debt analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"High Yield & Emerging Markets Debt Analysis:\n\n{research_report}\n\nNOTE: Use this high yield and emerging markets analysis to inform your allocation to higher yielding fixed income assets. Consider how credit risk, liquidity conditions, and macroeconomic factors differ between U.S. high yield and emerging market debt."
            
            elif function_name == "emerging_market_analyst":
                print(f"*** TOOL USED: emerging_market_analyst ***")
                
                # Call the emerging market analyst function
                try:
                    research_report = emerging_market_analyst()
                except Exception as e:
                    print(f"Error generating emerging markets research report: {e}")
                    research_report = "I attempted to generate a comprehensive emerging markets analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Emerging Markets Analysis:\n\n{research_report}\n\nNOTE: Use this emerging markets analysis to inform your allocation to both EM equities and fixed income. Consider how global macro factors and domestic fundamentals influence different EM assets, and how they might perform in various economic scenarios."
            
            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": tool_response
            }
        
        # Recursive function to handle multiple rounds of tool calls
        def handle_conversation(messages, tools, round_num=1, max_rounds=15):
            print(f"\nStarting conversation round {round_num}...")
            
            if round_num > max_rounds:
                print(f"Reached maximum rounds ({max_rounds}). Stopping to prevent infinite loop.")
                return messages[-1].content if hasattr(messages[-1], 'content') else "Maximum conversation rounds reached without final response."
            
            # Call the API
            response = client.chat.completions.create(
                model="o1",
                top_p=1.0,
                messages=messages,
                tools=tools if round_num < max_rounds else None  # Stop offering tools in final round
            )
            
            # Get the response message
            response_message = response.choices[0].message
            
            # Check for tool calls
            tool_calls = response_message.tool_calls
            
            if tool_calls:
                print(f"Round {round_num}: Found {len(tool_calls)} tool call(s)")
                
                # Add the assistant's message to the conversation
                messages.append(response_message)
                
                # Process each tool call
                for tool_call in tool_calls:
                    tool_response = process_tool_call(tool_call)
                    messages.append(tool_response)
                
                # Recursive call to handle next round
                return handle_conversation(messages, tools, round_num + 1, max_rounds)
            else:
                # No more tool calls, we have our final response
                print(f"Round {round_num}: No tool calls, received final response")
                return response_message.content
                
        print("Calling OpenAI API with tools...")
        
        # Initialize the conversation
        system_message = {
            "role": "system",
            "content": "You are an elite portfolio manager who builds sophisticated investment strategies based on deep market research. Your exceptional track record comes from conducting EXTENSIVE RESEARCH before making any recommendation.\n\nRESEARCH METHODOLOGY REQUIREMENTS:\n1. Conduct AT LEAST 5-7 detailed searches on different aspects of the market before making recommendations\n2. For each search query, construct DETAILED and SPECIFIC prompts (30-50 words) that will yield high-quality information\n3. Research multiple sectors, market caps, geographies, and asset classes\n4. Analyze macroeconomic trends, sector rotations, valuation metrics, and risk factors\n5. Investigate both tactical (1-6 month) and strategic (1-3 year) opportunities\n\nWHEN CONSTRUCTING SEARCH QUERIES:\n* Include specific timeframes (e.g., 'Q3 2025 outlook')\n* Request numerical data ('P/E ratios for mid-cap industrial stocks')\n* Target precise sectors or sub-sectors ('semiconductor equipment manufacturers' not just 'tech')\n* Ask for comparisons ('small cap vs large cap performance during rate cuts')\n* Seek expert consensus ('analyst expectations for healthcare sector 2025-2026')\n\nEXAMPLE HIGH-QUALITY SEARCH QUERIES:\n- 'US small cap industrial stocks with P/E under 15 and positive earnings revisions for 2025, focus on aerospace suppliers and automation'\n- 'Healthcare sector rotation analysis: which subsectors outperform when inflation moderates and Fed cuts rates, historical data 2000-2024'\n- 'Top performing dividend aristocrats with international revenue exposure, valuation metrics and 2025 earnings projections'\n\nONLY after conducting this comprehensive research should you formulate your final recommendation."
        }
        
        user_message = {
            "role": "user",
            "content": content + "\n\nBefore making recommendations, conduct thorough market research in this sequence:\n\n" + \
            "1. MARKET ANALYSIS (REQUIRED, MUST CONDUCT ALL TOOLS)\n" + \
            "IMPORTANT: You must conduct all the tools in the order they are listed below before conducting any targeted research.\n" + \
            "   - Use equity_research_analyst for comprehensive equity market insights\n" + \
            "   - Use treasuries_analyst for detailed US Treasury market analysis\n" + \
            "   - Use foreign_exchange_analyst for currency valuation and FX market insights\n" + \
            "   - Use ig_credit_analyst for Investment Grade corporate bond analysis\n" + \
            "   - Use high_yield_analyst for High Yield and Emerging Market debt analysis\n" + \
            "   - Use emerging_market_analyst for detailed Emerging Markets equity and fixed income analysis\n" + \
            "   - Use commodities_analyst if the portfolio includes or should include commodities\n" + \
            "   - Use etf_analyst to identify optimal ETF vehicles for implementation\n\n" + \
            "2. TARGETED RESEARCH (AS NEEDED)\n" + \
            "   - Use free_search to investigate specific opportunities or concerns \n" + \
            "   - Use free_search to search any information you need to make the best portfolio recommendations\n\n"    
        }
        
        initial_messages = [system_message, user_message]
        available_tools = [energy_stocks_tool, search_tool, equity_research_tool, commodities_research_tool, etf_research_tool, treasuries_tool, foreign_exchange_tool, ig_credit_tool, high_yield_tool, emerging_markets_tool]
        
        # Start the conversation without forcing a tool call
        final_content = handle_conversation(initial_messages, available_tools)
        
        print("\n=== Final Portfolio Recommendation ===")
        
        if final_content:
            print(final_content)
            return final_content
        else:
            print("No content in final response, returning what's available.")
            return "No recommendation was generated."
            
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        import traceback
        traceback.print_exc()
        return f"An error occurred while calling the OpenAI API: {str(e)}"


# optimize()
