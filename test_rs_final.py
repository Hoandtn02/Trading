"""
Test hàm get_industry_performance đã sửa
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
sys.path.insert(0, r'd:\OneDrive\Desktop\Trading-1')
django.setup()

import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("TEST: get_industry_performance (FIX v3)")
print("=" * 60)

from dashboard.sync_service import get_industry_performance

# Test với các mã đầu ngành
test_symbols = ['VCB', 'FPT', 'MWG', 'VNM', 'HPG', 'TCB', 'SAB', 'VHM']

for symbol in test_symbols:
    rs = get_industry_performance(symbol)
    
    if rs >= 5:
        label = "LEADER"
        bonus = 15
    elif rs >= 2:
        label = "OUTPERFORM"
        bonus = 8
    elif rs >= -2:
        label = "NEUTRAL"
        bonus = 0
    elif rs >= -5:
        label = "UNDERPERFORM"
        bonus = -5
    else:
        label = "LAGGARD"
        bonus = -10
    
    print(f"  {symbol:>6}: RS = {rs:>+6.2f}% -> {label} (bonus: {bonus:>+3})")

print("=" * 60)
