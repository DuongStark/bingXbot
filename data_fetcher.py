import time
import requests
import hmac
from hashlib import sha256
from config import BINGX_API_KEY, BINGX_API_SECRET, BINGX_API_URL, SYMBOL

def get_sign(api_secret, payload):
    return hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"), digestmod=sha256).hexdigest()

def parse_param(params_map):
    sorted_keys = sorted(params_map)
    params_str = "&".join(["%s=%s" % (x, params_map[x]) for x in sorted_keys])
    if params_str != "":
        return params_str + "&timestamp=" + str(int(time.time() * 1000))
    else:
        return "timestamp=" + str(int(time.time() * 1000))

def get_market_data():
    path = '/openApi/swap/v3/quote/klines'
    method = "GET"
    params_map = {
        "symbol": SYMBOL,  # Đảm bảo SYMBOL là 'BTC-USDT'
        "interval": "1m",
        "limit": "20"
    }
    params_str = parse_param(params_map)
    signature = get_sign(BINGX_API_SECRET, params_str)
    url = f"{BINGX_API_URL}{path}?{params_str}&signature={signature}"
    headers = {
        'X-BX-APIKEY': BINGX_API_KEY,
    }
    response = requests.request(method, url, headers=headers)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        from logger import log_event
        log_event(f"Lỗi lấy dữ liệu thị trường: {response.status_code} - {response.text}")
        return []

def get_market_data_15m():
    path = '/openApi/swap/v3/quote/klines'
    method = "GET"
    params_map = {
        "symbol": SYMBOL,
        "interval": "15m",
        "limit": "10"
    }
    params_str = parse_param(params_map)
    signature = get_sign(BINGX_API_SECRET, params_str)
    url = f"{BINGX_API_URL}{path}?{params_str}&signature={signature}"
    headers = {
        'X-BX-APIKEY': BINGX_API_KEY,
    }
    response = requests.request(method, url, headers=headers)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        from logger import log_event
        log_event(f"Lỗi lấy dữ liệu 15m: {response.status_code} - {response.text}")
        return []

def get_balance():
    url = f"{BINGX_API_URL}/openApi/swap/v2/user/balance"
    # Tạo params và ký giống test_balance
    params_map = {}
    params_str = parse_param(params_map)
    signature = get_sign(BINGX_API_SECRET, params_str)
    full_url = f"{url}?{params_str}&signature={signature}"
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    response = requests.get(full_url, headers=headers)
    if response.status_code == 200:
        data = response.json().get("data", {})
        balance_info = data.get("balance", {})
        # Lấy availableMargin (số dư khả dụng)
        return float(balance_info.get("availableMargin", 0))
    return 0

def get_last_close_price():
    """Lấy giá đóng cửa gần nhất của BTC-USDT (dạng float)."""
    data = get_market_data()
    if not data:
        return None
    # Dữ liệu trả về là list các nến, mỗi nến là dict hoặc list
    # Thường: [timestamp, open, high, low, close, ...]
    last_candle = data[-1] if len(data) > 0 else None
    if not last_candle:
        return None
    # Nếu là dict
    if isinstance(last_candle, dict):
        return float(last_candle.get("close", 0))
    # Nếu là list, close thường ở vị trí thứ 4
    if isinstance(last_candle, list) and len(last_candle) >= 5:
        return float(last_candle[4])
    return None

def get_current_price():
    """Lấy giá real-time từ BingX ticker"""
    url = f"{BINGX_API_URL}/openApi/swap/v2/quote/price"
    params = {"symbol": SYMBOL}
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    
    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json().get("data", {})
            price = data.get("price")
            if price:
                return float(price)
    except Exception as e:
        from logger import log_event
        log_event(f"Lỗi lấy giá real-time: {e}")
    
    # Fallback về get_last_close_price nếu lỗi
    return get_last_close_price()