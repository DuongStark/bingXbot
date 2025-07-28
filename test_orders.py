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

def get_open_orders():
    path = '/openApi/swap/v2/trade/openOrders'
    method = "GET"
    params_map = {
        "symbol": SYMBOL
    }
    params_str = parse_param(params_map)
    signature = get_sign(BINGX_API_SECRET, params_str)
    url = f"{BINGX_API_URL}{path}?{params_str}&signature={signature}"
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    response = requests.request(method, url, headers=headers)
    print("Status code:", response.status_code)
    print("Raw response:", response.text)
    if response.status_code == 200:
        data = response.json().get("data", [])
        if not data:
            print("Không có lệnh nào đang mở.")
        else:
            print("Danh sách lệnh đang mở:")
            for order in data:
                print(order)
    else:
        print(f"Lỗi lấy danh sách lệnh: {response.status_code} - {response.text}")

if __name__ == "__main__":
    get_open_orders() 