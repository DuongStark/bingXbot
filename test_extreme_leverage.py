from trade_executor import get_account_balance, calculate_position_size, set_leverage, get_trading_info
from data_fetcher import get_current_price
from logger import log_event
import time

def test_extreme_leverage():
    """Test đặc biệt cho extreme leverage x100-x125"""
    
    print("=== 🚨 TESTING EXTREME LEVERAGE x100-x125 🚨 ===")
    print("⚠️  WARNING: Đây là mức đòn bẩy CỰC KỲ NGUY HIỂM!")
    print("💀 Có thể mất sạch tài khoản chỉ trong vài giây!")
    print("=" * 50)
    
    # 1. Lấy thông tin tài khoản
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
    
    # 2. Test extreme leverage cases
    extreme_cases = [
        {"leverage": 100, "amount": 10},   # 10$ với 100x
        {"leverage": 100, "amount": 20},   # 20$ với 100x  
        {"leverage": 125, "amount": 10},   # 10$ với 125x
        {"leverage": 125, "amount": 15},   # 15$ với 125x
    ]
    
    for i, case in enumerate(extreme_cases, 1):
        leverage = case["leverage"]
        amount = case["amount"]
        
        print(f"\n🧪 TEST {i}: ${amount} với {leverage}x EXTREME LEVERAGE")
        print(f"   Position value: ${amount * leverage} (!!)")
        
        try:
            # Calculate position size với extreme leverage
            quantity, safe_amount = calculate_position_size(
                trade_amount_usd=amount,
                current_price=current_price,
                leverage=leverage,
                sl_price=current_price * 0.999,  # SL chỉ 0.1% - rất gần!
                account_balance=balance_info['available_margin']
            )
            
            print(f"   📊 Calculated: {quantity:.6f} BTC, ${safe_amount:.2f} margin")
            print(f"   💀 Position value: ${safe_amount * leverage:.2f}")
            print(f"   🔥 Liquidation risk: EXTREME HIGH")
            
            if quantity <= 0:
                print("   ❌ Position blocked by safety logic")
                continue
                
            if quantity < 0.001:
                print("   ❌ Below minimum BTC amount")
                continue
            
            # Test set leverage
            leverage_result = set_leverage(leverage, "LONG")
            if leverage_result.get('code') == 0:
                print("   ✅ Leverage setting successful")
            else:
                print(f"   ⚠️ Leverage issue: {leverage_result}")
            
            # Calculate liquidation distance
            liquidation_distance = (1 / leverage) * 100  # % distance to liquidation
            liquidation_price = current_price * (1 - liquidation_distance/100)
            
            print(f"   💀 LIQUIDATION PRICE: ${liquidation_price:.1f}")
            print(f"   💀 LIQUIDATION DISTANCE: {liquidation_distance:.3f}%")
            print(f"   ⚡ Tài khoản sẽ ZERO nếu BTC giảm {liquidation_distance:.3f}%")
            
            # Safety warnings
            if liquidation_distance < 1:
                print("   🚨🚨🚨 CẢNH BÁO: Liquidation < 1% - CỰC KỲ NGUY HIỂM!")
            
            print("   " + "="*40)
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
        
        time.sleep(1)
    
    print(f"\n{'='*50}")
    print("🚨 EXTREME LEVERAGE SUMMARY:")
    print("- Chỉ trade với số tiền bạn có thể mất 100%")
    print("- Set SL rất gần (0.1-0.2%) để giảm thiểu tổn thất")
    print("- Theo dõi liên tục, sẵn sàng đóng lệnh bất cứ lúc nào")
    print("- 1 pip sai = mất sạch margin")
    print("💀 YOU HAVE BEEN WARNED!")

if __name__ == "__main__":
    test_extreme_leverage()