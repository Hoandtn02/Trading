"""
Debug RS Label - Kiểm tra xem tại sao RS luôn NEUTRAL
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
print("DEBUG: RS Label Issue")
print("=" * 60)

from vnstock_data import Quote, Insights

# Test với 1 mã cụ thể
test_symbol = 'FPT'
lookback = 5

# === Test 1: Quote API trực tiếp ===
print(f"\n[1] Test Quote API cho {test_symbol}:")
try:
    q = Quote(symbol=test_symbol)
    stock_df = q.history(symbol=test_symbol, length='30D', interval='1D')
    print(f"    Stock rows: {len(stock_df) if stock_df is not None else 0}")
    
    if stock_df is not None and len(stock_df) >= lookback:
        stock_price = stock_df['close'].iloc[-1]
        stock_past = stock_df['close'].iloc[-lookback]
        stock_return = ((stock_price - stock_past) / stock_past) * 100
        print(f"    Price: {stock_price} -> Past: {stock_past}")
        print(f"    Stock {lookback}d return: {stock_return:.2f}%")
    else:
        print(f"    NOT ENOUGH DATA: {len(stock_df) if stock_df is not None else 0} rows")
except Exception as e:
    print(f"    ERROR: {e}")

# === Test 2: VNIndex ===
print(f"\n[2] Test VNIndex:")
try:
    q_vn = Quote(symbol='VNINDEX')
    vn_df = q_vn.history(symbol='VNINDEX', length='30D', interval='1D')
    print(f"    VNIndex rows: {len(vn_df) if vn_df is not None else 0}")
    
    if vn_df is not None and len(vn_df) >= lookback:
        vn_price = vn_df['close'].iloc[-1]
        vn_past = vn_df['close'].iloc[-lookback]
        vn_return = ((vn_price - vn_past) / vn_past) * 100
        print(f"    Price: {vn_price} -> Past: {vn_past}")
        print(f"    VNIndex {lookback}d return: {vn_return:.2f}%")
        
        # Calculate RS
        rs = stock_return - vn_return
        print(f"\n    *** RS = {rs:.2f}% ***")
        
        if rs >= 5:
            label = "LEADER"
        elif rs >= 2:
            label = "OUTPERFORM"
        elif rs >= -2:
            label = "NEUTRAL"
        elif rs >= -5:
            label = "UNDERPERFORM"
        else:
            label = "LAGGARD"
        
        print(f"    Label: {label}")
except Exception as e:
    print(f"    ERROR: {e}")

# === Test 3: Insights Screener ===
print(f"\n[3] Test Insights Screener:")
try:
    ins = Insights()
    screener_df = ins.screener().filter(2000)
    print(f"    Screener rows: {len(screener_df)}")
    
    if test_symbol in screener_df['symbol'].values:
        row = screener_df[screener_df['symbol'] == test_symbol]
        rs_3m = row['rs_3m'].iloc[0]
        out_idx = row['outperforms_index_3m'].iloc[0]
        print(f"    {test_symbol} - rs_3m: {rs_3m}, outperforms_index_3m: {out_idx}")
    else:
        print(f"    {test_symbol} NOT in screener!")
        print(f"    Sample symbols: {screener_df['symbol'].head(10).tolist()}")
except Exception as e:
    print(f"    ERROR: {e}")

# === Test 4: get_industry_performance function ===
print(f"\n[4] Test get_industry_performance():")
from dashboard.sync_service import get_industry_performance
try:
    rs_value = get_industry_performance(test_symbol, None)
    print(f"    Result: {rs_value}")
except Exception as e:
    print(f"    ERROR: {e}")

print("\n" + "=" * 60)
