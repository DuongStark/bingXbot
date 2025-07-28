import time
import requests
import hmac
from hashlib import sha256
import json
from config import BINGX_API_KEY, BINGX_API_SECRET, BINGX_API_URL, SYMBOL, TRADE_AMOUNT, LEVERAGE
from data_fetcher import get_last_close_price

def get_sign(api_secret, payload):
    return hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"), digestmod=sha256).hexdigest()

def parse_param(params_map):
    sorted_keys = sorted(params_map)
    params_str = "&".join(["%s=%s" % (x, params_map[x]) for x in sorted_keys])
    if params_str != "":
        return params_str + "&timestamp=" + str(int(time.time() * 1000))
    else:
        return "timestamp=" + str(int(time.time() * 1000))

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

def place_order(signal, sl=None, tp=None, leverage=None, trade_amount=None):
    path = '/openApi/swap/v2/trade/order'
    method = "POST"
    side = "BUY" if signal == "buy" else "SELL"
    position_side = "LONG" if signal == "buy" else "SHORT"
    # --- Sửa: Tính số BTC từ trade_amount (USDT) ---
    if trade_amount is None:
        trade_amount = TRADE_AMOUNT
    price = get_last_close_price()
    if not price or price <= 0:
        raise Exception("Không lấy được giá BTC-USDT để tính số lượng BTC.")
    quantity_btc = round(trade_amount / price, 6)  # Làm tròn 6 chữ số thập phân
    params_map = {
        "symbol": SYMBOL,
        "side": side,
        "positionSide": position_side,
        "type": "MARKET",
        "quantity": quantity_btc,
    }
    if sl:
        params_map["stopLoss"] = json.dumps({
            "type": "STOP_MARKET",
            "stopPrice": sl,
            "workingType": "MARK_PRICE"
        })
    if tp:
        params_map["takeProfit"] = json.dumps({
            "type": "TAKE_PROFIT_MARKET",
            "stopPrice": tp,
            "price": tp,
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
    url = f"{BINGX_API_URL}/openApi/swap/v2/trade/order"
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    params = {"symbol": SYMBOL, "orderId": order_id}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json().get("data", {})
        status = data.get("status", "")
        return status in ["NEW", "PARTIALLY_FILLED"]
    return False

def get_open_orders(symbol=SYMBOL):
    """Lấy danh sách các lệnh đang mở (NEW, PARTIALLY_FILLED) cho symbol hiện tại."""
    url = f"{BINGX_API_URL}/openApi/swap/v2/trade/openOrders"
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    params = {"symbol": symbol}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json().get("data", [])
        # Trả về danh sách orderId của các lệnh đang mở
        return [order.get("orderId") for order in data if order.get("status") in ["NEW", "PARTIALLY_FILLED"]]
    return []

def get_open_positions(symbol=SYMBOL):
    """Kiểm tra có vị thế đang mở với symbol hiện tại không."""
    url = f"{BINGX_API_URL}/openApi/swap/v2/user/positions"
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    params = {"symbol": symbol}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json().get("data", [])
        # Nếu có vị thế với khối lượng > 0 thì coi là đang mở
        for pos in data:
            if float(pos.get("positionAmt", 0)) != 0:
                return True
    return False 