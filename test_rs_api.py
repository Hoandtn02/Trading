"""
Test RS đúng cách từ vnstock_data Insights API
"""
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("TEST: RS từ Insights API (ĐÚNG CÁCH)")
print("=" * 60)

try:
    from vnstock_data import Insights
    
    ins = Insights()
    
    # Cách 1: Lấy RS từ Screener (có sẵn trên server)
    print("\n[1] Lấy screener data (có RS field)...")
    df = ins.screener().filter()
    
    if df is not None and len(df) > 0:
        print(f"    Tổng cổ phiếu: {len(df)}")
        
        # Tìm các cột liên quan đến RS
        rs_cols = [c for c in df.columns if 'rs' in c.lower() or 'strength' in c.lower() or 'outperform' in c.lower()]
        print(f"    RS-related columns: {rs_cols}")
        
        if 'rs_3month' in df.columns:
            print("\n[2] Top 10 cổ phiếu có RS cao nhất:")
            top_rs = df.nlargest(10, 'rs_3month')[['ticker', 'rs_3month', 'close_price', 'price_return_3month']]
            print(top_rs.to_string())
        
        if 'outperforms_index_3month' in df.columns:
            print("\n[3] Top 10 cổ phiếu outperform VN-Index nhiều nhất:")
            top_out = df.nlargest(10, 'outperforms_index_3month')[['ticker', 'outperforms_index_3month', 'rs_3month']]
            print(top_out.to_string())
    else:
        print("    Không lấy được dữ liệu screener")
        
except Exception as e:
    print(f"    LỖI: {e}")
    import traceback
    traceback.print_exc()

# Cách 2: Top Gainers
print("\n" + "-" * 40)
print("[4] Top Gainers (từ ranking API)...")
try:
    from vnstock_data import Insights
    ins = Insights()
    
    gainers = ins.ranking().gainer(limit=10)
    if gainers is not None and len(gainers) > 0:
        print(gainers.to_string())
    else:
        print("    Không lấy được top gainers")
except Exception as e:
    print(f"    LỖI: {e}")

print("\n" + "=" * 60)
