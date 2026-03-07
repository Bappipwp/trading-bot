"""Unit tests for RiskManager — no Alpaca connection needed."""
import pytest
from unittest.mock import patch
from tests.conftest import make_position
from strategy.base import Signal


# Patch config values so tests are deterministic regardless of .env
@pytest.fixture(autouse=True)
def patch_config():
    with patch("risk.manager.config") as mock_cfg:
        mock_cfg.MAX_POSITION_PCT = 0.10
        mock_cfg.MAX_DAILY_LOSS_PCT = 0.10          # 10% of day-open equity
        mock_cfg.DAILY_PROFIT_TARGET_USD = 200.0
        mock_cfg.HIGH_PROFIT_THRESHOLD_USD = 1500.0
        mock_cfg.HIGH_PROFIT_POSITION_PCT = 0.02
        yield mock_cfg


def make_signal(symbol="AAPL", side="buy", qty=1):
    return Signal(symbol=symbol, side=side, qty=qty)


# ── RiskManager import after patch ──────────────────────────────────────────

def get_rm():
    from risk.manager import RiskManager
    return RiskManager()


# ── check_daily_limits ──────────────────────────────────────────────────────
# Day-open equity = 10,000; 10% loss limit = $1,000

class TestDailyLoss:
    def test_no_baseline_always_ok(self):
        rm = get_rm()
        assert rm.check_daily_limits(9_000) is True

    def test_within_limit_ok(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        # $500 loss, limit is $1,000
        assert rm.check_daily_limits(9_500) is True

    def test_exactly_at_limit_halts(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        # exactly 10% loss = $1,000
        assert rm.check_daily_limits(9_000) is False

    def test_beyond_limit_halts(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        assert rm.check_daily_limits(8_000) is False

    def test_profit_target_halts(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        # up $200 — profit target hit
        assert rm.check_daily_limits(10_200) is False

    def test_below_profit_target_ok(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        # up $100 — still trading
        assert rm.check_daily_limits(10_100) is True

    def test_halted_flag_persists(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        rm.check_daily_limits(8_000)  # trigger halt (20% loss)
        assert rm._halted is True
        # still halted even if equity recovered (no intraday reset)
        assert rm.check_daily_limits(10_050) is False

    def test_start_of_day_resets_halt(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        rm.check_daily_limits(8_000)
        rm.start_of_day(10_000)  # new day
        assert rm._halted is False
        assert rm.check_daily_limits(9_500) is True


# ── validate ────────────────────────────────────────────────────────────────

class TestValidate:
    def test_valid_signal_approved(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        signals = [make_signal("AAPL", "buy", 1)]
        approved = rm.validate(signals, 10_000, {})
        assert len(approved) == 1
        assert approved[0].symbol == "AAPL"

    def test_zero_qty_rejected(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        signals = [make_signal("AAPL", "buy", 0)]
        approved = rm.validate(signals, 10_000, {})
        assert approved == []

    def test_negative_qty_rejected(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        signals = [make_signal("AAPL", "buy", -5)]
        approved = rm.validate(signals, 10_000, {})
        assert approved == []

    def test_halted_rejects_all(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        rm._halted = True
        signals = [make_signal("AAPL", "buy", 1), make_signal("MSFT", "buy", 1)]
        assert rm.validate(signals, 10_000, {}) == []

    def test_position_at_max_skipped(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        # max position = 10% of 10_000 = 1_000; position value = 950 ≥ 900 (90%)
        pos = make_position("AAPL", 950)
        signals = [make_signal("AAPL", "buy", 1)]
        approved = rm.validate(signals, 10_000, {"AAPL": pos})
        assert approved == []

    def test_position_below_max_approved(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        # position value = 500, max = 1_000, below 90% threshold (900)
        pos = make_position("AAPL", 500)
        signals = [make_signal("AAPL", "buy", 1)]
        approved = rm.validate(signals, 10_000, {"AAPL": pos})
        assert len(approved) == 1

    def test_sell_signal_always_approved(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        # Even if we hold a large position, sells should pass through
        pos = make_position("AAPL", 9_999)
        signals = [make_signal("AAPL", "sell", 5)]
        approved = rm.validate(signals, 10_000, {"AAPL": pos})
        assert len(approved) == 1

    def test_daily_loss_blocks_validate(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        signals = [make_signal("AAPL", "buy", 1)]
        # down $1,500 — beyond the $1,000 limit (10% of 10,000)
        approved = rm.validate(signals, 8_500, {})
        assert approved == []

    def test_profit_target_blocks_validate(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        signals = [make_signal("AAPL", "buy", 1)]
        # up $200 — profit target hit
        approved = rm.validate(signals, 10_200, {})
        assert approved == []

    def test_multiple_signals_mixed(self):
        rm = get_rm()
        rm.start_of_day(10_000)
        signals = [
            make_signal("AAPL", "buy", 1),
            make_signal("MSFT", "buy", 0),   # rejected: qty=0
            make_signal("NVDA", "buy", 2),
        ]
        approved = rm.validate(signals, 10_000, {})
        assert len(approved) == 2
        symbols = [s.symbol for s in approved]
        assert "AAPL" in symbols
        assert "NVDA" in symbols
