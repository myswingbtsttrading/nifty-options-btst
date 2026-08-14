import os


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Signal generation time.
SIGNAL_HOUR = 15
SIGNAL_MINUTE = 0

# NIFTY option parameters.
STRIKE_INTERVAL = 50

# We will start with ATM selection.
STRIKE_OFFSET = 0

# Signal quality threshold.
MIN_CONFIDENCE = 65.0