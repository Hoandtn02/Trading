import sys
import os
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
import django
django.setup()

TV_SERVICE_URL = "http://localhost:7788"

print("Testing TV Inputs for SMA...")
try:
    r = requests.post(
        f"{TV_SERVICE_URL}/indicators",
        json={
            "symbol": "HOSE:SSI", 
            "indicator": "STD;SMA", 
            "timeframe": "D",
            "inputs": {"length": 50}
        },
        timeout=15
    )
    data = r.json()
    print("SMA 50:")
    print(data.get('data')[-1] if data.get('data') else data)
except Exception as e:
    print(f"Lỗi khi kết nối TV service: {e}")
