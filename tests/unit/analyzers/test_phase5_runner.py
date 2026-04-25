"""
Test script for Phase 5 - Unified Dashboard Runner
"""
import sys
sys.path.insert(0, r"d:\OneDrive\Desktop\Trading")

import warnings
warnings.filterwarnings('ignore')

from dashboard.dashboard_runner import (
    run_stock_analysis,
    run_index_analysis,
    run_gold_analysis,
    run_futures_analysis,
    run_etf_analysis,
    run_crypto_analysis,
    run_market_overview,
    get_cache_stats,
    clear_all_cache,
)


def test_phase5():
    print("=" * 60)
    print("Phase 5 Test: Unified Dashboard Runner")
    print("=" * 60)
    
    # Test Cache Stats
    print("\n--- Cache Stats ---")
    stats = get_cache_stats()
    print(f"Cache files: {stats['count']}")
    print(f"Cache size: {stats['total_size_mb']} MB")
    
    # Clear cache first
    print("\n--- Clearing Cache ---")
    result = clear_all_cache()
    print(f"Cleared: {result['cleared']} files")
    
    # Test Stock Analysis
    print("\n" + "=" * 60)
    print("STOCK ANALYSIS")
    print("=" * 60)
    
    stock = run_stock_analysis("VCB")
    if stock['status'] == 'success':
        print(f"Symbol: {stock['symbol']}")
        print(f"Price: {stock['price']['current']:,.0f} VND")
        print(f"Change: {stock['price']['change_percent']:+.2f}%")
        print(f"RSI: {stock['technical']['rsi']:.1f}")
        print(f"F-Score: {stock['fundamental']['f_score']}/9")
        print(f"Signal: {stock['recommendation']['action']}")
        print(f"Master Score: {stock['recommendation']['master_score']}/100")
    else:
        print(f"ERROR: {stock.get('error')}")
    
    # Test Index Analysis
    print("\n" + "=" * 60)
    print("INDEX ANALYSIS")
    print("=" * 60)
    
    index = run_index_analysis("VNINDEX")
    if index['status'] == 'success':
        print(f"Index: {index['symbol']}")
        print(f"Value: {index['current_value']:,.2f}")
        print(f"Change: {index['change_percent']:+.2f}%")
        print(f"Trend: {index['trend']}")
        print(f"Market Breadth: {index['breadth_percent']:.1f}% up")
    else:
        print(f"ERROR: {index.get('error')}")
    
    # Test Gold Analysis
    print("\n" + "=" * 60)
    print("GOLD ANALYSIS")
    print("=" * 60)
    
    gold = run_gold_analysis("gold_vn")
    if gold['status'] == 'success':
        print(f"Type: {gold['name']}")
        print(f"Buy: {gold['buy_price']:,.0f} VND")
        print(f"Sell: {gold['sell_price']:,.0f} VND")
        print(f"Change: {gold['change_percent']:+.2f}%")
    else:
        print(f"ERROR: {gold.get('error')}")
    
    # Test Futures Analysis
    print("\n" + "=" * 60)
    print("FUTURES ANALYSIS")
    print("=" * 60)
    
    futures = run_futures_analysis("VN30F")
    if futures['status'] == 'success':
        print(f"Contract: {futures['symbol']}")
        print(f"Price: {futures['current_price']:,.2f}")
        print(f"Change: {futures['change_percent']:+.2f}%")
        print(f"Basis: {futures['basis']:+.2f}")
    else:
        print(f"ERROR: {futures.get('error')}")
    
    # Test ETF Analysis
    print("\n" + "=" * 60)
    print("ETF ANALYSIS")
    print("=" * 60)
    
    etf = run_etf_analysis("E1VFVN30")
    if etf['status'] == 'success':
        print(f"Symbol: {etf['symbol']}")
        print(f"NAV: {etf['nav']:,.0f}")
        print(f"Change: {etf['change_percent']:+.2f}%")
    else:
        print(f"ERROR: {etf.get('error')}")
    
    # Test Crypto Analysis
    print("\n" + "=" * 60)
    print("CRYPTO ANALYSIS")
    print("=" * 60)
    
    crypto = run_crypto_analysis("BTCUSDT")
    if crypto['status'] == 'success':
        print(f"Symbol: {crypto['name']}")
        print(f"Price: ${crypto['current_price']:,.2f}")
        print(f"Change 24h: {crypto['change_percent_24h']:+.2f}%")
    else:
        print(f"ERROR: {crypto.get('error')}")
    
    # Test Market Overview (batch)
    print("\n" + "=" * 60)
    print("MARKET OVERVIEW (Batch)")
    print("=" * 60)
    
    overview = run_market_overview()
    print(f"Timestamp: {overview['timestamp']}")
    print(f"Indices: {list(overview['indices'].keys())}")
    print(f"Gold types: {list(overview['gold'].keys())}")
    print(f"Crypto: {list(overview['crypto'].keys())}")
    
    # Cache stats after
    print("\n--- Cache Stats After ---")
    stats = get_cache_stats()
    print(f"Cache files: {stats['count']}")
    print(f"Cache size: {stats['total_size_mb']} MB")
    
    print("\n" + "=" * 60)
    print("Phase 5 Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_phase5()
