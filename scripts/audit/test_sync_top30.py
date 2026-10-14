import os
import sys
import django
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vnstock_web.settings")
django.setup()

from dashboard.models import StockData, StockAnalysis
from dashboard.tv_client import get_ohlcv
from dashboard.sync_service import (
    sync_foreign_flow_from_vci,
    sync_stock_batch,
    save_results_to_db,
    get_market_rsi
)

def main():
    # Đúng 30 mã đầu tiên trong StockData database
    stocks = list(StockData.objects.all()[:30])
    symbols = [s.symbol for s in stocks]
    print(f"Bắt đầu đồng bộ cho {len(symbols)} cổ phiếu đầu tiên: {symbols}")

    t0 = time.time()
    
    # 1. Sync foreign flow từ VCI
    print("\n--- [1] Sync dữ liệu khối ngoại từ VCI price board ---")
    f_res = sync_foreign_flow_from_vci(symbols)
    print(f"Đã cập nhật khối ngoại cho {len(f_res)} mã trong DB.")

    # 2. Prefetch VNINDEX nến
    print("\n--- [2] Prefetch VNINDEX nến để tính RS ---")
    vnindex_df = get_ohlcv('VNINDEX', count=250)
    print(f"Đã tải {len(vnindex_df) if vnindex_df is not None else 0} nến VNINDEX.")

    # 3. Sync technical data & compute indicators
    print("\n--- [3] Sync dữ liệu kỹ thuật & tính toán chỉ báo (BB, MACD, RSI, RS,...) ---")
    market_rsi = get_market_rsi()
    batch_res = sync_stock_batch(symbols, market_rsi=market_rsi, fast_mode=True, vnindex_df=vnindex_df)
    saved_count = save_results_to_db(batch_res.get("results", []))
    print(f"Đã lưu kết quả phân tích kỹ thuật cho {saved_count} mã vào DB.")

    total_time = round(time.time() - t0, 2)
    print(f"\nHoàn tất đồng bộ trong {total_time} giây!")

if __name__ == "__main__":
    main()
