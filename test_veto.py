"""
Check VETO reasons
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
sys.path.insert(0, r'd:\OneDrive\Desktop\Trading-1')
django.setup()

from dashboard.models import StockAnalysis

# Get VETO reasons distribution
print("=" * 60)
print("VETO REASONS DISTRIBUTION")
print("=" * 60)

from django.db.models import Count
vetos = StockAnalysis.objects.filter(is_vetoed=True).values('veto_reason').annotate(count=Count('id')).order_by('-count')

for v in vetos[:30]:
    reason = v['veto_reason'] or '(empty)'
    print(f"  {v['count']:>3}x: {reason}")

# Check FPT specifically
print("\n--- FPT VETO Details ---")
fpt = StockAnalysis.objects.filter(symbol__symbol='FPT').first()
if fpt:
    print(f"is_vetoed: {fpt.is_vetoed}")
    print(f"veto_reason: {fpt.veto_reason}")
    print(f"industry_performance: {fpt.industry_performance}")

# Check some non-veto stocks
print("\n--- Non-VETO Stocks with RS ---")
non_veto = StockAnalysis.objects.filter(is_vetoed=False).exclude(rs_label='VETO').order_by('-industry_performance')[:10]
for a in non_veto:
    print(f"  {a.symbol.symbol}: RS={a.industry_performance:+.2f}, Label={a.rs_label}")

print("=" * 60)
