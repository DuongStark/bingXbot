import pandas as pd

def calculate_indicators(data):
    df = pd.DataFrame(data)
    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)
    
    # RSI (sửa lại công thức chính xác)
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14, min_periods=1).mean()
    avg_loss = loss.rolling(window=14, min_periods=1).mean()
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))
    
    # EMA
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    
    # MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_histogram"] = df["macd"] - df["macd_signal"]
    
    return df

def calculate_dynamic_levels(current_price, atr, volatility_factor=1.5):
    """Tính toán TP/SL động dựa trên ATR và volatility"""
    # SL: 1.5-2x ATR
    sl_distance = atr * volatility_factor
    # TP: 2-3x ATR (risk:reward = 1:2)
    tp_distance = atr * (volatility_factor * 2)
    
    return sl_distance, tp_distance

def calculate_market_confidence(df):
    """Tính độ tin cậy của tín hiệu thị trường (0-100)"""
    current_price = df["close"].iloc[-1]
    rsi = df["rsi"].iloc[-1]
    ema20 = df["ema20"].iloc[-1]
    ema50 = df["ema50"].iloc[-1]
    macd = df["macd"].iloc[-1]
    macd_signal = df["macd_signal"].iloc[-1]
    
    confidence = 50  # Base confidence
    
    # RSI confirmation
    if 30 < rsi < 70:
        confidence += 10  # Neutral RSI is good
    elif rsi > 80 or rsi < 20:
        confidence -= 15  # Extreme RSI is risky
    
    # Trend confirmation
    if current_price > ema20 > ema50:
        confidence += 15  # Strong uptrend
    elif current_price < ema20 < ema50:
        confidence += 15  # Strong downtrend
    else:
        confidence -= 10  # Sideways/unclear trend
    
    # MACD confirmation
    if abs(macd - macd_signal) > 50:
        confidence += 10  # Strong MACD signal
    
    # Volume confirmation
    recent_volume = df["volume"].iloc[-3:].mean()
    avg_volume = df["volume"].mean()
    if recent_volume > avg_volume * 1.2:
        confidence += 5  # High volume confirms signal
    
    return max(0, min(100, confidence))

def format_for_gemini(df, balance, trade_amount, leverage):
    current_price = df["close"].iloc[-1]
    rsi = df["rsi"].iloc[-1]
    ema20 = df["ema20"].iloc[-1]
    ema50 = df["ema50"].iloc[-1]
    macd = df["macd"].iloc[-1]
    macd_signal = df["macd_signal"].iloc[-1]
    
    # Tính ATR và volatility
    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift())
    low_close = abs(df["low"] - df["close"].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=14).mean().iloc[-1]
    
    # Tính volatility percentage
    volatility = (atr / current_price) * 100
    
    # Tính động lực thị trường
    price_change_5m = ((current_price - df["close"].iloc[-6]) / df["close"].iloc[-6]) * 100
    volume_trend = "tăng" if df["volume"].iloc[-1] > df["volume"].iloc[-5:].mean() else "giảm"
    
    # Tính toán TP/SL động
    sl_distance, tp_distance = calculate_dynamic_levels(current_price, atr)
    
    # Tính market confidence
    confidence = calculate_market_confidence(df)
    
    # Xác định trend ngắn hạn
    trend = "tăng" if current_price > ema20 and ema20 > ema50 else "giảm" if current_price < ema20 and ema20 < ema50 else "sideway"
    
    # Tính available balance
    max_balance = balance * 50  # 50000 USD
    
    # Prompt cho phép Gemini lựa chọn trade amount và leverage
    text = (
        f"BTC: {current_price:.1f} | RSI: {rsi:.0f} | Trend: {trend} | ATR: {atr:.1f}\n"
        f"EMA20: {ema20:.1f} | EMA50: {ema50:.1f} | MACD: {macd:.2f}\n"
        f"5min change: {price_change_5m:+.2f}% | Volume: {volume_trend}\n"
        f"Volatility: {volatility:.2f}% | Confidence: {confidence}/100\n"
        f"Account: 50,000$ | Max risk per trade: 1,000$ (2%)\n"
        f"Suggested SL distance: ±{sl_distance:.1f} | TP distance: ±{tp_distance:.1f}\n\n"
        f"RISK MANAGEMENT RULES:\n"
        f"- Max loss per trade: 1,000$ (2% of account)\n"
        f"- Position size depends on SL distance\n"
        f"- Example: SL 2% away → max position 50,000$ (1000$/0.02)\n"
        f"- Example: SL 1% away → max position 100,000$ (1000$/0.01)\n\n"
        f"TRADING RULES:\n"
        f"- Very high confidence (>90): Use 4000-6000$ and leverage 15-20x\n"
        f"- High confidence (80-90): Use 3000-5000$ and leverage 10-15x\n"
        f"- Medium confidence (60-80): Use 2000-3000$ and leverage 8-12x\n"
        f"- Low confidence (40-60): Use 1000-2000$ and leverage 5-8x\n"
        f"- Very low confidence (<40): HOLD\n"
        f"- Low volatility (<1.5%): Can use higher leverage safely\n"
        f"- High volatility (>2.5%): Use lower leverage, wider SL/TP\n"
        f"- Strong trend + volume + MACD confirm = max leverage\n"
        f"- RSI extreme (>75 or <25): reduce leverage by 30%\n"
        f"- Clear breakout + high volume = increase leverage\n"
        f"- Always set SL to protect 2% max risk\n\n"
        f"RESPONSE FORMAT (exact):\n"
        f"Signal: [buy/sell/hold]\n"
        f"Amount: [1000-6000 USD or empty if hold]\n"
        f"Leverage: [5-20 or empty if hold]\n"
        f"SL: [price or empty]\n"
        f"TP: [price or empty]\n"
        f"Reason: [max 15 words]"
    )
    return text
