"""
Test script to verify which APIs work correctly
"""
import warnings
warnings.filterwarnings("ignore")

def test_vnstock_data():
    print("=" * 60)
    print("Testing vnstock_data APIs")
    print("=" * 60)
    
    # Test 1: Market().index()
    print("\n1. Testing Market().index('VNINDEX').ohlcv()...")
    try:
        from vnstock_data import Market
        mkt = Market()
        df = mkt.index("VNINDEX").ohlcv(interval="1D", length=5)
        print(f"   SUCCESS: Got {len(df)} rows")
        print(f"   Columns: {list(df.columns)[:5]}")
        print(f"   Last row: {df.iloc[-1].to_dict()}")
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")
    
    # Test 2: Market().bond()
    print("\n2. Testing Market().bond('VNBY5Y').history()...")
    try:
        from vnstock_data import Market
        mkt = Market()
        df = mkt.bond("VNBY5Y").history(length="30D")
        print(f"   SUCCESS: Got {len(df)} rows")
        if df is not None and len(df) > 0:
            print(f"   Columns: {list(df.columns)[:5]}")
            print(f"   Last row: {df.iloc[-1].to_dict()}")
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")
    
    # Test 3: Market().etf()
    print("\n3. Testing Market().etf('E1VFVN30').ohlcv()...")
    try:
        from vnstock_data import Market
        mkt = Market()
        df = mkt.etf("E1VFVN30").ohlcv(interval="1D", length=5)
        print(f"   SUCCESS: Got {len(df)} rows")
        if df is not None and len(df) > 0:
            print(f"   Columns: {list(df.columns)[:5]}")
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")
    
    # Test 4: Market().forex()
    print("\n4. Testing Market().forex('USDVND').ohlcv()...")
    try:
        from vnstock_data import Market
        mkt = Market()
        df = mkt.forex("USDVND").ohlcv(interval="1D", length=5)
        print(f"   SUCCESS: Got {len(df)} rows")
        if df is not None and len(df) > 0:
            print(f"   Columns: {list(df.columns)[:5]}")
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")
    
    # Test 5: Fund.listing()
    print("\n5. Testing Fund().listing()...")
    try:
        from vnstock_data import Fund
        fund = Fund()
        df = fund.listing()
        print(f"   SUCCESS: Got {len(df)} rows")
        if df is not None and len(df) > 0:
            print(f"   Columns: {list(df.columns)[:5]}")
            print(f"   First 3: {df.head(3)[['short_name', 'nav']].to_dict()}")
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")

def test_analyzers():
    print("\n" + "=" * 60)
    print("Testing Dashboard Analyzers")
    print("=" * 60)
    
    # Test IndexAnalyzer
    print("\n1. Testing IndexAnalyzer...")
    try:
        from dashboard.analyzers import IndexAnalyzer
        analyzer = IndexAnalyzer(period_ta=30)
        result = analyzer.analyze("VNINDEX")
        print(f"   Symbol: {result.symbol}")
        print(f"   Current Value: {result.current_value}")
        print(f"   Change: {result.change_percent}%")
        print(f"   Trend: {result.trend}")
        print(f"   SUCCESS")
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")
    
    # Test FuturesAnalyzer
    print("\n2. Testing FuturesAnalyzer...")
    try:
        from dashboard.analyzers import FuturesAnalyzer
        analyzer = FuturesAnalyzer(period_ta=30)
        result = analyzer.analyze("VN30F")
        print(f"   Symbol: {result.symbol}")
        print(f"   Current Price: {result.current_price}")
        print(f"   Trend: {result.trend}")
        print(f"   SUCCESS")
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")
    
    # Test FundAnalyzer
    print("\n3. Testing FundAnalyzer...")
    try:
        from dashboard.analyzers import FundAnalyzer
        analyzer = FundAnalyzer(period_ta=30)
        result = analyzer.analyze("E1VFVN30")
        print(f"   Symbol: {result.symbol}")
        print(f"   NAV: {result.nav}")
        print(f"   Trend: {result.trend}")
        print(f"   SUCCESS")
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")
    
    # Test ForexAnalyzer
    print("\n4. Testing ForexAnalyzer...")
    try:
        from dashboard.analyzers import ForexAnalyzer
        analyzer = ForexAnalyzer(period_ta=30)
        result = analyzer.analyze("USDVND")
        print(f"   Symbol: {result.symbol}")
        print(f"   Rate: {result.current_rate}")
        print(f"   Trend: {result.trend}")
        print(f"   SUCCESS")
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")
    
    # Test GovBondIndexAnalyzer
    print("\n5. Testing GovBondIndexAnalyzer...")
    try:
        from dashboard.analyzers import GovBondIndexAnalyzer
        analyzer = GovBondIndexAnalyzer()
        result = analyzer.analyze("VNBY5Y")
        print(f"   Symbol: {result.symbol}")
        print(f"   Name: {result.name}")
        print(f"   Current Price: {result.current_price}")
        print(f"   Trend: {result.trend}")
        print(f"   SUCCESS")
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")

if __name__ == "__main__":
    import sys
    sys.path.insert(0, r'd:\OneDrive\Desktop\Trading')
    
    test_vnstock_data()
    test_analyzers()
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
