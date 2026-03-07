from utils.logger import get_logger

log = get_logger(__name__)


class PortfolioTracker:
    """
    Wraps Alpaca account + positions into a simple view.
    Queries the broker on each update() call so state is always fresh.
    """

    def __init__(self, broker, db=None):
        self.broker = broker
        self.db = db
        self.equity: float = 0.0
        self.cash: float = 0.0
        self.positions: dict = {}

    def update(self):
        account = self.broker.get_account()
        self.equity = float(account.equity)
        self.cash = float(account.cash)
        self.positions = self.broker.get_positions()
        if self.db:
            self.db.save_snapshot(self.equity, self.cash, len(self.positions))
        self._log_summary()

    def _log_summary(self):
        log.info(
            f"Portfolio | equity=${self.equity:,.2f}  cash=${self.cash:,.2f}  "
            f"positions={list(self.positions.keys()) or 'none'}"
        )
        for symbol, pos in self.positions.items():
            pnl = float(pos.unrealized_pl)
            pnl_pct = float(pos.unrealized_plpc) * 100
            log.info(
                f"  {symbol}: {pos.qty} shares @ avg ${float(pos.avg_entry_price):.2f} | "
                f"P&L ${pnl:+.2f} ({pnl_pct:+.2f}%)"
            )
