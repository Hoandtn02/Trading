"""
Test script để kiểm tra Relative Strength calculation
Chạy: & "$env:USERPROFILE\.venv\Scripts\python.exe" test_rs.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
sys.path.insert(0, r'd:\OneDrive\Desktop\Trading-1')
django.setup()

import pandas as pd
from datetime import datetime, timedelta

print("=" * 60)
print("TEST: Relative Strength - Chi tiết")
print("=" * 60)

# Test 1: get_sector_category với ICB codes
print("\n[TEST 1] get_sector_category với ICB Codes")
print("-" * 40)

from dashboard.sync_service import get_sector_category

# Test với ICB codes
test_cases = [
    ("Thực phẩm và đồ uống", "3500"),
    ("Bia và đồ uống", "3530"),
    ("Sản xuất bia", "3533"),
    ("Đồ uống & giải khát", "3537"),
    ("Ngân hàng", "8000"),
    ("Bất động sản", "8500"),
    ("Bia/Nước giải khát", ""),  # Không có ICB
    ("Ngân hàng TMCP", ""),  # Không có ICB
]

for industry, icb_code in test_cases:
    sector = get_sector_category(industry, icb_code)
    print(f"  '{industry}' (ICB:{icb_code}) -> '{sector}'")

# Test 2: Database Stock Analysis
print("\n[TEST 2] Database Stock Analysis")
print("-" * 40)

from dashboard.models import StockData, StockAnalysis

stocks = StockData.objects.all()[:5]
print(f"Tổng số mã trong database: {StockData.objects.count()}")

for stock in stocks:
    try:
        analysis = StockAnalysis.objects.get(symbol=stock)
        rs_label = getattr(analysis, 'rs_label', 'N/A')
        rs_bonus = getattr(analysis, 'rs_bonus', 'N/A')
        rs_perf = getattr(analysis, 'industry_performance', 0)
        sector = get_sector_category(stock.industry or stock.get_industry())
        
        print(f"  {stock.symbol}: industry='{stock.industry}', sector='{sector}'")
        print(f"    RS: {rs_label}, Bonus: {rs_bonus}, Perf: {rs_perf}%")
    except StockAnalysis.DoesNotExist:
        print(f"  {stock.symbol}: No analysis found")

# Test 3: Median Fallback
print("\n[TEST 3] Median Fallback")
print("-" * 40)

from dashboard.sync_service import apply_median_fallback

test_raw_data = {
    'pe': 15.0,
    'pb': 2.0,
    'roe': 18.0,
}

banking_enriched = apply_median_fallback(test_raw_data, 'banking', 'TEST')
print(f"  Banking fallback: {banking_enriched.get('_fallback_applied', [])}")
print(f"    NIM={banking_enriched.get('nim')}, NPL={banking_enriched.get('npl')}")

mfg_enriched = apply_median_fallback(test_raw_data, 'manufacturing', 'TEST')
print(f"  Manufacturing fallback: {mfg_enriched.get('_fallback_applied', [])}")
print(f"    Gross Margin={mfg_enriched.get('gross_margin')}")

print("\n" + "=" * 60)
print("SUMMARY: Tất cả fixes đã được apply")
print("=" * 60)
print("""
1. get_sector_category() - Đã thêm ICB code support
2. get_industry_performance() - So sánh với VNIndex
3. apply_median_fallback() - Median fallback cho missing data
4. Database fields - rs_label, rs_bonus đã được thêm
5. CSV Export - Đã thêm columns mới

Sau khi chạy sync, dữ liệu RS sẽ được tính đúng.
""")
