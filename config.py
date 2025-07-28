from dotenv import load_dotenv
import os

load_dotenv()

BINGX_API_KEY = os.getenv("BINGX_API_KEY")
BINGX_API_SECRET = os.getenv("BINGX_API_SECRET")
BINGX_API_URL = os.getenv("BINGX_API_URL")
SYMBOL = os.getenv("SYMBOL")
TIMEFRAME = os.getenv("TIMEFRAME")
TRADE_AMOUNT = float(os.getenv("TRADE_AMOUNT"))
LEVERAGE = int(os.getenv("LEVERAGE"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = os.getenv("GEMINI_API_URL")