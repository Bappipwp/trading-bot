from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest, LimitOrderRequest,
    StopLossRequest, TakeProfitRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream

import config
from utils.logger import get_logger

log = get_logger(__name__)


class AlpacaClient:
    def __init__(self):
        self.trading = TradingClient(
            api_key=config.API_KEY,
            secret_key=config.API_SECRET,
            paper=config.PAPER,
        )
        self.data = StockHistoricalDataClient(
            api_key=config.API_KEY,
            secret_key=config.API_SECRET,
        )
        self.stream = StockDataStream(
            api_key=config.API_KEY,
            secret_key=config.API_SECRET,
        )
        mode = "PAPER" if config.PAPER else "LIVE"
        log.info(f"Alpaca client initialized [{mode}]")

    def get_account(self):
        return self.trading.get_account()

    def get_positions(self) -> dict:
        positions = self.trading.get_all_positions()
        return {p.symbol: p for p in positions}

    def place_market_order(self, symbol: str, qty: float, side: str) -> object:
        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY,
        )
        order = self.trading.submit_order(req)
        log.info(f"Market order submitted: {side} {qty} {symbol} → id={order.id}")
        return order

    def place_bracket_order(
        self,
        symbol: str,
        qty: float,
        side: str,          # "buy" = long, "short" = short
        stop_price: float,
        take_profit_price: float,
    ) -> object:
        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY,
            order_class=OrderClass.BRACKET,
            stop_loss=StopLossRequest(stop_price=stop_price),
            take_profit=TakeProfitRequest(limit_price=take_profit_price),
        )
        order = self.trading.submit_order(req)
        log.info(
            f"Bracket order submitted: {side} {qty} {symbol} "
            f"stop={stop_price} tp={take_profit_price} → id={order.id}"
        )
        return order

    def place_limit_order(self, symbol: str, qty: float, side: str, limit_price: float) -> object:
        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
        req = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY,
            limit_price=limit_price,
        )
        order = self.trading.submit_order(req)
        log.info(f"Limit order submitted: {side} {qty} {symbol} @ {limit_price} → id={order.id}")
        return order

    def cancel_order(self, order_id: str):
        self.trading.cancel_order_by_id(order_id)
        log.info(f"Order cancelled: {order_id}")

    def cancel_all_orders(self):
        self.trading.cancel_orders()
        log.info("All open orders cancelled")

    def close_all_positions(self):
        self.trading.close_all_positions(cancel_orders=True)
        log.info("All positions closed")
