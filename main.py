import time
from data_fetcher import get_last_close_price
import os
from data_fetcher import get_market_data, get_balance
from indicator_processor import calculate_indicators, format_for_gemini
from gemini_analyzer import analyze
from signal_evaluator import parse_signal_sl_tp
from trade_executor import place_order, is_order_open, set_leverage
from logger import log_event
from config import TRADE_AMOUNT, LEVERAGE
import requests
from config import BINGX_API_KEY, BINGX_API_SECRET, BINGX_API_URL, SYMBOL
import hmac
from hashlib import sha256

def get_sign(api_secret, payload):
    return hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"), digestmod=sha256).hexdigest()

def parse_param(params_map):
    sorted_keys = sorted(params_map)
    params_str = "&".join(["%s=%s" % (x, params_map[x]) for x in sorted_keys])
    if params_str != "":
        return params_str + "&timestamp=" + str(int(time.time() * 1000))
    else:
        return "timestamp=" + str(int(time.time() * 1000))

def has_open_orders():
    path = '/openApi/swap/v2/trade/openOrders'
    method = "GET"
    params_map = {"symbol": SYMBOL}
    params_str = parse_param(params_map)
    signature = get_sign(BINGX_API_SECRET, params_str)
    url = f"{BINGX_API_URL}{path}?{params_str}&signature={signature}"
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    response = requests.request(method, url, headers=headers)
    if response.status_code == 200:
        data = response.json().get("data", {})
        orders = data.get("orders", [])
        return len(orders) > 0
    return False

QUESTION = ""  # Đã tích hợp vào format_for_gemini
ORDER_ID_FILE = "current_order.txt"

order_id = None
if os.path.exists(ORDER_ID_FILE):
    with open(ORDER_ID_FILE, "r") as f:
        order_id = f.read().strip() or None

while True:
    try:
        if has_open_orders():
            log_event("Đã có lệnh mở, không đặt lệnh mới.")
            time.sleep(60)
            continue
        if not order_id:
            # Kiểm tra thực tế trên sàn: nếu đã có lệnh mở hoặc vị thế mở thì bỏ qua
            if has_open_orders():
                log_event(f"Đã có lệnh đang mở trên sàn (orderId: {order_id}), không mở lệnh mới.")
                time.sleep(120)
                continue
            data = get_market_data()
            if not data:
                log_event("Không lấy được dữ liệu thị trường.")
                time.sleep(120)
                continue
            balance = get_balance()
            if balance is None:
                log_event("Không lấy được số dư tài khoản.")
                time.sleep(120)
                continue
            df = calculate_indicators(data)
            data_text = format_for_gemini(df, balance, TRADE_AMOUNT, LEVERAGE)
            signal_text = analyze(data_text, QUESTION)
            signal, sl, tp = parse_signal_sl_tp(signal_text)
            log_event(f"Gemini trả về: {signal_text} | Tín hiệu: {signal} | SL: {sl} | TP: {tp}")
            if signal in ["buy", "sell"]:
                # Kiểm tra hợp lệ SL trước khi đặt lệnh
                last_price = get_last_close_price()
                if signal == "buy" and sl is not None and sl >= last_price:
                    log_event(f"Lỗi: Stop loss ({sl}) phải nhỏ hơn giá hiện tại ({last_price}) cho lệnh mua.")
                    time.sleep(120)
                    continue
                if signal == "sell" and sl is not None and sl <= last_price:
                    log_event(f"Lỗi: Stop loss ({sl}) phải lớn hơn giá hiện tại ({last_price}) cho lệnh bán.")
                    time.sleep(120)
                    continue
                # Thiết lập đòn bẩy trước khi đặt lệnh
                side_leverage = "LONG" if signal == "buy" else "SHORT"
                lev_result = set_leverage(LEVERAGE, side_leverage)
                log_event(f"Thiết lập đòn bẩy {LEVERAGE}x cho {side_leverage}: {lev_result}")
                result = place_order(signal, sl=sl, tp=tp, trade_amount=TRADE_AMOUNT)
                log_event(f"Đặt lệnh {signal}: {result}")
                if result.get("code") == 0 and result.get("orderId"):
                    order_id = str(result.get("orderId"))
                    with open(ORDER_ID_FILE, "w") as f:
                        f.write(order_id)
            else:
                log_event("Không có tín hiệu giao dịch.")
            time.sleep(120)
        else:
            # Kiểm tra trạng thái lệnh
            if not is_order_open(order_id):
                log_event(f"Lệnh {order_id} đã đóng hoặc không còn hiệu lực.")
                order_id = None
                if os.path.exists(ORDER_ID_FILE):
                    os.remove(ORDER_ID_FILE)
            time.sleep(60)
    except Exception as e:
        log_event(f"Lỗi: {e}")
        time.sleep(60) 