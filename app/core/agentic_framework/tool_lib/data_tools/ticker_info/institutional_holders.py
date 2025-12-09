from concurrent.futures import ThreadPoolExecutor, as_completed
from app.db.core.pull_fmp_data import FMP_API_DATA

def get_institutional_holders(ticker: str, year: int, quarter: int, row_limit: int = 1000):
    """
    Retrieves institutional holders for a given ticker using parallel requests.
    """
    fmp_data = FMP_API_DATA()

    def fetch_page(page: int):
        return fmp_data.get_institutional_holder_analytics(ticker, year, quarter, page=page, limit=100)

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_page, page): page for page in range(1, 20)}
        for future in as_completed(futures):
            data = future.result()
            if data:
                results.extend(data)
    
    results = [r for r in results if r['changeInSharesNumber'] != 0] # remove firms that didn't buy or sell any shares

    return results


if __name__ == "__main__":
    import time
    start_time = time.time()
    data = get_institutional_holders("AAL", 2025, 3)
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")
    print(len(data))
    print(data[0]['investorName'])
    print(data[0]['changeInSharesNumber'])
    print(data[0])
