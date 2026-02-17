"""Test: New option data methods through the Alpaca broker facade."""

from app.utils.alpaca.broker import Alpaca

alpaca = Alpaca()
TEST_SYMBOL = "SPY260320C00580000"
SEP = "=" * 80


def test_option_bars():
    print(f"\n{SEP}")
    print("1. get_option_bars()")
    print(SEP)
    try:
        bars = alpaca.get_option_bars(TEST_SYMBOL, timeframe='1d', limit=3)
        print(f"Returned {len(bars)} bars")
        for bar in bars:
            print(f"  {bar['timestamp']} | O:{bar['open']} H:{bar['high']} L:{bar['low']} C:{bar['close']} V:{bar['volume']}")
        print(">>> SUCCESS")
    except Exception as e:
        print(f">>> FAILED: {e}")


def test_option_latest_quote():
    print(f"\n{SEP}")
    print("2. get_option_latest_quote()")
    print(SEP)
    try:
        quote = alpaca.get_option_latest_quote(TEST_SYMBOL)
        print(f"  Bid: {quote['bid_price']} x {quote['bid_size']}")
        print(f"  Ask: {quote['ask_price']} x {quote['ask_size']}")
        print(f"  Time: {quote['timestamp']}")
        print(">>> SUCCESS")
    except Exception as e:
        print(f">>> FAILED: {e}")


def test_option_snapshot():
    print(f"\n{SEP}")
    print("3. get_option_snapshot()")
    print(SEP)
    try:
        snap = alpaca.get_option_snapshot(TEST_SYMBOL)
        if 'quote' in snap:
            q = snap['quote']
            print(f"  Quote - Bid: {q['bid_price']} x {q['bid_size']} | Ask: {q['ask_price']} x {q['ask_size']}")
        if 'trade' in snap:
            t = snap['trade']
            print(f"  Trade - Price: {t['price']} Size: {t['size']} Time: {t['timestamp']}")
        if 'greeks' in snap:
            g = snap['greeks']
            print(f"  Greeks - Delta: {g['delta']} Gamma: {g['gamma']} Theta: {g['theta']} Vega: {g['vega']} Rho: {g['rho']}")
        print(">>> SUCCESS")
    except Exception as e:
        print(f">>> FAILED: {e}")


if __name__ == "__main__":
    print(f"Testing option data via Alpaca broker facade")
    print(f"Test symbol: {TEST_SYMBOL}")
    test_option_bars()
    test_option_latest_quote()
    test_option_snapshot()
    print(f"\n{SEP}\nDone.")
