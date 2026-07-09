"""
Quick test: Sync FPT and check RS label
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
sys.path.insert(0, r'd:\OneDrive\Desktop\Trading-1')
django.setup()

import warnings
warnings.filterwarnings('ignore')

from dashboard.sync_service import analyze_stock
from dashboard.models import StockAnalysis

# Test FPT
print("=" * 60)
print("TEST: Sync FPT with FIXED rs_label")
print("=" * 60)

result = analyze_stock('FPT', market_rsi=50.0, fast_mode=False)

if result:
    print(f"Symbol: {result.get('symbol')}")
    print(f"is_vetoed: {result.get('is_vetoed')}")
    print(f"veto_reason: {result.get('veto_reason')}")
    print(f"industry_performance: {result.get('industry_performance')}")
    print(f"rs_label: {result.get('rs_label')}")
    print(f"rs_bonus: {result.get('rs_bonus')}")
    print(f"master_score: {result.get('master_score')}")
else:
    print("FAILED to analyze FPT")

# Check in DB
print("\n--- DB Check ---")
fpt_analysis = StockAnalysis.objects.filter(symbol__symbol='FPT').first()
if fpt_analysis:
    print(f"DB rs_label: {fpt_analysis.rs_label}")
    print(f"DB industry_performance: {fpt_analysis.industry_performance}")
    print(f"DB rs_bonus: {fpt_analysis.rs_bonus}")
    print(f"DB is_vetoed: {fpt_analysis.is_vetoed}")
else:
    print("FPT not found in DB")

print("=" * 60)
