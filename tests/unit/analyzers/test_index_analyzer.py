"""
Test script for IndexAnalyzer - Phase 2
"""
import sys
sys.path.insert(0, r"d:\OneDrive\Desktop\Trading")

import warnings
warnings.filterwarnings('ignore')

from dashboard.analyzers.index_analyzer import IndexAnalyzer


def test_index_analyzer():
    print("=" * 60)
    print("Phase 2 Test: Index Analyzer")
    print("=" * 60)
    
    analyzer = IndexAnalyzer(period_ta=60)
    
    # Test with VNIndex
    indices = ["VNINDEX", "VN30", "HNXIndex"]
    
    for symbol in indices:
        print(f"\n{'='*60}")
        print(f"Analyzing: {symbol}")
        print("=" * 60)
        
        try:
            result = analyzer.analyze(symbol)
            print(analyzer.format_output(result))
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    test_index_analyzer()
