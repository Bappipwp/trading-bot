"""
Smoke test — connects to your Alpaca paper account and verifies:
  1. Authentication works
  2. Account info is readable
  3. Bar data is fetchable
  4. Market clock is readable

No orders are placed. Safe to run anytime.
Run: python smoke_test.py
"""

import sys
from broker.alpaca_client import AlpacaClient
from data.feed import DataFeed
import config


def check(label: str, fn):
    try:
        result = fn()
        print(f"  [OK] {label}")
        return result
    except Exception as e:
        print(f"  [FAIL] {label}: {e}")
        return None


def main():
    print("\n=== Smoke Test ===")
    print(f"Mode: {'PAPER' if config.PAPER else '*** LIVE ***'}\n")

    broker = AlpacaClient()
    feed = DataFeed(broker.data)

    account = check("Connect to Alpaca + get account", broker.get_account)
    if account:
        print(f"         equity=${float(account.equity):,.2f}  cash=${float(account.cash):,.2f}")

    clock = check("Get market clock", broker.trading.get_clock)
    if clock:
        print(f"         market {'OPEN' if clock.is_open else 'CLOSED'}")

    bars = check(
        f"Fetch bars for {config.SYMBOLS[0]}",
        lambda: feed.get_latest_bars([config.SYMBOLS[0]], n=5),
    )
    if bars:
        df = bars.get(config.SYMBOLS[0])
        if df is not None and not df.empty:
            print(f"         last close=${df['close'].iloc[-1]:.2f}  ({len(df)} bars)")

    positions = check("Get positions", broker.get_positions)
    if positions is not None:
        print(f"         {len(positions)} open position(s): {list(positions.keys()) or 'none'}")

    print("\n=== Done ===\n")


if __name__ == "__main__":
    main()
