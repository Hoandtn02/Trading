import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vnstock_web.settings")
import django
django.setup()

from dashboard.models import StockData, StockAnalysis

stocks = StockData.objects.all()[:30]
print(f"Kiểm tra Relative Strength của 30 cổ phiếu đầu tiên:\n")

header = f"{'Symbol':<6} | {'Price':<8} | {'Industry':<20} | {'RS_Label':<10} | {'Ind_Perf_%':<12} | {'RS_Bonus':<10} | {'Is_Leader':<10}"
print(header)
print("-" * len(header))

neutral_count = 0
zero_perf_count = 0
zero_bonus_count = 0

for s in stocks:
    analysis = getattr(s, "analysis", None)
    rs_label = analysis.rs_label if analysis else "N/A"
    ind_perf = analysis.industry_performance if analysis else 0.0
    rs_bonus = analysis.rs_bonus if analysis else 0
    is_leader = analysis.is_industry_leader if analysis else False
    ind = s.industry or "N/A"

    if rs_label == "NEUTRAL":
        neutral_count += 1
    if ind_perf == 0.0:
        zero_perf_count += 1
    if rs_bonus == 0:
        zero_bonus_count += 1

    print(f"{s.symbol:<6} | {s.price:<8.1f} | {ind:<20} | {rs_label:<10} | {ind_perf:<12.2f} | {rs_bonus:<10} | {str(is_leader):<10}")

print("\n" + "="*50)
print(f"Thống kê trên 30 mã đầu:")
print(f"- RS Label = 'NEUTRAL': {neutral_count}/30")
print(f"- Industry Perf = 0.0%: {zero_perf_count}/30")
print(f"- RS Bonus = 0: {zero_bonus_count}/30")
