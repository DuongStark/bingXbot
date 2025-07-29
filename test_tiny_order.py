from trade_executor import get_account_balance, calculate_position_size, place_order, set_leverage, get_trading_info
from data_fetcher import get_current_price
from logger import log_event
import time

def test_tiny_real_order():
    """Test với lệnh thực tế nhỏ để verify không còn lỗi margin"""
    
    print("=== TESTING TINY REAL ORDER ===")
    
    # 1. Lấy trading info từ BingX
    trading_info = get_trading_info()
    if trading_info:
        print(f"📋 Min Quantity: {trading_info['min_qty']}")
        print(f"📋 Min Notional: ${trading_info['min_notional']}")
    
    # 2. Lấy thông tin tài khoản
    balance_info = get_account_balance()
    if not balance_info:
        print("❌ Cannot get balance!")
        return
    
    current_price = get_current_price()
    if not current_price:
        print("❌ Cannot get BTC price!")
        return
    
    print(f"💰 Available Margin: ${balance_info['available_margin']:.2f}")
    print(f"💰 Current BTC Price: ${current_price:.1f}")
    
    # 3. Test với amount cực nhỏ
    test_amount = 50  # Chỉ $50
    test_leverage = 5
    
    print(f"\n🧪 TESTING TINY ORDER: ${test_amount} với {test_leverage}x")
    
    try:
        # Calculate position size
        quantity, safe_amount = calculate_position_size(
            trade_amount_usd=test_amount,
            current_price=current_price,
            leverage=test_leverage,
            sl_price=None,  # No SL for simple test
            account_balance=balance_info['available_margin']
        )
        
        print(f"📊 Calculated: {quantity:.6f} BTC, ${safe_amount:.2f} margin")
        
        if quantity <= 0:
            print("❌ Position size = 0, ultra conservative blocking")
            return
            
        if quantity < 0.001:
            print("❌ Below minimum BTC amount")
            return
        
        # Set leverage
        leverage_result = set_leverage(test_leverage, "LONG")
        if leverage_result.get('code') == 0:
            print("✅ Leverage set successfully")
        else:
            print(f"⚠️ Leverage warning: {leverage_result}")
        
        # Đây là nơi có thể test thực tế (uncomment để test)
        print("\n🚀 READY TO PLACE REAL ORDER:")
        print(f"   - Quantity: {quantity:.6f} BTC")
        print(f"   - Margin: ${safe_amount:.2f}")
        print(f"   - Usage: {(safe_amount/balance_info['available_margin'])*100:.1f}%")
        
        # Uncomment dòng dưới để đặt lệnh thực tế (CHỈ KHI BẠN CHẮC CHẮN!)
        # result = place_order("buy", leverage=test_leverage, trade_amount=test_amount, current_price=current_price)
        # print(f"📋 Order result: {result}")
        
        print("✅ Test completed - No insufficient margin errors expected!")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_tiny_real_order()