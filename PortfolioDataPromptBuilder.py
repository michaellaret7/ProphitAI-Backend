import json
from PortfolioData import get_portfolio_holdings, analyze_portfolio_correlations, connect_to_ib, calculate_portfolio_metrics, calculate_monthly_portfolio_metrics, calculate_monthly_stock_metrics, analyze_portfolio_diversification, analyze_portfolio_correlations
from openai import OpenAI
import numpy as np
import os
from datetime import datetime
import psycopg2
import pandas as pd

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
    system_prompt = """You are an elite equity research analyst with 20+ years experience at top investment banks. Your expertise includes:

- Data-driven market analysis with multiple reliable sources
- Quantitative analysis of trends and integration with macroeconomic factors
- Providing precise, actionable insights backed by verifiable data
- Identifying both obvious and hidden market risks across timeframes
- Recommending opportunities that enhance risk-adjusted returns

Focus on information that directly impacts investment decisions. Provide both defensive strategies and growth opportunities with current market data."""

    user_prompt = """
GOAL: Provide comprehensive equity market analysis across multiple timeframes (1w, 1m, 3m, 6m) for portfolio optimization.

FORMAT:

1. EXECUTIVE SUMMARY
   - Current market conditions, key recommendations, major opportunities/risks

2. MARKET PERFORMANCE 
   - Major indices (S&P 500, Nasdaq, Dow, Russell, FTSE, DAX, Nikkei, Shanghai) across all timeframes
   - Volume, volatility (VIX), and breadth indicators

3. SECTOR ANALYSIS
   - Performance ranking of all major sectors across all timeframes
   - Rotation patterns, correlation analysis, notable outperformers/underperformers

4. MACRO FACTORS
   - Central bank policies, rates, inflation, employment, currencies, yield curve

5. GEOPOLITICAL IMPACT
   - Current tensions, policy changes, upcoming events affecting markets

6. SENTIMENT & TECHNICALS
   - Institutional vs retail positioning, fund flows, technical indicators

7. VALUATIONS
   - P/E, P/S, P/B, CAPE compared to historical averages
   - Earnings trends, margin analysis, valuation dispersions

8. FACTOR PERFORMANCE
   - Value, Growth, Quality, Momentum, Size, Low Volatility across timeframes
   - Factor rotation and recommended tilts

9. THEMATIC OPPORTUNITIES
   - Emerging trends, secular growth themes, defensive and contrarian opportunities

10. OUTLOOK
    - Short and medium-term forecasts, key catalysts, inflection points

REQUIREMENTS:
- Include precise numerical data and historical comparisons
- Specify timeframes for trends (accelerating/decelerating)
- Support claims with specific events/releases
- Highlight contradictory indicators
- Cover global markets (not just individual stocks)
- Use reliable sources (Bloomberg, Reuters, FT, WSJ, major banks)
- Current date: March 7th, 2025
- Clearly distinguish facts from opinions
- Label estimates when exact data unavailable
- Consider potential tail risks
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


def commodities_analyst():
    system_prompt = """You are a senior commodities analyst with 20+ years experience at major trading firms and investment banks. Your expertise includes:

- Fundamental supply-demand analysis across energy, metals, and agricultural markets
- Price trend analysis incorporating seasonal patterns and cyclical behaviors
- Physical market dynamics including storage, transportation, and delivery constraints
- Geopolitical risk assessment for commodity-producing regions
- Macro drivers of commodity prices (inflation, currency, interest rates)

Focus on actionable commodity market insights for portfolio allocation. Balance risk management with opportunity identification."""

    user_prompt = """
GOAL: Provide comprehensive commodities market analysis across multiple timeframes (1w, 1m, 3m, 6m) for portfolio optimization.

FORMAT:

1. EXECUTIVE SUMMARY
   - Current commodities market conditions, key recommendations, major opportunities/risks

2. COMMODITIES PERFORMANCE
   - Major commodity indices and benchmarks across all timeframes
   - Key individual commodities (oil, gas, gold, silver, copper, agriculture) performance
   - Volatility metrics and term structure (contango/backwardation)

3. SECTOR ANALYSIS
   - Performance ranking of commodity sectors (Energy, Precious Metals, Industrial Metals, Agriculture)
   - Inter-commodity spreads and relative value opportunities
   - Supply-demand balances by sector

4. MACRO DRIVERS
   - Dollar strength/weakness impact on commodity prices
   - Inflation trends and commodity response
   - Interest rate environment and carrying costs
   - Global economic growth and commodity demand outlook

5. GEOPOLITICAL FACTORS
   - Production disruptions and supply concerns
   - Trade policies, sanctions, and export restrictions
   - Resource nationalism and regulatory developments
   - Weather patterns and climate-related impacts

6. MARKET POSITIONING
   - Speculative vs. commercial positioning (COT reports)
   - ETF flows and investor sentiment
   - Physical market premiums/discounts
   - Technical indicators and price momentum

7. INVENTORY & STORAGE
   - Current inventory levels vs. 5-year averages
   - Storage economics and capacity constraints
   - Seasonal stock patterns and anomalies
   - Production capacity utilization rates

8. CURVE DYNAMICS
   - Forward curve structures across commodities
   - Roll yields and implications for investors
   - Calendar spread opportunities
   - Inter-commodity spread relationships

9. THEMATIC OPPORTUNITIES
   - Secular trends affecting commodities (energy transition, electrification)
   - Supply constraints and capacity additions
   - Substitution and demand destruction price levels
   - Emerging market demand growth

10. OUTLOOK
    - Short and medium-term price forecasts with probability distributions
    - Key catalysts and event risks to monitor
    - Seasonal patterns likely to emerge
    - Recommended positioning strategies

REQUIREMENTS:
- Include precise numerical data (prices, basis points, percentages)
- Compare current levels to historical averages and seasonal norms
- Specify supply-demand balances with quantitative estimates
- Support claims with specific market events
- Highlight divergences between physical and financial markets
- Use reliable sources (Bloomberg, Reuters, IEA, EIA, USDA, major banks)
- Current date: March 7th, 2025
- Distinguish between structural and cyclical trends
- Address potential external shocks (weather, geopolitics)
- Consider cross-asset implications (FX, rates, equities)
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


def fixed_income_analyst():
    system_prompt = """You are a veteran fixed income strategist with 20+ years experience at premier investment firms. Your expertise includes:

- Interest rate analysis across global yield curves and monetary policy regimes
- Credit market assessment from investment grade to high yield and emerging markets
- Macro factors driving bond yields, spreads, and returns
- Duration, convexity, and yield curve positioning strategies
- Fixed income relative value across sectors, regions, and structures

Focus on delivering actionable fixed income insights that directly impact portfolio construction. Provide both risk management strategies and alpha generation opportunities."""

    user_prompt = """
GOAL: Provide comprehensive fixed income market analysis across multiple timeframes (1w, 1m, 3m, 6m) for portfolio optimization.

FORMAT:

1. EXECUTIVE SUMMARY
   - Current fixed income market conditions and key investment themes
   - Strategic recommendations and major opportunities/risks

2. RATES MARKET PERFORMANCE
   - Sovereign yield curves (US, EU, UK, Japan) across all timeframes
   - Real yields and breakeven inflation rates
   - Yield curve shape metrics (slope, curvature)
   - Volatility conditions (MOVE index) and rate expectations

3. CREDIT MARKET ANALYSIS
   - Performance of credit sectors (IG, HY, EM, securitized products)
   - Credit spread evolution and relative value
   - Credit quality trends and rating migration
   - Default rates and recovery expectations

4. CENTRAL BANK POLICY
   - Policy rates and forward guidance across major central banks
   - Balance sheet policies (QE/QT) and liquidity conditions
   - Market vs. central bank rate expectations divergence
   - Impact of recent policy decisions and communications

5. ECONOMIC FUNDAMENTALS
   - Growth and inflation outlook impact on fixed income
   - Labor market conditions and wage pressures
   - Fiscal policy developments and government funding needs
   - Current position in the credit cycle

6. MARKET TECHNICALS
   - Supply/demand dynamics (issuance, redemptions, fund flows)
   - Investor positioning and sentiment indicators
   - Liquidity conditions and bid-ask spreads
   - Foreign investor activity and currency-hedged yields

7. RELATIVE VALUE
   - Cross-market spreads and opportunities
   - Sector rotation recommendations
   - Duration positioning considerations
   - Security selection themes

8. CURVE POSITIONING
   - Yield curve strategies (flatteners, steepeners)
   - Roll-down analysis and carry opportunities
   - Inflection points and optimal positioning
   - Scenario analysis across different rate environments

9. THEMATIC OPPORTUNITIES
   - Special situations and dislocations
   - Structural changes in fixed income markets
   - Regulatory impacts on bond markets
   - Innovation in fixed income products

10. OUTLOOK
    - Rate and spread forecasts with probability scenarios
    - Key catalysts and event risks to monitor
    - Optimal portfolio positioning strategies
    - Duration and credit exposure recommendations

REQUIREMENTS:
- Include precise numerical data (yields, spreads, basis points)
- Compare current levels to historical ranges
- Specify expected returns and risk metrics for recommended positions
- Support claims with specific economic data points and market events
- Highlight inconsistencies in market pricing
- Use reliable sources (Bloomberg, central banks, major dealer research)
- Current date: March 7th, 2025
- Distinguish between tactical and strategic recommendations
- Consider correlation with other asset classes
- Address inflation and liquidity risks
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
    system_prompt = """You are a leading ETF strategist with 20+ years experience across asset management and investment research. Your expertise includes:

- ETF structure, mechanics, and liquidity analysis
- Performance and tracking efficiency evaluation
- Factor, thematic, and sector ETF evaluation
- ETF portfolio construction techniques
- Total cost analysis including expense ratios, tracking error, and trading costs

Focus on identifying optimal ETF selections for various portfolio objectives. Evaluate both strategic and tactical ETF opportunities across asset classes."""

    user_prompt = """
GOAL: Provide comprehensive ETF market analysis across multiple timeframes (1w, 1m, 3m, 6m) for portfolio optimization.

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

ASSETS YOU ARE ALLOWED TO BUY:
1. STOCKS/EQUITIES
2. BONDS
3. EXCHANGE TRADED FUNDS (ETFS)
4. COMMODITIES
5. REAL ESTATE INVESTMENT TRUSTS (REITs)
6. FOREIGN EXCHANGE

Format your response with these sections(BE CONCISE AND TO THE POINT):
1. Portfolio Assessment
2. Key Issues
3. Specific Recommendations (with exact position sizes and tickers)
4. Implementation Plan
5. Expected Outcome

ONCE YOU HAVE FINISHED YOUR ANALYSIS, PLEASE PROVIDE THE NEW PORTFOLIO WITH YOUR SUGGESTED CHANGES IN THIS FORMAT(PRINT THIS HORIZONTALLY IN A TABLE):
Stock Ticker: New Position Size | Quantity | New Allocation | New Market Value

THEN I WANT THE EXACT TRADE EXECUTION INSTRUCTIONS IN THIS FORMAT:
Trade Action: [action(buy/sell/hold)] | Ticker: [ticker] | Quantity: [quantity]

THIS IS THE FORMAT YOU SHOULD USE(THESE ARE EXAMPLES):
• SELL 'SOME STOCK' (100 shares) --> entire position
• SELL 'SOME STOCK' (50 shares) --> reduce from 100 → 50
• HOLD 'SOME STOCK' (50 shares)
• BUY 'SOME STOCK' (500 shares)

RULES:
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
        
        fixed_income_research_tool = {
            "type": "function",
            "function": {
                "name": "fixed_income_analyst",
                "description": "Generate a comprehensive fixed income market analysis covering sovereign bonds, credit markets, yield curves, and interest rate environments. The report includes central bank policies, economic fundamentals, relative value opportunities, and optimal positioning strategies.",
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
            
            elif function_name == "fixed_income_analyst":
                print(f"*** TOOL USED: fixed_income_analyst ***")
                
                # Call the fixed income analyst function
                try:
                    research_report = fixed_income_analyst()
                except Exception as e:
                    print(f"Error generating fixed income research report: {e}")
                    research_report = "I attempted to generate a comprehensive fixed income market analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Fixed Income Market Analysis:\n\n{research_report}\n\nNOTE: Use this fixed income analysis to optimize bond allocations, duration positioning, and credit exposure in your portfolio. Consider how the current interest rate environment affects both your fixed income holdings and other asset classes."
            
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
            
            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": tool_response
            }
        
        # Recursive function to handle multiple rounds of tool calls
        def handle_conversation(messages, tools, round_num=1, max_rounds=10):
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
            "1. MARKET ANALYSIS (REQUIRED)\n" + \
            "   - Use equity_research_analyst for comprehensive equity market insights\n" + \
            "   - Use fixed_income_analyst if the portfolio includes or should include bonds\n" + \
            "   - Use commodities_analyst if the portfolio includes or should include commodities\n" + \
            "   - Use etf_analyst to identify optimal ETF vehicles for implementation\n\n" + \
            "2. TARGETED RESEARCH (AS NEEDED)\n" + \
            "   - Use free_search to investigate specific opportunities or concerns \n" + \
            "   - Use free_search to search any information you need to make the best portfolio recommendations\n\n"    
        }
        
        initial_messages = [system_message, user_message]
        available_tools = [energy_stocks_tool, search_tool, equity_research_tool, fixed_income_research_tool, commodities_research_tool, etf_research_tool]
        
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

optimize()
