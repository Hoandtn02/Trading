"""
Check StockAnalysis RS values
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
sys.path.insert(0, r'd:\OneDrive\Desktop\Trading-1')
django.setup()

from dashboard.models import StockAnalysis, StockData

# Get recent analyses
analyses = StockAnalysis.objects.select_related('symbol').all()[:20]

print("=" * 90)
print(f"{'Symbol':<8} {'Industry Perf':>14} {'RS Label':<12} {'RS Bonus':>10} {'Master Score':>12}")
print("-" * 90)

for a in analyses:
    symbol = a.symbol.symbol
    ind_perf = a.industry_performance or 0
    rs_label = a.rs_label or 'N/A'
    rs_bonus = a.rs_bonus or 0
    score = a.master_score or 0
    
    print(f"{symbol:<8} {ind_perf:>+14.2f} {rs_label:<12} {rs_bonus:>+10} {score:>12}")

print("=" * 90)

# Check specific stock
print("\n--- FPT ---")
fpt = StockAnalysis.objects.filter(symbol__symbol='FPT').first()
if fpt:
    print(f"industry_performance: {fpt.industry_performance}")
    print(f"rs_label: {fpt.rs_label}")
    print(f"rs_bonus: {fpt.rs_bonus}")
else:
    print("FPT not found!")

# Count RS labels distribution
print("\n--- RS Label Distribution ---")
from django.db.models import Count
dist = StockAnalysis.objects.values('rs_label').annotate(count=Count('id')).order_by('-count')
for d in dist:
    print(f"  {d['rs_label']}: {d['count']}")
