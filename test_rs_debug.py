from dashboard.sync_service import get_industry_performance
import logging

logging.basicConfig(level=logging.DEBUG)

for symbol in ["VCB", "POW", "VJC"]:
    try:
        val = get_industry_performance(symbol)
        print(symbol, val)
    except Exception as e:
        print(symbol, "ERROR", e)
