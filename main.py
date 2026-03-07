"""
Trading Bot — Entry Point

Swap out DummyStrategy for your real strategy when ready.
"""

import argparse
import time
from datetime import datetime, timezone

import config
from broker.alpaca_client import AlpacaClient
from data.feed import DataFeed
from db.database import Database
from execution.executor import Executor
from portfolio.tracker import PortfolioTracker
from risk.manager import RiskManager
from strategy.base import DummyStrategy  # ← swap this for your strategy
from utils.logger import get_logger

log = get_logger("main")


def market_is_open(broker: AlpacaClient) -> bool:
    clock = broker.trading.get_clock()
    return clock.is_open


def eod_close_if_needed(broker: AlpacaClient) -> bool:
    clock = broker.trading.get_clock()
    if not clock.is_open:
        return False
    seconds_to_close = (clock.next_close - datetime.now(timezone.utc)).total_seconds()
    mins_to_close = seconds_to_close / 60
    if mins_to_close <= config.EOD_CLOSE_MINUTES_BEFORE:
        log.warning(f"EOD: {mins_to_close:.1f}min to close — closing all positions")
        broker.close_all_positions()
        return True
    return False


def run(force: bool = False):
    log.info("=== Trading Bot Starting ===")
    if force:
        log.info("--force: skipping market hours check, running one iteration")

    # Wire up components
    broker = AlpacaClient()
    db = Database()
    feed = DataFeed(broker.data)
    strategy = DummyStrategy()
    risk = RiskManager(db=db)
    executor = Executor(broker, db=db)
    portfolio = PortfolioTracker(broker, db=db)

    # Initial portfolio snapshot
    portfolio.update()
    risk.start_of_day(portfolio.equity)

    log.info(f"Symbols: {config.SYMBOLS}")
    log.info(f"Loop interval: {config.LOOP_INTERVAL_SECONDS}s")

    while True:
        now = datetime.now(timezone.utc)

        if not force and not market_is_open(broker):
            log.info(f"Market closed at {now.strftime('%H:%M:%S UTC')} — waiting...")
            time.sleep(60)
            continue

        try:
            # 0. Close all positions near end of day
            if eod_close_if_needed(broker):
                time.sleep(config.LOOP_INTERVAL_SECONDS)
                continue

            # 1. Fetch latest bars
            bars = feed.get_latest_bars(config.SYMBOLS, n=50)

            # 2. Generate signals from strategy
            signals = strategy.generate_signals(bars)
            log.info(f"Strategy generated {len(signals)} signal(s)")

            # 3. Validate signals through risk manager
            approved = risk.validate(signals, portfolio.equity, portfolio.positions)
            log.info(f"Risk approved {len(approved)} signal(s)")

            # 4. Execute approved signals
            if approved:
                executor.execute(approved)

            # 5. Sync pending orders
            executor.sync_pending()

            # 6. Update portfolio state
            portfolio.update()

        except Exception as e:
            log.error(f"Loop error: {e}", exc_info=True)

        if force:
            log.info("--force: single iteration done, exiting")
            break

        time.sleep(config.LOOP_INTERVAL_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="bypass market hours check, run one iteration and exit")
    args = parser.parse_args()
    run(force=args.force)
