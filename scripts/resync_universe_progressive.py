import os
import sys
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
django.setup()

from dashboard.sync_service import analyze_stock, save_results_to_db, get_market_rsi
from dashboard.models import StockData, StockAnalysis
from concurrent.futures import ThreadPoolExecutor, as_completed

def run():
    print("=== TIẾN HÀNH ĐỒNG BỘ TỪNG LÔ CHO 116 MÃ CỔ PHIẾU ===")
    symbols = list(StockData.objects.values_list('symbol', flat=True))
    total_symbols = len(symbols)
    print(f"Tổng số mã: {total_symbols}")
    
    market_rsi = get_market_rsi()
    print(f"Market RSI: {market_rsi}")
    
    BATCH_SIZE = 15
    saved_total = 0
    start_all = time.time()
    
    for i in range(0, total_symbols, BATCH_SIZE):
        batch = symbols[i:i + BATCH_SIZE]
        print(f"\n[Batch {i//BATCH_SIZE + 1}/{(total_symbols + BATCH_SIZE - 1)//BATCH_SIZE}] Đang xử lý {len(batch)} mã: {batch[:5]}...")
        t0 = time.time()
        
        batch_results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_sym = {executor.submit(analyze_stock, sym, market_rsi, True): sym for sym in batch}
            for fut in as_completed(future_to_sym):
                sym = future_to_sym[fut]
                try:
                    res = fut.result(timeout=40)
                    if res:
                        batch_results.append(res)
                except Exception as e:
                    print(f"  Lỗi {sym}: {e}")
                    
        if batch_results:
            n_saved = save_results_to_db(batch_results)
            saved_total += n_saved
            print(f"  -> Lưu thành công {n_saved}/{len(batch)} mã ({time.time() - t0:.1f}s)")
        else:
            print(f"  -> Không có kết quả hợp lệ trong batch này")
            
    print(f"\n=== ĐÃ HOÀN TẤT ĐỒNG BỘ: {saved_total}/{total_symbols} mã trong {time.time() - start_all:.1f}s ===")
    
    # Kiểm tra phân bố
    veto_cnt = StockAnalysis.objects.filter(is_vetoed=True).count()
    gold_cnt = StockAnalysis.objects.filter(is_vetoed=False, master_score__gte=70).count()
    guerrilla_cnt = StockAnalysis.objects.filter(is_vetoed=False, master_score__gte=55, master_score__lt=70).count()
    risk_cnt = StockAnalysis.objects.filter(is_vetoed=False, master_score__lt=55).count()
    
    print(f"Tổng số mã trong StockAnalysis: {StockAnalysis.objects.count()}")
    print(f"💎 GOLD (>= 70):           {gold_cnt}")
    print(f"🚀 GUERRILLA (55 - 69):     {guerrilla_cnt}")
    print(f"🔥 RISK (< 55):             {risk_cnt}")
    print(f"🚫 VETO:                    {veto_cnt}")

if __name__ == '__main__':
    run()
