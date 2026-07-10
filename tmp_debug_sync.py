import sys, os
sys.path.insert(0, 'd:/OneDrive/Desktop/Trading-1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')
import django
django.setup()

from dashboard.sync_service import get_exact_foreign_metrics
print(get_exact_foreign_metrics('HDB'))
