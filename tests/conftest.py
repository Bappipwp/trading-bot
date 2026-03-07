"""Shared fixtures for all tests."""
import pandas as pd
import pytest
from unittest.mock import MagicMock


def make_bars(n: int = 20) -> dict[str, pd.DataFrame]:
    """Generate fake OHLCV bars for testing."""
    import numpy as np
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n, freq="1min")
    close = 150 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame({
        "open": close - 0.1,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": np.random.randint(1000, 5000, n).astype(float),
    }, index=dates)
    return {"AAPL": df, "MSFT": df.copy()}


@pytest.fixture
def sample_bars():
    return make_bars()


def make_position(symbol: str, market_value: float) -> MagicMock:
    """Fake Alpaca position object."""
    pos = MagicMock()
    pos.symbol = symbol
    pos.market_value = str(market_value)
    pos.qty = "10"
    pos.avg_entry_price = str(market_value / 10)
    pos.unrealized_pl = "50.0"
    pos.unrealized_plpc = "0.05"
    return pos
