"""
Test script for StockAnalyzer Phase 1 - Technical Analysis
Run: python -m tests.unit.analyzers.test_stock_analyzer
"""
import sys
sys.path.insert(0, r"d:\OneDrive\Desktop\Trading")

from dashboard.analyzers.stock_analyzer import StockAnalyzer, analyze_stock

def test_stock_analyzer():
    """Test StockAnalyzer with real data"""
    print("=" * 60)
    print("Phase 1 Test: StockAnalyzer - Technical Analysis")
    print("=" * 60)
    
    analyzer = StockAnalyzer(period_ta=90)
    
    # Test with VCB
    symbols = ["VCB", "TCB", "HPG"]
    
    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"Analyzing: {symbol}")
        print("=" * 60)
        
        try:
            result = analyzer.analyze(symbol, include_sentiment=False)
            print(analyzer.to_string(result))
        except Exception as e:
            print(f"ERROR analyzing {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    return True

if __name__ == "__main__":
    test_stock_analyzer()
