"""
Test RS calculation với dữ liệu thật
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
print("TEST: RS Calculation - Manual")
print("=" * 60)

from vnstock_data import Quote

# Lấy VNINDEX làm benchmark
q = Quote(symbol='VCB')
vn = q.history(symbol='VNINDEX', length='20D', interval='1D')
print(f"VNINDEX: {len(vn)} rows")
print(f"VNINDEX close: {vn['close'].tolist()}")

if len(vn) >= 5:
    vn_ret_5d = ((vn['close'].iloc[-1] - vn['close'].iloc[-5]) / vn['close'].iloc[-5]) * 100
    print(f"VNINDEX 5d return: {vn_ret_5d:.2f}%")

# Test với nhiều mã
print("\n" + "-" * 40)
test_symbols = ['VCB', 'FPT', 'MWG', 'VNM', 'HPG', 'TCB', 'SAB', 'VHM']

for sym in test_symbols:
    df = q.history(symbol=sym, length='20D', interval='1D')
    if df is not None and len(df) >= 5:
        ret = ((df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]) * 100
        rs = ret - vn_ret_5d
        
        if rs >= 5: label = "LEADER"
        elif rs >= 2: label = "OUTPERFORM"
        elif rs >= -2: label = "NEUTRAL"
        elif rs >= -5: label = "UNDERPERFORM"
        else: label = "LAGGARD"
        
        print(f"{sym:>6}: price={df['close'].iloc[-1]:>8.2f}, ret={ret:>+6.2f}%, RS={rs:>+6.2f}% -> {label}")
    else:
        print(f"{sym:>6}: Khong du du lieu ({len(df) if df is not None else 0} rows)")

print("=" * 60)
