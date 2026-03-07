from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal
import pandas as pd


@dataclass
class Signal:
    symbol: str
    side: Literal["buy", "sell", "short"]  # "short" = open a new short position
    qty: float                             # number of shares
    entry_price: float = 0.0              # last close — executor uses this for stop/TP prices
    stop_loss_pct: float | None = None    # e.g. 0.02 = 2% stop loss; falls back to config default
    take_profit_pct: float | None = None  # e.g. 0.04 = 4% take profit; falls back to config default
    confidence: float = 1.0              # 0.0–1.0, used by risk manager to scale size
    notes: str = ""


class BaseStrategy(ABC):
    """
    All strategies inherit from this class and implement generate_signals().
    The rest of the bot (risk, execution) works with the Signal dataclass —
    the strategy never touches orders directly.
    """

    @abstractmethod
    def generate_signals(self, bars: dict[str, pd.DataFrame]) -> list[Signal]:
        """
        Given the latest OHLCV bars for each symbol, return a list of Signals.

        Args:
            bars: {symbol: DataFrame(open, high, low, close, volume)}

        Returns:
            List of Signal objects (may be empty)
        """
        ...


# ---------------------------------------------------------------------------
# Example dummy strategy — always passes (buy 1 share of each symbol).
# Replace or subclass this with your real strategy later.
# ---------------------------------------------------------------------------

class DummyStrategy(BaseStrategy):
    """
    Buys 1 share of every symbol every loop. No stop loss, no take profit.
    Replace this with a real strategy in my_strategies/.
    """

    def generate_signals(self, bars: dict[str, pd.DataFrame]) -> list[Signal]:
        signals = []
        for symbol, df in bars.items():
            if df.empty:
                continue
            signals.append(Signal(symbol=symbol, side="buy", qty=1))
        return signals
