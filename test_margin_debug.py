from trade_executor import get_account_balance, calculate_position_size
from data_fetcher import get_current_price
from logger import log_event

def test_margin_debug():
    """Test function để debug margin issues"""
    
    print("=== DEBUGGING INSUFFICIENT MARGIN ===")
    
    # 1. Kiểm tra số dư tài khoản
    balance_info = get_account_balance()
    if not balance_info:
        print("❌ Không thể lấy thông tin tài khoản!")
        return
    
    # 2. Lấy giá hiện tại
    current_price = get_current_price()
    if not current_price:
        print("❌ Không thể lấy giá BTC!")
        return
    
    print(f"💰 Giá BTC hiện tại: ${current_price:.1f}")
    
    # 3. Test với các trade amount khác nhau
    test_cases = [
        {"amount": 100, "leverage": 5},
        {"amount": 200, "leverage": 5}, 
        {"amount": 500, "leverage": 5},
        {"amount": 1000, "leverage": 8},
        {"amount": 1500, "leverage": 6},
    ]
    
    for case in test_cases:
        amount = case["amount"]
        leverage = case["leverage"]
        
        print(f"\n📊 Test: ${amount} với {leverage}x leverage")
        
        try:
            quantity, safe_amount = calculate_position_size(
                trade_amount_usd=amount,
                current_price=current_price,
                leverage=leverage,
                sl_price=None,
                account_balance=balance_info['available_margin']
            )
            
            margin_needed = safe_amount
            position_value = safe_amount * leverage
            
            print(f"   Quantity BTC: {quantity:.6f}")
            print(f"   Safe amount: ${safe_amount:.2f}")
            print(f"   Position value: ${position_value:.2f}")
            print(f"   Margin needed: ${margin_needed:.2f}")
            print(f"   Available margin: ${balance_info['available_margin']:.2f}")
            
            if margin_needed <= balance_info['available_margin']:
                print(f"   ✅ OK - Đủ margin")
            else:
                print(f"   ❌ FAIL - Thiếu ${margin_needed - balance_info['available_margin']:.2f}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

if __name__ == "__main__":
    test_margin_debug()