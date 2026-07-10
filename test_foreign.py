import sys, os
sys.path.insert(0, 'd:/OneDrive/Desktop/Trading-1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
import django
django.setup()

from dashboard.sync_service import get_exact_foreign_metrics

for sym in ['VHM', 'VIC', 'FPT']:
    r = get_exact_foreign_metrics(sym)
    print(f'{sym}:')
    print(f'  foreign_streak = {r["foreign_streak"]}')
    print(f'  latest_net_val = {r["latest_net_val"]/1e9:.2f}B')
    print(f'  latest_net_val_2 = {r["latest_net_val_2"]/1e9:.2f}B')
    print(f'  foreign_absorption_ratio = {r["foreign_absorption_ratio"]}%')
    print()