from datetime import datetime, timedelta, timezone
import pandas as pd

from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import DataFeed as AlpacaFeed

import config
from utils.logger import get_logger

log = get_logger(__name__)

# Map config string → Alpaca TimeFrame object
_TIMEFRAME_MAP = {
    "1Min": TimeFrame(1, TimeFrameUnit.Minute),
    "5Min": TimeFrame(5, TimeFrameUnit.Minute),
    "15Min": TimeFrame(15, TimeFrameUnit.Minute),
    "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
    "1Day": TimeFrame(1, TimeFrameUnit.Day),
}


class DataFeed:
    def __init__(self, data_client):
        self.client = data_client

    def get_bars(
        self,
        symbols: list[str],
        timeframe: str = config.BAR_TIMEFRAME,
        lookback_bars: int = 100,
    ) -> dict[str, pd.DataFrame]:
        tf = _TIMEFRAME_MAP.get(timeframe)
        if tf is None:
            raise ValueError(f"Unknown timeframe: {timeframe}. Valid: {list(_TIMEFRAME_MAP)}")

        end = datetime.now(timezone.utc)
        # Estimate how far back we need based on timeframe, with 3x buffer for
        # weekends/holidays/after-hours gaps so we always get enough bars.
        minutes_per_bar = {
            "1Min": 1, "5Min": 5, "15Min": 15, "1Hour": 60, "1Day": 1440,
        }.get(timeframe, 1)
        lookback_minutes = lookback_bars * minutes_per_bar * 3
        start = end - timedelta(minutes=lookback_minutes)

        req = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=tf,
            start=start,
            end=end,
            feed=AlpacaFeed.IEX,  # free tier; upgrade to AlpacaFeed.SIP with paid subscription
        )

        raw = self.client.get_stock_bars(req)
        result: dict[str, pd.DataFrame] = {}

        # BarSet.df has a (symbol, timestamp) multi-index
        full_df = raw.df
        for symbol in symbols:
            try:
                df = full_df.loc[symbol][["open", "high", "low", "close", "volume"]].tail(lookback_bars)
                result[symbol] = df
                log.info(f"Fetched {len(df)} bars for {symbol}")
            except KeyError:
                log.warning(f"No bar data returned for {symbol}")

        return result

    def get_latest_bars(self, symbols: list[str], n: int = 20) -> dict[str, pd.DataFrame]:
        return self.get_bars(symbols, lookback_bars=n)
