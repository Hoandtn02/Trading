import os
import sys
import django
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
django.setup()

from dashboard.sync_service import sync_top30_deep_fundamentals
from dashboard.models import QuarterlyFinancial, StockData, StockAnalysis

def run_test():
    print("Testing deep fundamental sync on 2 test symbols ['VCB', 'FPT']...")
    t0 = time.time()
    
    result = sync_top30_deep_fundamentals(target_symbols=['VCB', 'FPT'])
    elapsed = time.time() - t0
    
    print(f"\nCompleted deep sync in {elapsed:.1f}s")
    print(f"Result summary: {result}")
    
    for sym in ['VCB', 'FPT']:
        sd = StockData.objects.filter(symbol=sym).first()
        sa = StockAnalysis.objects.filter(symbol__symbol=sym).first()
        qf_list = list(QuarterlyFinancial.objects.filter(symbol=sym).order_by('-quarter_date')[:4])
        
        print(f"\n================ Symbol: {sym} ================")
        if sd:
            print(f"StockData: PE={sd.pe}, PB={sd.pb}, ROE={sd.roe}%, ProfitGrowth={sd.profit_growth}%, F-Score={sd.f_score}")
        if sa:
            print(f"StockAnalysis: Vetoed={sa.is_vetoed}, Reason='{sa.veto_reason}', MasterScore={sa.master_score}")
        print(f"QuarterlyFinancial count: {len(qf_list)}")
        for q in qf_list:
            print(f"  Quý {q.quarter} ({q.quarter_date}): ROE={q.roe}%, ROA={q.roa}%, PE={q.pe}, PB={q.pb}, F-Score={q.f_score}, ProfitGrowth={q.profit_growth}%")

if __name__ == '__main__':
    run_test()
