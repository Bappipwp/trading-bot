import sqlite3
from datetime import datetime, timezone
from strategy.base import Signal
from utils.logger import get_logger

log = get_logger(__name__)

_NOW = lambda: datetime.now(timezone.utc).isoformat()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id                TEXT PRIMARY KEY,
    symbol            TEXT NOT NULL,
    side              TEXT NOT NULL,
    qty               REAL NOT NULL,
    entry_price       REAL,
    stop_price        REAL,
    take_profit_price REAL,
    order_type        TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending',
    fill_price        REAL,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol           TEXT NOT NULL,
    side             TEXT NOT NULL,
    qty              REAL NOT NULL,
    entry_price      REAL,
    stop_loss_pct    REAL,
    take_profit_pct  REAL,
    approved         INTEGER NOT NULL,
    reject_reason    TEXT,
    timestamp        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    equity          REAL NOT NULL,
    cash            REAL NOT NULL,
    position_count  INTEGER NOT NULL,
    timestamp       TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: str = "trading.db"):
        self.path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        log.info(f"Database ready: {path}")

    def save_order(
        self,
        order_id: str,
        symbol: str,
        side: str,
        qty: float,
        entry_price: float = 0.0,
        stop_price: float | None = None,
        take_profit_price: float | None = None,
        order_type: str = "market",
    ):
        now = _NOW()
        self._conn.execute(
            """INSERT OR IGNORE INTO orders
               (id, symbol, side, qty, entry_price, stop_price,
                take_profit_price, order_type, status, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,'pending',?,?)""",
            (order_id, symbol, side, qty, entry_price, stop_price,
             take_profit_price, order_type, now, now),
        )
        self._conn.commit()

    def update_order_status(self, order_id: str, status: str, fill_price: float | None = None):
        self._conn.execute(
            "UPDATE orders SET status=?, fill_price=?, updated_at=? WHERE id=?",
            (status, fill_price, _NOW(), order_id),
        )
        self._conn.commit()

    def save_signal(self, sig: Signal, approved: bool, reject_reason: str = ""):
        self._conn.execute(
            """INSERT INTO signals
               (symbol, side, qty, entry_price, stop_loss_pct,
                take_profit_pct, approved, reject_reason, timestamp)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (sig.symbol, sig.side, sig.qty, sig.entry_price,
             sig.stop_loss_pct, sig.take_profit_pct,
             1 if approved else 0,
             reject_reason or None,
             _NOW()),
        )
        self._conn.commit()

    def save_snapshot(self, equity: float, cash: float, position_count: int):
        self._conn.execute(
            "INSERT INTO portfolio_snapshots (equity, cash, position_count, timestamp) VALUES (?,?,?,?)",
            (equity, cash, position_count, _NOW()),
        )
        self._conn.commit()

    def close(self):
        self._conn.close()
