import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
import django
django.setup()
from dashboard.models import StockAnalysis
row = StockAnalysis.objects.select_related('symbol').filter(symbol__symbol='HDB').first()
if not row:
    print('HDB_NOT_FOUND')
else:
    print({
        'symbol': row.symbol.symbol,
        'foreign_buy_val': row.foreign_buy_val,
        'foreign_sell_val': row.foreign_sell_val,
        'foreign_trading_share': row.foreign_trading_share,
        'foreign_accumulated_trend': row.foreign_accumulated_trend,
        'foreign_accumulated_slope': row.foreign_accumulated_slope,
        'latest_net_val': row.latest_net_val,
        'foreign_buy_streak': row.foreign_buy_streak,
        'updated': str(getattr(row, 'updated_at', None)),
    })
