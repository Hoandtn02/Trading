"""
Script để fetch dữ liệu tài chính quý từ vnstock_data (VCI)
Hỗ trợ tiến trình đồng bộ chuyên sâu BCTC cho Top 30 cổ phiếu
Chạy: python scripts/fetch_quarterly_data.py
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')

import django
django.setup()

# Thêm venv site-packages vào sys.path
for _venv_candidate in [
    os.path.expanduser('~/.venv/Lib/site-packages'),
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.venv', 'Lib', 'site-packages')),
]:
    if os.path.exists(_venv_candidate) and _venv_candidate not in sys.path:
        sys.path.insert(0, _venv_candidate)

from dashboard.sync_service import sync_top30_deep_fundamentals

def main():
    print("🚀 Bắt đầu chạy Deep Fundamental Sync cho Top 30 cổ phiếu...")
    res = sync_top30_deep_fundamentals()
    print("Kết quả:", res)

if __name__ == '__main__':
    main()
