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
    
    # Prompt cho HIGH PROFIT AGGRESSIVE TRADING 🚀
    text = (
        f"BTC: {current_price:.1f} | RSI: {rsi:.0f} | Trend: {trend} | ATR: {atr:.1f}\n"
        f"EMA20: {ema20:.1f} | EMA50: {ema50:.1f} | MACD: {macd:.2f}\n"
        f"5min change: {price_change_5m:+.2f}% | Volume: {volume_trend}\n"
        f"Volatility: {volatility:.2f}% | Confidence: {confidence}/100\n"
        f"DEMO ACCOUNT | Available: 1000$ | TARGET: 90-200% PROFIT 🚀\n"
        f"ATR-based SL: ±{sl_distance:.1f} | TP: ±{tp_distance:.1f}\n\n"
        
        f"🚀 AGGRESSIVE HIGH-PROFIT STRATEGY:\n"
        f"- Target 90-200% profit per successful trade\n"
        f"- Use maximum leverage 100-125x for explosive gains\n"
        f"- Wider TP targets: 0.8-2.0% (for massive profits)\n"
        f"- Tight SL: 0.1-0.2% (control risk with extreme leverage)\n"
        f"- Look for strong breakouts and momentum\n\n"
        
        f"💎 LEVERAGE & AMOUNT RULES:\n"
        f"- Very high confidence (>85): Use 80-100$ with 125x leverage\n"
        f"- High confidence (75-85): Use 60-80$ with 100-110x leverage\n"
        f"- Medium confidence (60-75): Use 40-60$ with 80-90x leverage\n"
        f"- Low confidence (40-60): Use 20-40$ with 50-70x leverage\n"
        f"- Very low confidence (<40): HOLD - wait for better setup\n\n"
        
        f"🎯 HIGH-PROFIT TARGETS:\n"
        f"- Breakout trades: TP = 1.5-2.0% (150-250% profit với 125x)\n"
        f"- Momentum trades: TP = 1.0-1.5% (125-190% profit)\n"
        f"- Reversal trades: TP = 0.8-1.2% (100-150% profit)\n"
        f"- Scalp trades: TP = 0.5-0.8% (60-100% profit)\n"
        f"- Always SL = 0.1-0.2% (max 20-25% loss với 125x)\n\n"
        
        f"⚡ AGGRESSIVE ENTRY SIGNALS:\n"
        f"- Strong volume spike + price breakout = MAX LEVERAGE\n"
        f"- RSI extreme bounce (20→40 or 80→60) = AGGRESSIVE ENTRY\n"
        f"- MACD explosive cross = FULL POSITION\n"
        f"- EMA20 break with momentum = HIGH LEVERAGE\n"
        f"- Multiple confirmations = 125x LEVERAGE\n\n"
        
        f"🔥 RESPONSE FORMAT:\n"
        f"Signal: [buy/sell/hold]\n"
        f"Amount: [20-100 USD]\n"
        f"Leverage: [50-125]\n"
        f"SL: [tight price, 0.1-0.2% away for risk control]\n"
        f"TP: [aggressive target, 0.5-2.0% away for high profit]\n"
        f"Reason: [breakout/momentum/reversal + confidence level + profit target]"
    )
    return text
