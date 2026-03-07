"""Unit tests for Executor — broker is fully mocked."""
import pytest
from unittest.mock import MagicMock, call
from execution.executor import Executor
from strategy.base import Signal


def make_broker(order_id="order-123", status="new"):
    broker = MagicMock()
    order = MagicMock()
    order.id = order_id
    order.status = status
    broker.place_market_order.return_value = order
    broker.trading.get_order_by_id.return_value = order
    return broker, order


class TestExecutorExecute:
    def test_places_order_for_each_signal(self):
        broker, _ = make_broker()
        executor = Executor(broker)
        signals = [
            Signal("AAPL", "buy", 1),
            Signal("MSFT", "sell", 2),
        ]
        orders = executor.execute(signals)
        assert len(orders) == 2
        assert broker.place_market_order.call_count == 2

    def test_order_args_passed_correctly(self):
        broker, _ = make_broker()
        executor = Executor(broker)
        executor.execute([Signal("AAPL", "buy", 3)])
        broker.place_market_order.assert_called_once_with(symbol="AAPL", qty=3, side="buy")

    def test_pending_orders_tracked(self):
        broker, order = make_broker("order-abc")
        executor = Executor(broker)
        executor.execute([Signal("AAPL", "buy", 1)])
        assert "order-abc" in executor.pending_orders

    def test_broker_error_does_not_crash(self):
        broker = MagicMock()
        broker.place_market_order.side_effect = Exception("API error")
        executor = Executor(broker)
        orders = executor.execute([Signal("AAPL", "buy", 1)])
        assert orders == []  # error swallowed, no crash

    def test_empty_signals_returns_empty(self):
        broker, _ = make_broker()
        executor = Executor(broker)
        assert executor.execute([]) == []


class TestExecutorSyncPending:
    def test_filled_order_removed(self):
        broker, order = make_broker("order-1", status="filled")
        executor = Executor(broker)
        executor.pending_orders["order-1"] = order
        executor.sync_pending()
        assert "order-1" not in executor.pending_orders

    def test_new_order_stays_pending(self):
        broker, order = make_broker("order-2", status="new")
        executor = Executor(broker)
        executor.pending_orders["order-2"] = order
        executor.sync_pending()
        assert "order-2" in executor.pending_orders

    def test_cancelled_order_removed(self):
        broker, order = make_broker("order-3", status="canceled")
        executor = Executor(broker)
        executor.pending_orders["order-3"] = order
        executor.sync_pending()
        assert "order-3" not in executor.pending_orders

    def test_fetch_error_does_not_crash(self):
        broker = MagicMock()
        broker.trading.get_order_by_id.side_effect = Exception("network error")
        executor = Executor(broker)
        executor.pending_orders["order-x"] = MagicMock()
        executor.sync_pending()  # should not raise
