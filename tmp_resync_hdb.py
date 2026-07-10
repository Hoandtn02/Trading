import sys
sys.path.insert(0, 'd:/OneDrive/Desktop/Trading-1')
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
import django
django.setup()
from dashboard.sync_service import analyze_stock

result = analyze_stock('HDB', market_rsi=50.0, fast_mode=False)
print('result keys:', list(result.keys()) if result else None)
if result:
    for k in ['foreign_buy_streak','latest_net_val','latest_net_val_2','foreign_buy_val','foreign_sell_val','foreign_absorption_ratio','foreign_trading_share','foreign_accumulated_trend','foreign_accumulated_slope']:
        print(k, result.get(k))
