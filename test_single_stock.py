"""Test sync với 1 mã cổ phiếu"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vnstock_web.settings')

import django
django.setup()

from dashboard.sync_service import analyze_stock, get_market_rsi

print("=" * 60)
print("TEST SYNC - Lấy dữ liệu 1 mã cổ phiếu")
print("=" * 60)

# Lấy Market RSI
print("\n1. Lấy Market RSI...")
market_rsi = get_market_rsi()
print(f"   Market RSI: {market_rsi:.2f}")

# Test với 1 mã
symbol = "VCB"
print(f"\n2. Phân tích mã {symbol}...")

result = analyze_stock(symbol, market_rsi)

if result:
    print(f"\n3. KẾT QUẢ PHÂN TÍCH {symbol}:")
    print("-" * 50)
    print(f"   Giá hiện tại: {result['price']:,.0f} VND")
    print(f"   Thay đổi: {result['change_percent']:+.2f}%")
    print(f"   Volume Ratio: {result['volume_ratio']:.2f}")
    print()
    print(f"   RSI: {result['rsi']:.1f}")
    print(f"   ADX: {result['adx']:.1f}")
    print(f"   CMF: {result['cmf']:+.4f}")
    print(f"   MFI: {result['mfi']:.1f}")
    print(f"   ATR: {result['atr']:,.0f}")
    print()
    print(f"   SMA 10: {result['sma_10']:,.0f}")
    print(f"   SMA 20: {result['sma_20']:,.0f}")
    print(f"   SMA 50: {result['sma_50']:,.0f}")
    print()
    print(f"   VWAP: {result['vwap']:,.0f} ({result['vwap_status']})")
    print(f"   Ichimoku: {result['ichimoku_status']}")
    print(f"   SuperTrend: {result['supertrend_signal']}")
    print()
    print(f"   P/E: {result['pe']}")
    print(f"   P/B: {result['pb']}")
    print(f"   ROE: {result['roe']}")
    print(f"   F-Score: {result['f_score']}/9 ({result.get('f_score_grade', 'N/A')})")
    print()
    print(f"   Master Score: {result['master_score']}")
    print(f"   Technical Score: {result['technical_score']}")
    print(f"   Fundamental Score: {result['fundamental_score']}")
    print(f"   Signal: {result['signal']}")
    print(f"   Criteria Met: {result['criteria_met']}/12")
    print(f"   R:R Ratio: {result['risk_reward_ratio']:.2f}")
    print()
    print(f"   Entry: {result['entry_price']:,.0f}")
    print(f"   Stop Loss: {result['stop_loss']:,.0f}")
    print(f"   Take Profit: {result['take_profit']:,.0f}")
    print(f"   Est. Days: {result['estimated_days_to_target']:.1f}")
    print()
    print(f"   Is Vetoed: {result['is_vetoed']}")
    print(f"   Veto Reason: {result['veto_reason']}")
    print(f"   Is Fast Pick: {result['is_fast_pick']}")
    print(f"   Trend: {result['trend']}")
    print()
    print("   Criteria List:")
    for c in result.get('criteria_list', []):
        print(f"     - {c}")
else:
    print(f"   LỖI: Không lấy được dữ liệu cho {symbol}")

print("\n" + "=" * 60)
