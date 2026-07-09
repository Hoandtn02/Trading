"""
Test multiple stocks: FPT, MSB, and others
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

test_symbols = ['FPT', 'MSB', 'ABB', 'LPB', 'GEX', 'BSR', 'HCM']

print("=" * 80)
print("TEST: RS Label cho nhiều mã")
print("=" * 80)

for symbol in test_symbols:
    print(f"\n{'='*40}")
    print(f"📊 {symbol}")
    print("-" * 40)
    
    # Analyze
    result = analyze_stock(symbol, market_rsi=50.0, fast_mode=False)
    
    if result:
        is_veto = result.get('is_vetoed', False)
        ind_perf = result.get('industry_performance', 0)
        rs_label = result.get('rs_label', 'N/A')
        rs_bonus = result.get('rs_bonus', 0)
        veto_reason = result.get('veto_reason', '')
        master_score = result.get('master_score', 0)
        
        print(f"  is_vetoed: {is_veto}")
        if is_veto:
            print(f"  veto_reason: {veto_reason}")
        print(f"  industry_performance: {ind_perf:+.2f}%")
        print(f"  rs_label: {rs_label}")
        print(f"  rs_bonus: {rs_bonus}")
        print(f"  master_score: {master_score}")
        
        # Expected label based on industry_performance
        if ind_perf >= 5:
            expected = "LEADER"
        elif ind_perf >= 2:
            expected = "OUTPERFORM"
        elif ind_perf >= -2:
            expected = "NEUTRAL"
        elif ind_perf >= -5:
            expected = "UNDERPERFORM"
        else:
            expected = "LAGGARD"
        
        status = "✅" if rs_label == expected else "❌"
        print(f"  Expected: {expected} {status}")
    else:
        print(f"  ❌ FAILED to analyze")

print("\n" + "=" * 80)
print("DB CHECK:")
print("=" * 80)

for symbol in test_symbols:
    db = StockAnalysis.objects.filter(symbol__symbol=symbol).first()
    if db:
        ind_perf = db.industry_performance or 0
        rs_label = db.rs_label or 'N/A'
        rs_bonus = db.rs_bonus or 0
        is_veto = db.is_vetoed
        
        print(f"\n{symbol}: rs_label={rs_label}, rs_bonus={rs_bonus}, ind_perf={ind_perf:+.2f}, veto={is_veto}")
    else:
        print(f"\n{symbol}: NOT FOUND IN DB")

print("\n" + "=" * 80)
