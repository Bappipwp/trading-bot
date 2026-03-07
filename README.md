# Trading Bot

A modular, strategy-agnostic intraday trading bot for US equities built on the [Alpaca](https://alpaca.markets) API.

The skeleton handles data fetching, risk management, bracket order execution, portfolio tracking, SQLite persistence, and a live dashboard. Plug in any strategy by subclassing `BaseStrategy`.

## Features

- **Paper trading by default** — flip one env var to go live
- **Modular strategy plugin** — swap strategies without touching any other code
- **Bracket orders** — stop loss and take profit attached to every trade (when strategy provides them)
- **Short selling** — signals support long, sell, and short sides
- **EOD close** — all positions flattened automatically before market close
- **Risk manager** — per-position size cap, daily loss halt (% of equity), daily profit target, high-profit protection mode
- **SQLite persistence** — orders, signals, and portfolio snapshots saved to `trading.db`
- **Live dashboard** — Streamlit UI with equity curve, orders table, and signals table (auto-refreshes every 60s)
- **36 unit tests** — zero API calls needed to run them

## Stack

- Python 3.11+
- [alpaca-py](https://github.com/alpacahq/alpaca-py) — broker API
- pandas — bar data
- Streamlit + Plotly — dashboard
- SQLite (stdlib) — persistence
- pytest — testing

## Project Structure

```
├── main.py                 # Entry point — event loop
├── config.py               # Symbols, risk params, paper/live toggle
├── broker/alpaca_client.py # Order placement, account management
├── data/feed.py            # OHLCV bar fetching (IEX feed)
├── strategy/base.py        # BaseStrategy ABC + DummyStrategy placeholder
├── my_strategies/          # Drop your strategies here
├── risk/manager.py         # Position sizing, daily P&L limits
├── execution/executor.py   # Signal → bracket/market order
├── portfolio/tracker.py    # Equity and P&L tracking
├── db/database.py          # SQLite persistence layer
├── dashboard.py            # Streamlit live dashboard
├── utils/logger.py         # File + console logging
└── tests/                  # Unit tests (no API key required)
```

## Setup

**1. Clone the repo**
```sh
git clone https://github.com/Bappipwp/trading-bot.git
cd trading-bot
```

**2. Create a virtual environment**
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Configure API keys**

Create an account at [alpaca.markets](https://alpaca.markets) and get paper trading keys.

```sh
cp .env.example .env
# edit .env and fill in your keys
```

**4. Run tests**
```sh
pytest tests/ -v
```

**5. Smoke test (verifies API connection, no orders placed)**
```sh
python smoke_test.py
```

**6. Run the bot**
```sh
# Continuous loop (market hours only)
python main.py

# Single iteration, bypasses market hours check
python main.py --force

# Run in background
nohup python main.py > nohup.out 2>&1 &
```

**7. Open the dashboard**
```sh
streamlit run dashboard.py
# opens http://localhost:8501
```

## Implementing a Strategy

Create a file in `my_strategies/` and subclass `BaseStrategy`:

```python
from strategy.base import BaseStrategy, Signal

class MyStrategy(BaseStrategy):
    def generate_signals(self, bars: dict) -> list[Signal]:
        signals = []
        for symbol, df in bars.items():
            signals.append(Signal(
                symbol=symbol,
                side="buy",
                qty=1,
                entry_price=float(df["close"].iloc[-1]),
                stop_loss_pct=0.02,   # triggers a bracket order
                take_profit_pct=0.04,
            ))
        return signals
```

Then swap it in `main.py`:
```python
from my_strategies.my_strategy import MyStrategy
strategy = MyStrategy()
```

If `stop_loss_pct` is set on a signal, the executor places a bracket order. Otherwise it places a plain market order.

## Configuration

| Setting | Default | Description |
|---|---|---|
| `SYMBOLS` | 10 tickers | Tickers to scan |
| `BAR_TIMEFRAME` | `1Min` | `1Min`, `5Min`, `15Min`, `1Hour`, `1Day` |
| `LOOP_INTERVAL_SECONDS` | `60` | How often the loop runs |
| `MAX_POSITION_PCT` | `0.05` | Max portfolio % per position (normal mode) |
| `MAX_DAILY_LOSS_PCT` | `0.10` | Halt if down 10% on the day |
| `DAILY_PROFIT_TARGET_USD` | `200.0` | Halt once up $200 on the day |
| `HIGH_PROFIT_THRESHOLD_USD` | `1500.0` | Switch to conservative sizing above this daily P&L |
| `HIGH_PROFIT_POSITION_PCT` | `0.02` | Position size cap in high-profit protection mode |
| `EOD_CLOSE_MINUTES_BEFORE` | `5` | Minutes before close to flatten all positions |

Set `PAPER=false` in `.env` to switch to live trading.

## License

MIT
