import os
from dotenv import load_dotenv

load_dotenv()

# --- Broker ---
API_KEY = os.getenv("APCA_API_KEY_ID", "")
API_SECRET = os.getenv("APCA_API_SECRET_KEY", "")
PAPER = os.getenv("PAPER", "true").lower() == "true"

# --- Trading Universe ---
# High-volatility, liquid US equities suitable for intraday momentum/scalping.
# The strategy will further filter these based on signal conditions.
SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMD",
    "META", "GOOGL", "AMZN", "SPY", "QQQ",
]

# --- Loop Interval ---
BAR_TIMEFRAME = "1Min"   # Alpaca timeframe string
LOOP_INTERVAL_SECONDS = 60

# --- Risk Parameters ---
MAX_POSITION_PCT        = 0.05   # max 5% of portfolio per position (normal mode)
MAX_DAILY_LOSS_PCT      = 0.10   # halt trading if down 10% on the day
DAILY_PROFIT_TARGET_USD = 200.0  # halt trading once up $200 on the day

# --- High-profit risk reduction ---
# Once cumulative daily profit exceeds this threshold, switch to a smaller
# position size to protect gains.
HIGH_PROFIT_THRESHOLD_USD = 1500.0  # e.g. up $1,500 on the day
HIGH_PROFIT_POSITION_PCT  = 0.02    # reduce to 2% per position when in profit-protect mode

# --- Intraday ---
EOD_CLOSE_MINUTES_BEFORE = 5    # close all positions N minutes before market close
