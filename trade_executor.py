import time
import requests
import hmac
from hashlib import sha256
import json
from config import BINGX_API_KEY, BINGX_API_SECRET, BINGX_API_URL, SYMBOL, TRADE_AMOUNT, LEVERAGE
from data_fetcher import get_last_close_price
from logger import log_event

def get_sign(api_secret, payload):
    return hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"), digestmod=sha256).hexdigest()

def parse_param(params_map):
    sorted_keys = sorted(params_map)
    params_str = "&".join(["%s=%s" % (x, params_map[x]) for x in sorted_keys])
    if params_str != "":
        return params_str + "&timestamp=" + str(int(time.time() * 1000))
    else:
        return "timestamp=" + str(int(time.time() * 1000))

def calculate_position_size(trade_amount_usd, current_price, leverage, sl_price=None, account_balance=50000):
    """Tính toán size position với risk management thông minh"""
    
    # Strategy 1: Fixed amount risk để dễ gỡ vốn
    base_risk_usd = 1000  # Fixed 1000$ risk mỗi lệnh
    
    # Strategy 2: Adaptive risk dựa trên drawdown
    drawdown_percent = max(0, (50000 - account_balance) / 50000 * 100)
    
    if drawdown_percent > 40:  # Account < 30k
        # Aggressive recovery mode
        max_risk_usd = 1200  # Tăng risk lên 1200$
        log_event(f"Recovery mode: tăng risk lên {max_risk_usd}$ (drawdown {drawdown_percent:.1f}%)")
    elif drawdown_percent > 20:  # Account < 40k  
        # Moderate recovery
        max_risk_usd = 1100  # Tăng nhẹ lên 1100$
        log_event(f"Recovery mode: tăng risk lên {max_risk_usd}$ (drawdown {drawdown_percent:.1f}%)")
    else:
        # Normal mode
        max_risk_usd = base_risk_usd
    
    # Nếu không có SL, sử dụng trade_amount trực tiếp
    if not sl_price:
        safe_trade_amount = min(trade_amount_usd, max_risk_usd * 10)
        quantity_btc = round(safe_trade_amount / current_price, 6)
        return quantity_btc, safe_trade_amount
    
    # Tính toán dựa trên SL distance
    sl_distance_percent = abs(current_price - sl_price) / current_price
    max_position_value = max_risk_usd / sl_distance_percent
    
    safe_position_value = min(trade_amount_usd * leverage, max_position_value)
    quantity_btc = round(safe_position_value / current_price, 6)
    actual_trade_amount = safe_position_value / leverage
    
    return quantity_btc, actual_trade_amount

def set_leverage(leverage, side, symbol=SYMBOL):
    path = '/openApi/swap/v2/trade/leverage'
    method = "POST"
    params_map = {
        "leverage": str(leverage),
        "side": side,  # "LONG" hoặc "SHORT"
        "symbol": symbol,
    }
    params_str = parse_param(params_map)
    signature = get_sign(BINGX_API_SECRET, params_str)
    url = f"{BINGX_API_URL}{path}?{params_str}&signature={signature}"
    headers = {
        'X-BX-APIKEY': BINGX_API_KEY,
    }
    response = requests.request(method, url, headers=headers)
    return response.json()

def place_order(signal, sl=None, tp=None, leverage=None, trade_amount=None, current_price=None, account_balance=50000):
    path = '/openApi/swap/v2/trade/order'
    method = "POST"
    side = "BUY" if signal == "buy" else "SELL"
    position_side = "LONG" if signal == "buy" else "SHORT"
    
    if trade_amount is None:
        trade_amount = TRADE_AMOUNT
    if leverage is None:
        leverage = LEVERAGE
    
    # Sử dụng current_price được truyền vào, hoặc lấy mới nếu không có
    if current_price is None:
        from data_fetcher import get_current_price
        price = get_current_price()
    else:
        price = current_price
        
    if not price or price <= 0:
        raise Exception("Không lấy được giá BTC-USDT để tính số lượng BTC.")
    
    # Log giá được sử dụng để debug
    from logger import log_event
    log_event(f"Sử dụng giá {price:.1f} để tính position size")
    
    # Tính position size an toàn với account_balance được truyền vào
    quantity_btc, safe_amount = calculate_position_size(trade_amount, price, leverage, sl, account_balance)
    
    params_map = {
        "symbol": SYMBOL,
        "side": side,
        "positionSide": position_side,
        "type": "MARKET",
        "quantity": quantity_btc,
    }
    
    # Validate và adjust SL/TP với giá real-time
    if sl:
        # Double-check SL với giá hiện tại
        if signal == "buy" and sl >= price:
            sl = price * 0.985  # SL = 98.5% của giá hiện tại
            from logger import log_event
            log_event(f"Final SL adjustment for buy: {sl:.1f}")
        elif signal == "sell" and sl <= price:
            sl = price * 1.015  # SL = 101.5% của giá hiện tại
            from logger import log_event
            log_event(f"Final SL adjustment for sell: {sl:.1f}")
            
        # Đảm bảo SL không quá gần giá hiện tại (min 0.5%)
        min_sl_distance = price * 0.005  # 0.5%
        if signal == "buy" and price - sl < min_sl_distance:
            sl = price - min_sl_distance
        elif signal == "sell" and sl - price < min_sl_distance:
            sl = price + min_sl_distance
            
        params_map["stopLoss"] = json.dumps({
            "type": "STOP_MARKET",
            "stopPrice": round(sl, 1),
            "workingType": "MARK_PRICE"
        })
    
    if tp:
        # Double-check TP với giá hiện tại
        if signal == "buy" and tp <= price:
            tp = price * 1.025  # TP = 102.5% của giá hiện tại
            from logger import log_event
            log_event(f"Final TP adjustment for buy: {tp:.1f}")
        elif signal == "sell" and tp >= price:
            tp = price * 0.975  # TP = 97.5% của giá hiện tại
            from logger import log_event
            log_event(f"Final TP adjustment for sell: {tp:.1f}")
            
        # Đảm bảo TP có risk:reward ratio tối thiểu 1:1.2
        if sl:
            sl_distance = abs(price - sl)
            min_tp_distance = sl_distance * 1.2
            if signal == "buy" and tp - price < min_tp_distance:
                tp = price + min_tp_distance
            elif signal == "sell" and price - tp < min_tp_distance:
                tp = price - min_tp_distance
                
        params_map["takeProfit"] = json.dumps({
            "type": "TAKE_PROFIT_MARKET",
            "stopPrice": round(tp, 1),
            "price": round(tp, 1),
            "workingType": "MARK_PRICE"
        })
    
    params_str = parse_param(params_map)
    signature = get_sign(BINGX_API_SECRET, params_str)
    url = f"{BINGX_API_URL}{path}?{params_str}&signature={signature}"
    headers = {
        'X-BX-APIKEY': BINGX_API_KEY,
    }
    response = requests.request(method, url, headers=headers)
    return response.json()

def is_order_open(order_id):
    path = '/openApi/swap/v2/trade/order'
    method = "GET"
    params_map = {"symbol": SYMBOL, "orderId": order_id}
    params_str = parse_param(params_map)
    signature = get_sign(BINGX_API_SECRET, params_str)
    url = f"{BINGX_API_URL}{path}?{params_str}&signature={signature}"
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    response = requests.request(method, url, headers=headers)
    if response.status_code == 200:
        data = response.json().get("data", {})
        status = data.get("status", "")
        return status in ["NEW", "PARTIALLY_FILLED"]
    return False

def get_open_orders(symbol=SYMBOL):
    """Lấy danh sách các lệnh đang mở (NEW, PARTIALLY_FILLED) cho symbol hiện tại."""
    path = '/openApi/swap/v2/trade/openOrders'
    method = "GET"
    params_map = {"symbol": symbol}
    params_str = parse_param(params_map)
    signature = get_sign(BINGX_API_SECRET, params_str)
    url = f"{BINGX_API_URL}{path}?{params_str}&signature={signature}"
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    response = requests.request(method, url, headers=headers)
    if response.status_code == 200:
        data = response.json().get("data", {})
        orders = data.get("orders", [])
        # Trả về danh sách orderId của các lệnh đang mở
        return [order.get("orderId") for order in orders if order.get("status") in ["NEW", "PARTIALLY_FILLED"]]
    return []

def get_open_positions(symbol=SYMBOL):
    """Kiểm tra có vị thế đang mở với symbol hiện tại không."""
    path = '/openApi/swap/v2/user/positions'
    method = "GET"
    params_map = {"symbol": symbol}
    params_str = parse_param(params_map)
    signature = get_sign(BINGX_API_SECRET, params_str)
    url = f"{BINGX_API_URL}{path}?{params_str}&signature={signature}"
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    response = requests.request(method, url, headers=headers)
    if response.status_code == 200:
        data = response.json().get("data", [])
        # Nếu có vị thế với khối lượng > 0 thì coi là đang mở
        for pos in data:
            if float(pos.get("positionAmt", 0)) != 0:
                return True
    return False