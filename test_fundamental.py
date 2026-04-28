"""Test fundamental data for multiple stocks"""
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'vnstock_web.settings'

import django
django.setup()

from dashboard.sync_service import get_fundamental_data

symbols = ['FPT', 'HPG', 'MWG', 'VNM', 'SSI', 'ACB', 'CTG', 'TCB', 'VPB', 'MBB']

print("=" * 60)
print("TEST FUNDAMENTAL DATA")
print("=" * 60)

for sym in symbols:
    data = get_fundamental_data(sym)
    pe = data["pe"]
    pb = data["pb"]
    roe = data["roe"]
    f = data["f_score"]
    print(f"{sym:6} | PE={pe:>6} | PB={pb:>5} | ROE={roe:>6} | F={f}/9")

print("=" * 60)
