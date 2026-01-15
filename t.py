"""Quick test for BatchPortfolioReturnsService."""
from app.services.portfolio import BatchPortfolioReturnsService
from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import Portfolio
import time

start_time = time.time()

# Get some portfolio IDs from DB
with UserSession() as session:
    portfolios = session.query(Portfolio.id, Portfolio.name).limit(20).all()
    portfolio_ids = [str(p.id) for p in portfolios]
    print(f"Found {len(portfolio_ids)} portfolios:")
    for p in portfolios:
        print(f"  - {p.name}: {p.id}")

if not portfolio_ids:
    print("No portfolios found!")
    exit(1)

print(f"\nTesting BatchPortfolioReturnsService with {len(portfolio_ids)} portfolios...")
print("-" * 60)

# Test the service
service = BatchPortfolioReturnsService(
    portfolio_ids=portfolio_ids,
    years=3
)

print(f"Unique tickers across all portfolios: {len(service.unique_tickers)}")
print(f"Tickers: {service.unique_tickers[:10]}{'...' if len(service.unique_tickers) > 10 else ''}")
print(f"Returns DataFrame shape: {service.returns_df.shape}")

# Get returns
results = service.get_all_returns()

print(f"\nResults for {len(results)} portfolios:")
for pid, returns in results.items():
    print(f"  - Portfolio {pid[:8]}...: {len(returns)} data points")
    if returns:
        print(f"    First: {returns[0]['date'][:10]}, Last: {returns[-1]['date'][:10]}")
        print(f"    Final cumulative return: {returns[-1]['cumulativeReturn']:.2%}")

print("\n✅ Test completed successfully!")
print(f"Total time taken: {time.time() - start_time:.2f} seconds")