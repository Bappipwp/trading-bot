import config
from strategy.base import Signal
from utils.logger import get_logger

log = get_logger(__name__)


class RiskManager:
    """
    Validates and scales signals before they reach the executor.

    Rules (all configurable via config.py):
    - Max position size: no single position > MAX_POSITION_PCT of portfolio equity
      (reduced to HIGH_PROFIT_POSITION_PCT once daily profit exceeds HIGH_PROFIT_THRESHOLD_USD)
    - Daily loss halt: stop trading if down more than MAX_DAILY_LOSS_PCT on the day
    - Daily profit halt: stop trading once up DAILY_PROFIT_TARGET_USD on the day
    - No duplicate positions: skip buy/short signals for symbols already held at max size
    """

    def __init__(self, db=None):
        self.db = db
        self._halted = False
        self._day_open_equity: float | None = None

    def start_of_day(self, equity: float):
        self._day_open_equity = equity
        self._halted = False
        log.info(f"Risk manager reset. Day-open equity: ${equity:,.2f}")

    def check_daily_limits(self, current_equity: float) -> bool:
        if self._day_open_equity is None:
            return True
        pnl = current_equity - self._day_open_equity
        max_loss_usd = self._day_open_equity * config.MAX_DAILY_LOSS_PCT
        if pnl >= config.DAILY_PROFIT_TARGET_USD:
            if not self._halted:
                log.info(
                    f"Daily profit target reached: +${pnl:,.2f}. Trading halted for today."
                )
            self._halted = True
        elif -pnl >= max_loss_usd:
            if not self._halted:
                log.warning(
                    f"Daily loss limit hit: -${-pnl:,.2f} (limit ${max_loss_usd:,.2f}). Trading halted for today."
                )
            self._halted = True
        return not self._halted

    def _position_pct(self, current_equity: float) -> float:
        """Return the active max-position percentage based on daily P&L."""
        if self._day_open_equity is None:
            return config.MAX_POSITION_PCT
        pnl = current_equity - self._day_open_equity
        if pnl >= config.HIGH_PROFIT_THRESHOLD_USD:
            log.info(
                f"High-profit mode (up ${pnl:,.2f}): position size capped at "
                f"{config.HIGH_PROFIT_POSITION_PCT*100:.0f}%"
            )
            return config.HIGH_PROFIT_POSITION_PCT
        return config.MAX_POSITION_PCT

    def validate(
        self,
        signals: list[Signal],
        equity: float,
        positions: dict,
    ) -> list[Signal]:
        if self._halted:
            log.warning("Risk: halted — all signals rejected")
            return []

        if not self.check_daily_limits(equity):
            return []

        approved: list[Signal] = []
        max_position_value = equity * self._position_pct(equity)

        for sig in signals:
            reject_reason = None

            if sig.qty <= 0:
                reject_reason = f"qty={sig.qty}"
                log.warning(f"Risk: rejecting signal with qty={sig.qty} for {sig.symbol}")
            elif sig.side == "buy" and sig.symbol in positions:
                pos = positions[sig.symbol]
                if float(pos.qty) > 0:
                    current_value = float(pos.market_value)
                    if current_value >= max_position_value * 0.9:
                        reject_reason = "long position already near max"
                        log.info(f"Risk: skip {sig.symbol} buy — {reject_reason}")
            elif sig.side == "short" and sig.symbol in positions:
                pos = positions[sig.symbol]
                if float(pos.qty) < 0:
                    current_value = abs(float(pos.market_value))
                    if current_value >= max_position_value * 0.9:
                        reject_reason = "short position already near max"
                        log.info(f"Risk: skip {sig.symbol} short — {reject_reason}")

            if self.db:
                self.db.save_signal(sig, approved=reject_reason is None, reject_reason=reject_reason or "")

            if reject_reason:
                continue

            approved.append(sig)
            log.info(f"Risk: approved {sig.side} {sig.qty} {sig.symbol} (confidence={sig.confidence:.2f})")

        return approved
