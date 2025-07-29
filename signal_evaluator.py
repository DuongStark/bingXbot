import re

def parse_signal_sl_tp(text):
    """
    Parse kết quả trả về từ Gemini theo format mới:
    Signal: [buy/sell/hold]
    Amount: [1000-5000 USD or empty if hold]
    Leverage: [3-10 or empty if hold]
    SL: [price or empty]
    TP: [price or empty]
    Reason: [max 15 words]
    """
    text = text.lower()
    signal = "hold"
    amount = None
    leverage = None
    sl = None
    tp = None
    reason = ""
    
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("signal:"):
            if "buy" in line:
                signal = "buy"
            elif "sell" in line:
                signal = "sell"
            else:
                signal = "hold"
        elif line.startswith("amount:"):
            amount_match = re.search(r"(\d+(?:\.\d+)?)", line)
            if amount_match:
                amount = float(amount_match.group(1))
        elif line.startswith("leverage:"):
            lev_match = re.search(r"(\d+(?:\.\d+)?)", line)
            if lev_match:
                leverage = int(float(lev_match.group(1)))
        elif line.startswith("sl:"):
            sl_match = re.search(r"(\d+(?:\.\d+)?)", line)
            if sl_match:
                sl = float(sl_match.group(1))
        elif line.startswith("tp:"):
            tp_match = re.search(r"(\d+(?:\.\d+)?)", line)
            if tp_match:
                tp = float(tp_match.group(1))
        elif line.startswith("reason:"):
            reason = line.replace("reason:", "").strip()
    
    return signal, amount, leverage, sl, tp, reason