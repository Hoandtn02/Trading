"""
Final Test Script - Complete Dashboard Analyzers
"""
import sys
sys.path.insert(0, r"d:\OneDrive\Desktop\Trading")

import warnings
warnings.filterwarnings('ignore')

from dashboard.analyzers import (
    StockAnalyzer, IndexAnalyzer, GoldAnalyzer, FuturesAnalyzer,
    FundAnalyzer, ForexAnalyzer, CryptoAnalyzer, CWAnalyzer, BondAnalyzer
)
from dashboard.dashboard_runner import (
    run_market_overview, get_cache_stats, clear_all_cache
)


def test_all_analyzers():
    print("=" * 70)
    print("COMPLETE ANALYZERS TEST - ALL PHASES 1-5")
    print("=" * 70)
    
    # Clear cache first
    clear_all_cache()
    print("\n[1/6] Cache cleared")
    
    # Phase 1: Stock
    print("\n" + "=" * 50)
    print("PHASE 1: STOCK ANALYZER")
    print("=" * 50)
    s = StockAnalyzer()
    r = s.analyze("VCB")
    print(f"VCB: {r.technical.current_price:,.0f} VND | RSI: {r.technical.rsi:.1f} | F-Score: {r.fundamental.f_score}/9")
    
    # Phase 2: Index
    print("\n" + "=" * 50)
    print("PHASE 2: INDEX ANALYZER")
    print("=" * 50)
    i = IndexAnalyzer()
    ri = i.analyze("VNINDEX")
    print(f"VNINDEX: {ri.current_value:,.2f} | Change: {ri.change_percent:+.2f}% | Breadth: {ri.breadth_percent:.1f}%")
    
    # Phase 3: Gold & Futures
    print("\n" + "=" * 50)
    print("PHASE 3: GOLD & FUTURES")
    print("=" * 50)
    g = GoldAnalyzer()
    rg = g.analyze("gold_vn")
    print(f"Gold SJC: Buy={rg.buy_price:,.0f} | Sell={rg.sell_price:,.0f}")
    
    f = FuturesAnalyzer()
    rf = f.analyze("VN30F")
    print(f"VN30F: {rf.current_price:,.2f} pts | Basis: {rf.basis:+.2f}")
    
    # Phase 4: ETF, Forex, Crypto, CW
    print("\n" + "=" * 50)
    print("PHASE 4: ETF, FOREX, CRYPTO, CW")
    print("=" * 50)
    
    fund = FundAnalyzer()
    rf2 = fund.analyze("E1VFVN30")
    print(f"ETF E1VFVN30: NAV={rf2.nav:,.0f}")
    
    crypto = CryptoAnalyzer()
    rc = crypto.analyze("BTCUSDT")
    print(f"Crypto BTC: ${rc.current_price:,.2f}")
    
    cw = CWAnalyzer()
    rcw = cw.analyze("CACB2511")
    print(f"CW CACB2511: {rcw.current_price:,.0f} VND | Status: {rcw.status}")
    
    # Phase 5: Bond
    print("\n" + "=" * 50)
    print("PHASE 5 (BONUS): BOND ANALYZER")
    print("=" * 50)
    b = BondAnalyzer()
    rb = b.get_government_bonds_list()
    print(f"Government Bonds: {len(rb)} bonds available")
    
    # Market Overview (Batch)
    print("\n" + "=" * 50)
    print("BATCH PROCESSING: MARKET OVERVIEW")
    print("=" * 50)
    overview = run_market_overview()
    print(f"Timestamp: {overview['timestamp']}")
    print(f"Indices: {list(overview['indices'].keys())}")
    print(f"Gold: {list(overview['gold'].keys())}")
    print(f"Futures: {list(overview['futures'].keys())}")
    print(f"Crypto: {list(overview['crypto'].keys())}")
    print(f"Bonds: {overview['bonds']['status']}")
    
    # Cache stats
    stats = get_cache_stats()
    print(f"\nCache: {stats['count']} files | {stats['total_size_mb']} MB")
    
    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    test_all_analyzers()
