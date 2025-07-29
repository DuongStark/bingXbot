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

def get_account_balance():
    """Lấy thông tin số dư tài khoản thực tế từ BingX"""
    path = '/openApi/swap/v2/user/balance'
    method = "GET"
    params_str = parse_param({})
    signature = get_sign(BINGX_API_SECRET, params_str)
    url = f"{BINGX_API_URL}{path}?{params_str}&signature={signature}"
    headers = {'X-BX-APIKEY': BINGX_API_KEY}
    
    try:
        response = requests.request(method, url, headers=headers)
        if response.status_code == 200:
            data = response.json().get("data", {})
            balance = data.get("balance", {})
            
            # Lấy các thông số quan trọng
            available_margin = float(balance.get("availableMargin", 0))
            used_margin = float(balance.get("usedMargin", 0))
            total_wallet_balance = float(balance.get("totalWalletBalance", 0))
            total_margin_balance = float(balance.get("totalMarginBalance", 0))
            
            log_event(f"=== ACCOUNT BALANCE DEBUG ===")
            log_event(f"Total Wallet Balance: ${total_wallet_balance:.2f}")
            log_event(f"Total Margin Balance: ${total_margin_balance:.2f}")
            log_event(f"Available Margin: ${available_margin:.2f}")
            log_event(f"Used Margin: ${used_margin:.2f}")
            log_event(f"============================")
            
            return {
                'available_margin': available_margin,
                'used_margin': used_margin,
                'total_wallet_balance': total_wallet_balance,
                'total_margin_balance': total_margin_balance
            }
    except Exception as e:
        log_event(f"Lỗi khi lấy account balance: {e}")
        return None

def calculate_position_size(trade_amount_usd, current_price, leverage, sl_price=None, account_balance=50000):
    """Tính toán size position cho demo trading với high leverage"""
    
    # Lấy số dư thực tế từ exchange
    balance_info = get_account_balance()
    if balance_info:
        available_margin = balance_info['available_margin']
        log_event(f"Available margin from exchange: ${available_margin:.2f}")
        
        if available_margin < 20:
            log_event(f"❌ MARGIN TOO LOW: ${available_margin:.2f} - Stopping trades")
            return 0, 0
            
    else:
        available_margin = account_balance
        log_event(f"Using fallback balance: ${available_margin:.2f}")
    
    # DEMO TRADING: Bỏ ultra-conservative, cho phép position sizes lớn hơn
    log_event(f"🔥 DEMO HIGH LEVERAGE TRADING: {leverage}x")
    
    # Sử dụng 80% available margin cho demo (thay vì 5-15%)
    safety_buffer = 50  # Chỉ reserve 50$ cho fees
    usable_margin = max(0, (available_margin - safety_buffer) * 0.8)  # 80% thay vì 5%
    
    log_event(f"Demo margin calculation:")
    log_event(f"  Available: ${available_margin:.2f}")
    log_event(f"  Buffer: ${safety_buffer:.2f}")
    log_event(f"  Usable (80%): ${usable_margin:.2f}")
    
    if usable_margin < 10:
        log_event(f"❌ USABLE MARGIN TOO LOW: ${usable_margin:.2f}")
        return 0, 0
    
    # Tính position size dựa trên trade amount yêu cầu
    if not sl_price:
        # Không có SL: sử dụng trade amount trực tiếp
        safe_trade_amount = min(trade_amount_usd, usable_margin)
        quantity_btc = round(safe_trade_amount / current_price, 6)
        
        log_event(f"Demo position without SL: ${safe_trade_amount:.2f} margin, {quantity_btc:.6f} BTC")
        log_event(f"Position value: ${safe_trade_amount * leverage:.2f} ({leverage}x)")
        return quantity_btc, safe_trade_amount
    
    # Có SL: Tính risk-based position nhưng không quá conservative
    sl_distance_percent = abs(current_price - sl_price) / current_price
    
    # Risk cao hơn cho demo: 200$ hoặc 40% usable margin
    max_risk_usd = min(200, usable_margin * 0.4)
    
    # Position value từ risk
    max_position_value = max_risk_usd / sl_distance_percent
    max_position_by_margin = usable_margin * leverage
    
    # Ưu tiên trade_amount yêu cầu thay vì giới hạn quá chặt
    safe_position_value = min(
        trade_amount_usd * leverage,
        max_position_value, 
        max_position_by_margin
    )
    
    quantity_btc = round(safe_position_value / current_price, 6)
    actual_trade_amount = safe_position_value / leverage
    
    # Final check - đảm bảo không vượt usable margin
    if actual_trade_amount > usable_margin:
        actual_trade_amount = usable_margin
        quantity_btc = round(actual_trade_amount / current_price, 6)
        log_event(f"⚠️ MARGIN SAFETY: Reduced to ${actual_trade_amount:.2f}")
    
    log_event(f"Demo position with SL: ${actual_trade_amount:.2f} margin, {quantity_btc:.6f} BTC")
    log_event(f"Position value: ${safe_position_value:.2f} ({leverage}x)")
    log_event(f"Margin usage: {(actual_trade_amount/available_margin)*100:.1f}% of available")
    
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
    log_event(f"Sử dụng giá {price:.1f} để tính position size")
    
    # Tính position size an toàn với account_balance được truyền vào
    quantity_btc, safe_amount = calculate_position_size(trade_amount, price, leverage, sl, account_balance)
    
    # Kiểm tra nếu quantity = 0 hoặc quá nhỏ
    if quantity_btc <= 0:
        log_event(f"❌ SKIP ORDER: Quantity = {quantity_btc} (insufficient margin)")
        return {"code": 80001, "msg": "Insufficient margin - position size too small", "data": {}}
    
    # Kiểm tra minimum quantity (BingX thường yêu cầu min 0.001 BTC)
    if quantity_btc < 0.001:
        log_event(f"❌ SKIP ORDER: Quantity {quantity_btc:.6f} < minimum 0.001 BTC")
        return {"code": 80001, "msg": "Position size below minimum", "data": {}}
    
    log_event(f"✅ ORDER SIZE OK: {quantity_btc:.6f} BTC, ${safe_amount:.2f} margin")
    
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
            log_event(f"Final SL adjustment for buy: {sl:.1f}")
        elif signal == "sell" and sl <= price:
            sl = price * 1.015  # SL = 101.5% của giá hiện tại
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
            log_event(f"Final TP adjustment for buy: {tp:.1f}")
        elif signal == "sell" and tp >= price:
            tp = price * 0.975  # TP = 97.5% của giá hiện tại
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

def get_trading_info(symbol=SYMBOL):
    """Lấy thông tin trading requirements từ BingX"""
    path = '/openApi/swap/v2/quote/exchangeInfo'
    method = "GET"
    params_str = parse_param({})
    signature = get_sign(BINGX_API_SECRET, params_str)
    url = f"{BINGX_API_URL}{path}?{params_str}&signature={signature}"
    headers = {'X-BX-APIKEY': BINGX_API_KEY}
    
    try:
        response = requests.request(method, url, headers=headers)
        if response.status_code == 200:
            data = response.json().get("data", {})
            symbols = data.get("symbols", [])
            
            for sym in symbols:
                if sym.get("symbol") == symbol:
                    min_qty = float(sym.get("minQty", 0))
                    min_notional = float(sym.get("minNotional", 0))
                    tick_size = float(sym.get("tickSize", 0))
                    step_size = float(sym.get("stepSize", 0))
                    
                    log_event(f"=== TRADING INFO FOR {symbol} ===")
                    log_event(f"Min Quantity: {min_qty}")
                    log_event(f"Min Notional: ${min_notional}")
                    log_event(f"Tick Size: {tick_size}")
                    log_event(f"Step Size: {step_size}")
                    log_event(f"================================")
                    
                    return {
                        'min_qty': min_qty,
                        'min_notional': min_notional,
                        'tick_size': tick_size,
                        'step_size': step_size
                    }
    except Exception as e:
        log_event(f"Lỗi khi lấy trading info: {e}")
        return None