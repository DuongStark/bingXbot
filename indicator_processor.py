import pandas as pd

def calculate_indicators(data):
    df = pd.DataFrame(data)
    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)
    # RSI
    df["rsi"] = df["close"].rolling(window=14).apply(lambda x: (x.diff().clip(lower=0).sum() / abs(x.diff()).sum()) * 100 if abs(x.diff()).sum() != 0 else 0)
    # EMA
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    # MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    return df

def format_for_gemini(df, balance, trade_amount, leverage):
    closes = df["close"].tolist()
    rsi = df["rsi"].iloc[-1]
    ema20 = df["ema20"].iloc[-1]
    ema50 = df["ema50"].iloc[-1]
    macd = df["macd"].iloc[-1]
    volume = df["volume"].iloc[-1]
    # Tính ATR(14) và StdDev(14) cho nến 1m
    atr = df["close"].rolling(window=14).apply(lambda x: x.max() - x.min()).iloc[-1]
    stddev = df["close"].rolling(window=14).std().iloc[-1]
    # Lấy giá đóng cửa 10 nến 15m gần nhất
    closes_15m = None
    try:
        from data_fetcher import get_market_data_15m
        data_15m = get_market_data_15m()
        if data_15m and isinstance(data_15m, list) and len(data_15m) > 0:
            closes_15m = []
            for candle in data_15m[-10:]:
                if isinstance(candle, dict):
                    closes_15m.append(float(candle.get("close", 0)))
                elif isinstance(candle, list) and len(candle) >= 5:
                    closes_15m.append(float(candle[4]))
    except Exception as e:
        closes_15m = None
    text = (
        f"Dữ liệu dưới đây là 20 nến 1 phút (1m) gần nhất.\n"
        f"Giá đóng cửa 20 nến 1m gần nhất: {closes}\n"
        f"Giá hiện tại: {closes[-1]} USDT\n"
        f"ATR(14): {atr:.2f}\n"
        f"Độ lệch chuẩn 14 nến: {stddev:.2f}\n"
        + (f"Giá đóng cửa 10 nến 15m gần nhất: {closes_15m}\n" if closes_15m else "") +
        f"RSI: {rsi:.2f}\n"
        f"EMA20: {ema20:.2f}\n"
        f"EMA50: {ema50:.2f}\n"
        f"MACD: {macd:.2f}\n"
        f"Volume: {volume:.2f}\n"
        f"Số dư tài khoản: {(balance*50):.2f} USDT\n"
        f"Số tiền vào lệnh: {trade_amount:.2f} USDT\n"
        f"Đòn bẩy: {leverage}x\n"
        "Dựa trên các chỉ báo này, tôi nên mua, bán hay giữ?\n"
        "Nếu mua/bán, hãy đề xuất mức giá stop loss và take profit hợp lý.\n"
        "Bắt buộc trả lời đúng theo format sau không cần phân tích gì thêm (nếu không có tín hiệu thì chỉ trả về hold):\n"
        "Tín hiệu: [mua/bán/giữ]\n"
        "Stop loss: [giá sl hoặc để trống nếu không có]\n"
        "Take profit: [giá tp hoặc để trống nếu không có]"
    )
    return text 
