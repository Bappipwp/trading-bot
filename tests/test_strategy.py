"""Unit tests for strategy base and DummyStrategy."""
import pandas as pd
import pytest
from strategy.base import Signal, DummyStrategy


def empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])


class TestSignal:
    def test_defaults(self):
        s = Signal(symbol="AAPL", side="buy", qty=5)
        assert s.confidence == 1.0
        assert s.notes == ""

    def test_fields(self):
        s = Signal(symbol="MSFT", side="sell", qty=3, confidence=0.7, notes="test")
        assert s.symbol == "MSFT"
        assert s.side == "sell"
        assert s.qty == 3


class TestDummyStrategy:
    def setup_method(self):
        self.strategy = DummyStrategy()

    def test_returns_signal_for_each_symbol(self, sample_bars):
        signals = self.strategy.generate_signals(sample_bars)
        assert len(signals) == 2
        symbols = {s.symbol for s in signals}
        assert symbols == {"AAPL", "MSFT"}

    def test_all_signals_are_buys(self, sample_bars):
        signals = self.strategy.generate_signals(sample_bars)
        assert all(s.side == "buy" for s in signals)

    def test_no_stop_loss_set(self, sample_bars):
        signals = self.strategy.generate_signals(sample_bars)
        assert all(s.stop_loss_pct is None for s in signals)

    def test_qty_is_one(self, sample_bars):
        signals = self.strategy.generate_signals(sample_bars)
        assert all(s.qty == 1 for s in signals)

    def test_empty_bars_skipped(self):
        bars = {"AAPL": empty_df(), "MSFT": empty_df()}
        signals = self.strategy.generate_signals(bars)
        assert signals == []

    def test_mixed_empty_and_valid(self, sample_bars):
        bars = {"AAPL": sample_bars["AAPL"], "MSFT": empty_df()}
        signals = self.strategy.generate_signals(bars)
        assert len(signals) == 1
        assert signals[0].symbol == "AAPL"

    def test_empty_universe(self):
        signals = self.strategy.generate_signals({})
        assert signals == []
