import os
from dotenv import load_dotenv

load_dotenv()


# Binance API
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET", "")

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Trading parameters
TRADING_INTERVAL = "5m"  # Candle interval
BOT_LOOP_SECONDS = 300   # How often the bot runs (5 minutes)
LOOKBACK_CANDLES = 100    # Number of candles to fetch for analysis

# Coins to monitor (USDT pairs)
COIN_LIST = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "DOGEUSDT",
    "MATICUSDT",
]

# Risk management
INITIAL_CAPITAL = 12.0          # ~₹1000 in USD
MAX_RISK_PER_TRADE = 0.03       # 3% of capital
MAX_DAILY_LOSS = 0.05           # 5% of capital
MAX_DRAWDOWN = 0.15             # 15% of capital
MIN_FEE_RATIO = 0.01            # Skip if fees > 1% of position

# Binance fee rate (0.1% maker/taker for basic tier)
FEE_RATE = 0.001

# Market regime thresholds
ADX_TREND_THRESHOLD = 25        # ADX > 25 = trending
ADX_SIDEWAYS_THRESHOLD = 20     # ADX < 20 = sideways
BB_WIDTH_VOLATILE_THRESHOLD = 0.05  # BB width threshold for volatility

# Strategy parameters
EMA_FAST = 9
EMA_SLOW = 21
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
TRAILING_STOP_PCT = 0.02        # 2% trailing stop

# Approval rules
LOSS_STREAK_APPROVAL = 3        # Require approval after N consecutive losses

# Paper trading (set to False for real money)
PAPER_TRADING = True

# Database
DB_PATH = "trades.db"
PAPER_DB_PATH = "paper_trades.db"
