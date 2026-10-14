import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
import django
django.setup()

from dashboard.models import StockData, StockAnalysis

stocks = StockData.objects.all()[:30]
print(f"Tổng số bản ghi StockData trong DB: {StockData.objects.count()}")
print(f"Kiểm tra 30 cổ phiếu đầu tiên:\n")

header = f"{'Symbol':<6} | {'Price':<8} | {'BB_Mid':<8} | {'BB_%':<6} | {'MACD':<8} | {'MACD_Sig':<8} | {'F_NetVal':<12} | {'F_BuyVal':<12} | {'F_Streak':<8} | {'F_Trend':<10}"
print(header)
print("-" * len(header))

bb_zero_count = 0
macd_zero_count = 0
foreign_zero_count = 0

for s in stocks:
    analysis = getattr(s, 'analysis', None)
    
    # BB check
    bb_zero = (s.bb_middle == 0 and s.bb_upper == 0)
    if bb_zero: bb_zero_count += 1
    
    # MACD check
    macd_zero = (s.macd == 0 and s.macd_signal == 0)
    if macd_zero: macd_zero_count += 1
    
    # Foreign check
    f_net = analysis.latest_net_val if analysis else 0.0
    f_buy = analysis.foreign_buy_val if analysis else 0.0
    f_streak = analysis.foreign_buy_streak if analysis else 0
    f_trend = analysis.foreign_accumulated_trend if analysis else "N/A"
    
    foreign_zero = (f_net == 0 and f_buy == 0 and f_streak == 0)
    if foreign_zero: foreign_zero_count += 1
    
    print(f"{s.symbol:<6} | {s.price:<8.1f} | {s.bb_middle:<8.1f} | {s.bb_percent:<6.1f} | {s.macd:<8.2f} | {s.macd_signal:<8.2f} | {f_net:<12.1f} | {f_buy:<12.1f} | {f_streak:<8} | {f_trend:<10}")

print("\n" + "="*50)
print(f"Thống kê trên 30 mã đầu:")
print(f"- Bollinger Bands bị 0: {bb_zero_count}/30")
print(f"- MACD bị 0: {macd_zero_count}/30")
print(f"- Dòng tiền khối ngoại bị 0: {foreign_zero_count}/30")
