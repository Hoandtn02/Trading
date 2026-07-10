import sys
sys.path.insert(0, 'd:/OneDrive/Desktop/Trading-1')

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
import django
django.setup()

from dashboard.models import StockAnalysis

a = StockAnalysis.objects.filter(symbol__symbol='HDB').first()
if not a:
    print('No HDB analysis row')
else:
    print('id', a.id, 'symbol', a.symbol.symbol)
    for f in [
        'foreign_buy_streak', 'latest_net_val', 'latest_net_val_2',
        'foreign_buy_val', 'foreign_sell_val', 'foreign_absorption_ratio',
        'foreign_trading_share', 'foreign_accumulated_trend',
        'foreign_accumulated_slope'
    ]:
        print(f'{f} = {getattr(a, f)!r}')
