"""
Test RS calculation - mỗi mã khởi tạo Quote riêng
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
sys.path.insert(0, r'd:\OneDrive\Desktop\Trading-1')
django.setup()

import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("TEST: RS Calculation - Independent Quotes")
print("=" * 60)

from vnstock_data import Quote

# Test từng mã riêng biệt
def get_stock_data(symbol):
    q = Quote(symbol=symbol)  # Khởi tạo với symbol
    df = q.history(symbol=symbol, length='20D', interval='1D')
    return df

# Lấy VNINDEX
vn = get_stock_data('VNINDEX')
print(f"VNINDEX: {len(vn)} rows")
if len(vn) >= 5:
    vn_ret = ((vn['close'].iloc[-1] - vn['close'].iloc[-5]) / vn['close'].iloc[-5]) * 100
    print(f"VNINDEX 5d return: {vn_ret:.2f}%")

# Test với nhiều mã
print("\n" + "-" * 40)
test_symbols = ['VCB', 'FPT', 'MWG', 'VNM', 'HPG', 'TCB', 'SAB', 'VHM']

for sym in test_symbols:
    df = get_stock_data(sym)
    if df is not None and len(df) >= 5:
        ret = ((df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]) * 100
        rs = ret - vn_ret
        
        if rs >= 5: label = "LEADER"
        elif rs >= 2: label = "OUTPERFORM"
        elif rs >= -2: label = "NEUTRAL"
        elif rs >= -5: label = "UNDERPERFORM"
        else: label = "LAGGARD"
        
        print(f"{sym:>6}: price={df['close'].iloc[-1]:>8.2f}, ret={ret:>+6.2f}%, RS={rs:>+6.2f}% -> {label}")
    else:
        print(f"{sym:>6}: Khong du du lieu ({len(df) if df is not None else 0} rows)")

print("=" * 60)
