import os
import sys
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
django.setup()

from dashboard.sync_service import sync_stock_batch, save_results_to_db, get_market_rsi
from dashboard.models import StockData, StockAnalysis

print("=== BẮT ĐẦU CHẠY ĐỒNG BỘ TOÀN BỘ UNIVERSE (116 MÃ) VỚI LOGIC ĐÃ FIX ===")
start_t = time.time()

market_rsi = get_market_rsi()
print(f"VNIndex Market RSI: {market_rsi}")

symbols = list(StockData.objects.values_list('symbol', flat=True))
print(f"Số mã cần phân tích lại: {len(symbols)}")

res = sync_stock_batch(symbols, market_rsi=market_rsi, fast_mode=True)
results = res.get('results', [])
failed = res.get('failed', [])

print(f"Hoàn thành phân tích: {len(results)} mã thành công, {len(failed)} mã lỗi.")
if failed:
    print(f"Các mã lỗi: {failed}")

print("Đang lưu kết quả vào Database...")
saved = save_results_to_db(results)
print(f"Đã lưu thành công: {saved} bản ghi.")
print(f"Thời gian thực hiện: {time.time() - start_t:.2f}s")

# Kiểm tra phân bố chiến thuật
total = StockAnalysis.objects.count()
veto_count = StockAnalysis.objects.filter(is_vetoed=True).count()
gold_count = StockAnalysis.objects.filter(is_vetoed=False, master_score__gte=70).count()
guerrilla_count = StockAnalysis.objects.filter(is_vetoed=False, master_score__gte=55, master_score__lt=70).count()
risk_count = StockAnalysis.objects.filter(is_vetoed=False, master_score__lt=55).count()

print("\n=== KẾT QUẢ PHÂN BỐ CHIẾN THUẬT SAU KHI ĐỒNG BỘ CHUẨN ===")
print(f"Tổng số mã: {total}")
print(f"💎 GOLD (Score >= 70):           {gold_count}")
print(f"🚀 GUERRILLA (55 <= Score < 70): {guerrilla_count}")
print(f"🔥 RISK (Score < 55):             {risk_count}")
print(f"🚫 VETO:                          {veto_count}")

# Top 5 mã có điểm cao nhất
top_picks = StockAnalysis.objects.filter(is_vetoed=False).order_by('-master_score')[:5]
print("\nTop 5 cổ phiếu đạt điểm cao nhất (không bị VETO):")
for p in top_picks:
    print(f"  - {p.symbol.symbol:<6} | Giá: {p.symbol.price:>8,.0f} VND | Score: {p.master_score:>2} | Signal: {p.signal:<8} | R:R: {p.risk_reward_ratio:.2f}")
