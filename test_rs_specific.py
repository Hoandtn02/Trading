"""
Test RS logic for specific stocks
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

test_symbols = ['VJC', 'MSB', 'LPB', 'VHM']

print("=" * 80)
print("TEST: RS Logic for VJC, MSB, LPB, VHM")
print("=" * 80)

for symbol in test_symbols:
    print(f"\n{'='*50}")
    print(f"📊 {symbol}")
    print("-" * 50)
    
    # Get from DB first
    db = StockAnalysis.objects.filter(symbol__symbol=symbol).first()
    if db:
        print(f"[DB] rs_label: {db.rs_label}")
        print(f"[DB] rs_bonus: {db.rs_bonus}")
        print(f"[DB] industry_performance: {db.industry_performance}")
        print(f"[DB] industry: {db.symbol.industry if db.symbol else 'N/A'}")
    
    # Run analysis
    print(f"\n[Analysis] Running analyze_stock...")
    result = analyze_stock(symbol, market_rsi=50.0, fast_mode=False)
    
    if result:
        rs_label = result.get('rs_label', 'N/A')
        rs_bonus = result.get('rs_bonus', 0)
        ind_perf = result.get('industry_performance', 0)
        industry = result.get('industry', 'N/A')
        is_veto = result.get('is_vetoed', False)
        
        print(f"\n[Result]")
        print(f"  rs_label: {rs_label}")
        print(f"  rs_bonus: {rs_bonus}")
        print(f"  industry_performance: {ind_perf:+.2f}%")
        print(f"  industry: {industry}")
        print(f"  is_vetoed: {is_veto}")
        
        # Expected label
        if is_veto:
            print(f"  Status: 🚫 VETO (RS calculation skipped)")
        else:
            if ind_perf >= 5:
                expected = "LEADER"
                expected_bonus = 15
            elif ind_perf >= 2:
                expected = "OUTPERFORM"
                expected_bonus = 10
            elif ind_perf >= -2:
                expected = "NEUTRAL"
                expected_bonus = 5
            elif ind_perf >= -5:
                expected = "UNDERPERFORM"
                expected_bonus = 0
            else:
                expected = "LAGGARD"
                expected_bonus = -10
            
            status = "✅" if rs_label == expected else "❌"
            bonus_status = "✅" if rs_bonus == expected_bonus else "❌"
            print(f"  Expected RS Label: {expected} {status}")
            print(f"  Expected RS Bonus: {expected_bonus} {bonus_status}")
    else:
        print(f"  ❌ FAILED to analyze")

print("\n" + "=" * 80)
