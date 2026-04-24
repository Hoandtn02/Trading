"""
Test script for Gold & Futures Analyzer - Phase 3
"""
import sys
sys.path.insert(0, r"d:\OneDrive\Desktop\Trading")

import warnings
warnings.filterwarnings('ignore')

from dashboard.analyzers.gold_analyzer import GoldAnalyzer
from dashboard.analyzers.futures_analyzer import FuturesAnalyzer


def test_phase3():
    print("=" * 60)
    print("Phase 3 Test: Gold & Futures Analyzers")
    print("=" * 60)
    
    # Test Gold Analyzer
    print("\n" + "=" * 60)
    print("GOLD ANALYZER")
    print("=" * 60)
    
    gold = GoldAnalyzer(period_ta=30)
    
    # Test gold_vn
    print("\n--- Vàng SJC Việt Nam ---")
    try:
        result = gold.analyze("gold_vn")
        print(gold.format_output(result))
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test gold_global
    print("\n--- Vàng Thế Giới ---")
    try:
        result = gold.analyze("gold_global")
        print(gold.format_output(result))
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test oil_crude
    print("\n--- Dầu Thô WTI ---")
    try:
        result = gold.analyze("oil_crude")
        print(gold.format_output(result))
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test Futures Analyzer
    print("\n" + "=" * 60)
    print("FUTURES ANALYZER")
    print("=" * 60)
    
    futures = FuturesAnalyzer(period_ta=30)
    
    print("\n--- VN30 Futures ---")
    try:
        result = futures.analyze("VN30F")
        print(futures.format_output(result))
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    test_phase3()
