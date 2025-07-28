import re

def parse_signal_sl_tp(text):
    """
    Parse kết quả trả về từ Gemini theo format:
    Tín hiệu: [mua/bán/giữ]
    Stop loss: [giá sl hoặc để trống nếu không có]
    Take profit: [giá tp hoặc để trống nếu không có]
    """
    text = text.lower()
    # Tín hiệu
    signal = "hold"
    sl = None
    tp = None
    for line in text.splitlines():
        if line.startswith("tín hiệu:"):
            if "mua" in line:
                signal = "buy"
            elif "bán" in line:
                signal = "sell"
            else:
                signal = "hold"
        elif line.startswith("stop loss:"):
            sl_match = re.search(r"(\d+(?:\.\d+)*)", line)
            if sl_match:
                sl = float(sl_match.group(1))
        elif line.startswith("take profit:"):
            tp_match = re.search(r"(\d+(?:\.\d+)*)", line)
            if tp_match:
                tp = float(tp_match.group(1))
    return signal, sl, tp 