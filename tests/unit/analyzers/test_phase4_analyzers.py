"""
Test script for Phase 4 Analyzers
ETF, Forex, Crypto, CW
"""
import sys
sys.path.insert(0, r"d:\OneDrive\Desktop\Trading")

import warnings
warnings.filterwarnings('ignore')

from dashboard.analyzers.fund_analyzer import FundAnalyzer
from dashboard.analyzers.forex_analyzer import ForexAnalyzer
from dashboard.analyzers.crypto_analyzer import CryptoAnalyzer
from dashboard.analyzers.cw_analyzer import CWAnalyzer


def test_phase4():
    print("=" * 60)
    print("Phase 4 Test: Fund, Forex, Crypto, CW Analyzers")
    print("=" * 60)
    
    # Test Fund Analyzer
    print("\n" + "=" * 60)
    print("FUND/ETF ANALYZER")
    print("=" * 60)
    
    fund = FundAnalyzer(period_ta=30)
    
    print("\n--- E1VFVN30 ETF ---")
    try:
        result = fund.analyze("E1VFVN30")
        print(fund.format_output(result))
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test Forex Analyzer
    print("\n" + "=" * 60)
    print("FOREX ANALYZER")
    print("=" * 60)
    
    forex = ForexAnalyzer(period_ta=30)
    
    pairs = ["EURUSD", "USDJPY"]
    for pair in pairs:
        print(f"\n--- {pair} ---")
        try:
            result = forex.analyze(pair)
            print(forex.format_output(result))
        except Exception as e:
            print(f"ERROR: {e}")
    
    # Test Crypto Analyzer
    print("\n" + "=" * 60)
    print("CRYPTO ANALYZER")
    print("=" * 60)
    
    crypto = CryptoAnalyzer(period_ta=30)
    
    cryptos = ["BTCUSDT", "ETHUSDT"]
    for sym in cryptos:
        print(f"\n--- {sym} ---")
        try:
            result = crypto.analyze(sym)
            print(crypto.format_output(result))
        except Exception as e:
            print(f"ERROR: {e}")
    
    # Test CW Analyzer
    print("\n" + "=" * 60)
    print("CW (COVERED WARRANT) ANALYZER")
    print("=" * 60)
    
    cw = CWAnalyzer(period_ta=30)
    
    warrants = ["CACB2511", "CHPG2512"]
    for sym in warrants:
        print(f"\n--- {sym} ---")
        try:
            result = cw.analyze(sym)
            print(cw.format_output(result))
        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    test_phase4()
