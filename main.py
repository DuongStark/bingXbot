import time
from data_fetcher import get_last_close_price, get_current_price
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

def validate_sl_tp(signal, current_price, sl, tp):
    """Kiểm tra và tự động điều chỉnh SL/TP với giá hiện tại"""
    adjusted_sl = sl
    adjusted_tp = tp
    
    if signal == "buy":
        # Lệnh mua: SL phải < giá hiện tại, TP phải > giá hiện tại
        if sl and sl >= current_price:
            # Auto-adjust SL cho lệnh buy
            adjusted_sl = current_price * 0.98  # SL = 98% của giá hiện tại
            log_event(f"Auto-adjust SL buy: {sl} -> {adjusted_sl:.1f}")
        if tp and tp <= current_price:
            # Auto-adjust TP cho lệnh buy
            adjusted_tp = current_price * 1.04  # TP = 104% của giá hiện tại
            log_event(f"Auto-adjust TP buy: {tp} -> {adjusted_tp:.1f}")
    elif signal == "sell":
        # Lệnh bán: SL phải > giá hiện tại, TP phải < giá hiện tại  
        if sl and sl <= current_price:
            # Auto-adjust SL cho lệnh sell
            adjusted_sl = current_price * 1.02  # SL = 102% của giá hiện tại
            log_event(f"Auto-adjust SL sell: {sl} -> {adjusted_sl:.1f}")
        if tp and tp >= current_price:
            # Auto-adjust TP cho lệnh sell
            adjusted_tp = current_price * 0.96  # TP = 96% của giá hiện tại
            log_event(f"Auto-adjust TP sell: {tp} -> {adjusted_tp:.1f}")
    
    return True, "OK", adjusted_sl, adjusted_tp

QUESTION = ""  # Đã tích hợp vào format_for_gemini
ORDER_ID_FILE = "current_order.txt"

def main_loop():
    order_id = None
    if os.path.exists(ORDER_ID_FILE):
        with open(ORDER_ID_FILE, "r") as f:
            order_id = f.read().strip() or None
            
    while True:
        try:
            # Kiểm tra vị thế mở trước khi đặt lệnh mới
            from trade_executor import get_open_positions
            if get_open_positions():
                log_event("Đã có vị thế mở, không đặt lệnh mới.")
                time.sleep(60)
                continue
                
            if has_open_orders():
                log_event("Đã có lệnh mở, không đặt lệnh mới.")
                time.sleep(60)
                continue
                
            if not order_id:
                # Lấy dữ liệu và phân tích
                data = get_market_data()
                if not data:
                    log_event("Không lấy được dữ liệu thị trường.")
                    time.sleep(60)  # Giảm từ 120s xuống 60s
                    continue
                    
                balance = get_balance()
                if balance is None:
                    log_event("Không lấy được số dư tài khoản.")
                    time.sleep(60)
                    continue
                    
                df = calculate_indicators(data)
                data_text = format_for_gemini(df, balance, TRADE_AMOUNT, LEVERAGE)
                
                # Log prompt ngắn để debug
                log_event("Gửi data tới Gemini...")
                signal_text = analyze(data_text, QUESTION)
                
                if not signal_text:
                    log_event("Gemini không trả về tín hiệu, bỏ qua chu kỳ này.")
                    time.sleep(60)
                    continue
                    
                signal, amount, leverage, sl, tp, reason = parse_signal_sl_tp(signal_text)
                log_event(f"Gemini: {signal} | Amount: {amount} | Leverage: {leverage} | SL: {sl} | TP: {tp} | Lý do: {reason}")
                
                if signal in ["buy", "sell"]:
                    # Lấy giá real-time ngay khi có tín hiệu để tránh biến động
                    current_price = get_current_price()
                    if not current_price:
                        log_event("Không lấy được giá real-time, bỏ qua lệnh.")
                        time.sleep(60)
                        continue
                    
                    log_event(f"Giá real-time khi đặt lệnh: {current_price:.1f}")
                    
                    # Validate SL/TP với giá real-time
                    is_valid, error_msg, adjusted_sl, adjusted_tp = validate_sl_tp(signal, current_price, sl, tp)
                    if not is_valid:
                        log_event(f"SL/TP không hợp lệ: {error_msg}")
                        time.sleep(60)
                        continue
                    
                    # Sử dụng amount và leverage từ Gemini hoặc fallback
                    trade_amount_to_use = amount if amount else TRADE_AMOUNT
                    leverage_to_use = leverage if leverage else LEVERAGE
                    
                    # Validate giới hạn
                    trade_amount_to_use = max(1000, min(6000, trade_amount_to_use))  # 1000-6000 USD
                    leverage_to_use = max(5, min(20, leverage_to_use))  # 5-20x
                        
                    # Thiết lập đòn bẩy trước khi đặt lệnh
                    side_leverage = "LONG" if signal == "buy" else "SHORT"
                    lev_result = set_leverage(leverage_to_use, side_leverage)
                    log_event(f"Thiết lập đòn bẩy {leverage_to_use}x cho {side_leverage}: {lev_result}")
                    
                    # Truyền current_price vào place_order để tránh lấy giá lại
                    result = place_order(signal, sl=adjusted_sl, tp=adjusted_tp, leverage=leverage_to_use, trade_amount=trade_amount_to_use, current_price=current_price, account_balance=balance*50)
                    log_event(f"Đặt lệnh {signal} với {trade_amount_to_use}$ và {leverage_to_use}x: {result}")
                    
                    if result.get("code") == 0 and result.get("orderId"):
                        order_id = str(result.get("orderId"))
                        with open(ORDER_ID_FILE, "w") as f:
                            f.write(order_id)
                    else:
                        log_event(f"Đặt lệnh thất bại: {result}")
                else:
                    log_event(f"Không có tín hiệu giao dịch. Lý do: {reason}")
                    
                time.sleep(60)  # Giảm từ 120s xuống 60s để phản ứng nhanh hơn
            else:
                # Kiểm tra trạng thái lệnh
                if not is_order_open(order_id):
                    log_event(f"Lệnh {order_id} đã đóng hoặc không còn hiệu lực.")
                    order_id = None
                    if os.path.exists(ORDER_ID_FILE):
                        os.remove(ORDER_ID_FILE)
                time.sleep(30)  # Giảm từ 60s xuống 30s để theo dõi lệnh sát hơn
        except Exception as e:
            log_event(f"Lỗi: {e}")
            time.sleep(30)  # Giảm delay khi gặp lỗi

if __name__ == "__main__":
    main_loop()