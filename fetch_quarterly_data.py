"""
Script để fetch dữ liệu tài chính quý từ vnstock_data
Chạy: python fetch_quarterly_data.py
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')

import django
django.setup()

from dashboard.models import QuarterlyFinancial

# Thêm venv site-packages vào sys.path
venv_site = os.path.expanduser(r"~/.venv/Lib/site-packages")
if venv_site not in sys.path:
    sys.path.insert(0, venv_site)

def fetch_and_save_quarterly():
    """Fetch dữ liệu quý từ vnstock_data và lưu vào DB"""
    
    from vnstock_data import Finance
    
    # Symbols cần fetch
    symbols = [
        'HDB', 'VCB', 'BID', 'TCB', 'ACB', 'VPB', 'MBB', 'STB', 'TPB',
        'FPT', 'HPG', 'SSI', 'VND',
        'VNM', 'MWG', 'PNJ',
        'VRE', 'VHM', 'NVL', 'KDH',
    ]
    
    results = []
    
    for symbol in symbols:
        print(f"Fetching {symbol}...", end=" ", flush=True)
        
        try:
            f = Finance(source='VCI', symbol=symbol)
            df = f.ratio(period='quarter', limit=12)
            
            count = 0
            for period in df.index:
                row = df.loc[period]
                roe = row.get('ROE (%)', 0)
                
                # Convert to percentage
                if roe and roe > 1:
                    roe_pct = roe
                else:
                    roe_pct = roe * 100 if roe else 0
                
                # Parse quarter date
                quarter_date = None
                try:
                    year = period[:4]
                    if 'Q1' in period: quarter_date = f"{year}-03-31"
                    elif 'Q2' in period: quarter_date = f"{year}-06-30"
                    elif 'Q3' in period: quarter_date = f"{year}-09-30"
                    elif 'Q4' in period: quarter_date = f"{year}-12-31"
                except: pass
                
                # F-Score calculation
                f_score = 0
                if roe_pct >= 25: f_score = 7
                elif roe_pct >= 20: f_score = 5
                elif roe_pct >= 15: f_score = 3
                else: f_score = 1
                
                # VETO
                is_vetoed = roe_pct < 15
                veto_reason = "ROE < 15" if is_vetoed else ""
                
                if quarter_date:
                    qf, created = QuarterlyFinancial.objects.update_or_create(
                        symbol=symbol,
                        quarter=period,
                        defaults={
                            'quarter_date': quarter_date,
                            'roe': round(roe_pct, 2),
                            'f_score': f_score,
                            'is_vetoed': is_vetoed,
                            'veto_reason': veto_reason,
                        }
                    )
                    count += 1
            
            print(f"{count} quarters")
            results.append({'symbol': symbol, 'count': count})
            
        except Exception as e:
            print(f"ERROR: {e}")
    
    print(f"\n{'='*50}")
    print(f"COMPLETE: {len(results)} symbols processed")
    
    # Summary
    print("\nSUMMARY:")
    total = 0
    for r in results:
        count = QuarterlyFinancial.objects.filter(symbol=r['symbol']).count()
        total += count
        print(f"  {r['symbol']}: {count} quarters")
    print(f"  TOTAL: {total} records")
    
    return results

if __name__ == '__main__':
    fetch_and_save_quarterly()
