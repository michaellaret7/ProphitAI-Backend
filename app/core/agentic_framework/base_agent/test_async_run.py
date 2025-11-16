"""
Run multiple synchronous sub-agents in parallel using asyncio.

This allows running existing synchronous agents in parallel
WITHOUT modifying the BaseAgent or SubAgent class structure.

Uses asyncio.to_thread() to wrap synchronous agent.run() calls,
with semaphore-based concurrency limiting and error handling.
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
from app.core.agentic_framework.tool_lib.sub_agents.ticker_analyst import TickerAnalyst
from app.utils.decorators.timer import timer


async def run_agents_parallel(
    tickers: List[str],
    max_concurrent: int = 3
) -> List[Dict[str, Any]]:
    """
    Run multiple synchronous agents in parallel with concurrency limiting and error handling.

    Args:
        tickers: List of ticker symbols to analyze
        max_concurrent: Maximum number of agents running simultaneously (prevents API rate limiting)

    Returns:
        List of dicts with ticker, success status, and result/error
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_single_agent(ticker: str) -> Dict[str, Any]:
        """Run single agent with semaphore and error handling"""
        async with semaphore:
            try:
                print(f"Starting analysis for {ticker}...")
                agent = TickerAnalyst(ticker=ticker)
                # asyncio.to_thread runs the sync function in a thread pool
                result = await asyncio.to_thread(agent.run)
                print(f"✓ Completed analysis for {ticker}")
                return {
                    "ticker": ticker,
                    "success": True,
                    "result": result
                }
            except Exception as e:
                print(f"✗ Error analyzing {ticker}: {str(e)}")
                return {
                    "ticker": ticker,
                    "success": False,
                    "error": str(e)
                }

    # Run all agents in parallel with concurrency limit
    results = await asyncio.gather(*[run_single_agent(ticker) for ticker in tickers])
    
    return results


def write_results_to_md(results: List[Dict[str, Any]], output_path: str = None) -> str:
    """
    Write analysis results to a markdown file.
    
    Args:
        results: List of agent results
        output_path: Optional custom path for output file
        
    Returns:
        Path to the created markdown file
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"parallel_agent_results_{timestamp}.md"
    
    # Count successes and failures
    successful = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])
    
    # Build markdown content
    md_lines = [
        "# Parallel Agent Analysis Results",
        f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"\n## Summary",
        f"- **Total Analyses:** {len(results)}",
        f"- **Successful:** {successful}",
        f"- **Failed:** {failed}",
        f"\n---\n",
    ]
    
    # Add detailed results for each ticker
    md_lines.append("## Detailed Results\n")
    
    for result in results:
        ticker = result["ticker"]
        
        if result["success"]:
            res = result["result"]
            md_lines.extend([
                f"### {ticker} ✓",
                f"**Status:** Success",
                f"- **Iterations:** {res.get('iterations', 'N/A')}",
                f"- **Total Tokens:** {res.get('total_tokens', 'N/A')}",
                f"- **Prompt Tokens:** {res.get('prompt_tokens', 'N/A')}",
                f"- **Completion Tokens:** {res.get('completion_tokens', 'N/A')}",
            ])
            
            # Add final answer if available
            if 'final_answer' in res:
                md_lines.extend([
                    f"\n**Analysis:**",
                    f"```",
                    f"{res['final_answer']}",
                    f"```",
                ])
            
            md_lines.append("\n---\n")
        else:
            md_lines.extend([
                f"### {ticker} ✗",
                f"**Status:** Failed",
                f"- **Error:** {result['error']}",
                f"\n---\n",
            ])
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(md_lines))
    
    return output_path

@timer
async def main():
    """Test parallel agent execution"""
    tickers = ["AAPL", "MSFT", "GOOGL"]

    print("="*60)
    print("Testing parallel sub-agent execution")
    print(f"Analyzing tickers: {', '.join(tickers)}")
    print("="*60)

    results = await run_agents_parallel(
        tickers=tickers,
        max_concurrent=3  
    )

    print("\n" + "="*60)
    print("Results Summary:")
    print("="*60)
    for result in results:
        if result["success"]:
            print(f"\n{result['ticker']}: ✓ Success")
            print(f"  Iterations: {result['result'].get('iterations', 'N/A')}")
            print(f"  Tokens: {result['result'].get('total_tokens', 'N/A')}")
        else:
            print(f"\n{result['ticker']}: ✗ Failed")
            print(f"  Error: {result['error']}")

    # Write results to markdown file
    md_path = write_results_to_md(results)
    print(f"\n{'='*60}")
    print(f"Results written to: {md_path}")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    asyncio.run(main())
