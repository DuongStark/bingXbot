import requests
from config import BINGX_API_KEY, BINGX_API_URL, SYMBOL

def get_last_price():
    url = f"{BINGX_API_URL}/openApi/swap/v2/quote/price"
    params = {"symbol": SYMBOL}
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    response = requests.get(url, params=params, headers=headers)
    print("Status code:", response.status_code)
    print("Raw response:", response.text)
    if response.status_code == 200:
        data = response.json().get("data", {})
        last_price = data.get("price")
        print(f"Giá hiện tại của {SYMBOL}: {last_price}")
    else:
        print(f"Lỗi lấy giá hiện tại: {response.status_code} - {response.text}")

if __name__ == "__main__":
    get_last_price() 