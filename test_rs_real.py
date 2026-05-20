"""
Test Relative Strength với các MÃ ĐẦU NGÀNH
Chạy: & "$env:USERPROFILE\.venv\Scripts\python.exe" test_rs_real.py
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
print("TEST: Relative Strength - MÃ ĐẦU NGÀNH")
print("=" * 60)

from vnstock_data import Quote

# Các mã đầu ngành để test
test_symbols = ['VCB', 'FPT', 'MWG', 'VNM', 'HPG', 'TCB', 'VPB', 'SSI']

try:
    quote = Quote(source='KBS')
    
    # Lấy VNINDEX
    print("\n[1] Lấy dữ liệu VNINDEX...")
    vn_df = quote.history(symbol='VNINDEX', length='20D', interval='1D')
    print(f"    VNINDEX: {len(vn_df)} rows")
    
    if vn_df is None or len(vn_df) < 20:
        print("    LỖI: Không lấy được VNINDEX")
    else:
        vn_return = ((vn_df['close'].iloc[-1] - vn_df['close'].iloc[-20]) / vn_df['close'].iloc[-20]) * 100
        print(f"    VNINDEX 20-day return: {vn_return:.2f}%")
    
    # Lấy dữ liệu từng mã
    print("\n[2] Lấy dữ liệu từng mã...")
    results = []
    
    for symbol in test_symbols:
        try:
            df = quote.history(symbol=symbol, length='20D', interval='1D')
            if df is not None and len(df) >= 20:
                stock_return = ((df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20]) * 100
                rs_vs_vn = stock_return - vn_return
                
                results.append({
                    'symbol': symbol,
                    'return': stock_return,
                    'rs': rs_vs_vn,
                    'close': df['close'].iloc[-1]
                })
                
                print(f"    {symbol}: return={stock_return:+.2f}%, RS={rs_vs_vn:+.2f}%")
            else:
                print(f"    {symbol}: Không đủ dữ liệu")
        except Exception as e:
            print(f"    {symbol}: LỖI - {e}")
    
    # Summary
    print("\n[3] KẾT QUẢ RS")
    print("-" * 40)
    if results:
        print(f"{'Symbol':<8} {'Price':>10} {'Return%':>10} {'RS%':>10} {'Label':<15}")
        print("-" * 55)
        for r in sorted(results, key=lambda x: x['rs'], reverse=True):
            rs = r['rs']
            if rs >= 5:
                label = "LEADER"
            elif rs >= 2:
                label = "OUTPERFORM"
            elif rs <= -5:
                label = "LAGGARD"
            elif rs <= -2:
                label = "UNDERPERFORM"
            else:
                label = "NEUTRAL"
            
            print(f"{r['symbol']:<8} {r['close']:>10.0f} {r['return']:>+10.2f} {r['rs']:>+10.2f} {label:<15}")
    
except Exception as e:
    print(f"LỖI: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
