import sys
import types
import pandas as pd
from unittest import mock

# Create a minimal Django mock package
django_pkg = types.ModuleType("django")
django_utils_pkg = types.ModuleType("django.utils")
django_utils_timezone = types.ModuleType("django.utils.timezone")
django_utils_timezone.now = lambda: None
django_utils_timezone.make_aware = lambda dt: dt
django_utils_timezone.utc = None

django_utils_pkg.timezone = django_utils_timezone
django_pkg.utils = django_utils_pkg

# Mock django.core.cache
django_core_pkg = types.ModuleType("django.core")
django_core_cache = types.ModuleType("django.core.cache")
django_core_cache.cache = mock.MagicMock()
django_core_cache.cache.get.return_value = None
django_core_pkg.cache = django_core_cache

# Mock django.conf
django_conf = types.ModuleType("django.conf")
django_conf.settings = mock.MagicMock()
django_conf.settings.INSTALLED_APPS = []
django_pkg.conf = django_conf

# Register all mocks
sys.modules["django"] = django_pkg
sys.modules["django.utils"] = django_utils_pkg
sys.modules["django.utils.timezone"] = django_utils_timezone
sys.modules["django.core"] = django_core_pkg
sys.modules["django.core.cache"] = django_core_cache

# Mock vnstock_data module
vnstock_data_mock = types.ModuleType("vnstock_data")

class MockQuote:
    def __init__(self, symbol=None):
        self.symbol = symbol

    def history(self, symbol=None, length=None, interval=None):
        sym = symbol or self.symbol
        if sym == "VNINDEX":
            return pd.DataFrame({
                "close": [1000.0, 1005.0, 1010.0, 1015.0, 1020.0]
            })
        else:
            return pd.DataFrame({
                "close": [50.0, 51.0, 52.0, 53.0, 54.0]
            })

class MockInsights:
    def screener(self):
        return self

    def filter(self, n):
        return self

    def __call__(self):
        return self

vnstock_data_mock.Quote = MockQuote
vnstock_data_mock.Insights = MockInsights
sys.modules["vnstock_data"] = vnstock_data_mock

# Now import the function
from dashboard.sync_service import get_industry_performance

# Test 1: Screener success
print("=== Test 1: Screener success ===")
insights = MockInsights()
insights._df = pd.DataFrame({
    "symbol": ["VCB"],
    "outperforms_index_3m": [5.5],
    "rs_3m": [3.2]
})

def screener_filter(self, n):
    return self

def screener_call(self):
    return self._df

with mock.patch.object(MockInsights, "screener", lambda self: self), \
     mock.patch.object(MockInsights, "filter", screener_filter), \
     mock.patch.object(MockInsights, "__call__", screener_call), \
     mock.patch("dashboard.sync_service.Insights", MockInsights):
    val = get_industry_performance("VCB")
    print(f"VCB RS = {val}")
    assert val == 5.5, f"Expected 5.5, got {val}"

# Test 2: Direct quote calculation
print("\n=== Test 2: Direct quote calculation ===")

class BrokenInsights:
    def screener(self):
        raise Exception("screener not available")

with mock.patch("dashboard.sync_service.Insights", side_effect=Exception("no insights")), \
     mock.patch("dashboard.sync_service.Quote", MockQuote):
    val = get_industry_performance("POW")
    print(f"POW RS = {val}")
    # stock return = (54-50)/50 * 100 = 8.0
    # vn return = (1020-1000)/1000 * 100 = 2.0
    # expected = 8.0 - 2.0 = 6.0
    assert val == 6.0, f"Expected 6.0, got {val}"

print("\nAll tests passed!")
