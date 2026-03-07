from strategy.base import Signal
from utils.logger import get_logger

log = get_logger(__name__)


class Executor:
    """
    Converts approved signals into broker orders.
    Routes to bracket orders when entry_price is set, plain market orders otherwise.
    """

    def __init__(self, broker, db=None):
        self.broker = broker
        self.db = db
        self.pending_orders: dict[str, object] = {}  # order_id → order object

    def execute(self, signals: list[Signal]) -> list[object]:
        orders = []
        for sig in signals:
            try:
                order = self._place(sig)
                self.pending_orders[str(order.id)] = order
                orders.append(order)
            except Exception as e:
                log.error(f"Order failed for {sig.symbol} ({sig.side} {sig.qty}): {e}")
        return orders

    def _place(self, sig: Signal) -> object:
        if sig.stop_loss_pct is not None and sig.entry_price > 0:
            p = sig.entry_price
            if sig.side == "buy":
                stop_price = round(p * (1 - sig.stop_loss_pct), 2)
                tp_price   = round(p * (1 + sig.take_profit_pct), 2) if sig.take_profit_pct else None
            else:  # short
                stop_price = round(p * (1 + sig.stop_loss_pct), 2)
                tp_price   = round(p * (1 - sig.take_profit_pct), 2) if sig.take_profit_pct else None
            order = self.broker.place_bracket_order(
                symbol=sig.symbol,
                qty=sig.qty,
                side=sig.side,
                stop_price=stop_price,
                take_profit_price=tp_price,
            )
            if self.db:
                self.db.save_order(str(order.id), sig.symbol, sig.side, sig.qty,
                                   sig.entry_price, stop_price, tp_price, "bracket")
            return order
        # plain market order — strategy didn't specify stop/TP
        order = self.broker.place_market_order(
            symbol=sig.symbol,
            qty=sig.qty,
            side=sig.side,
        )
        if self.db:
            self.db.save_order(str(order.id), sig.symbol, sig.side, sig.qty,
                               sig.entry_price, None, None, "market")
        return order

    def sync_pending(self):
        """Remove filled/cancelled orders from pending tracking."""
        for order_id in list(self.pending_orders):
            try:
                order = self.broker.trading.get_order_by_id(order_id)
                if order.status in ("filled", "canceled", "expired", "replaced"):
                    log.info(f"Order {order_id} settled: {order.status}")
                    fill_price = float(order.filled_avg_price) if order.filled_avg_price else None
                    if self.db:
                        self.db.update_order_status(order_id, order.status, fill_price)
                    del self.pending_orders[order_id]
            except Exception as e:
                log.warning(f"Could not fetch order {order_id}: {e}")
