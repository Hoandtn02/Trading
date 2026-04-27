# Lessons Learned - Trading Dashboard Development

**Created:** 2026-04-25
**Project:** Trading Dashboard with vnstock ecosystem

---

## 1. vnstock_data API Issues & Fixes

### 1.1 Price Data Scaling Issue
**Problem:** API returns prices divided by 1000
```
API returns: 60.6, 34.25, 27.9
Actual price: 60,600, 34,250, 27,900 VND
```

**Fix:** Multiply price columns by 1000 in `_get_ohlcv()`
```python
price_cols = ['open', 'high', 'low', 'close']
for col in price_cols:
    if col in df.columns:
        df[col] = df[col] * 1000
```

### 1.2 vnstock_ta v0.2.0 API Changes
**Problem:** Old class names no longer work
```
Old: vnstock_ta.MomentumIndicator, TrendIndicator, VolatilityIndicator
New: vnstock_ta.Indicator (unified class)
```

**Fix:** Use unified `Indicator` class
```python
from vnstock_ta import Indicator

ta = Indicator(df)
df['rsi'] = ta.rsi(period=14)
df['sma'] = ta.sma(period=20)
df['macd'] = ta.macd()
df['adx'] = ta.adx()
```

### 1.3 Fundamental Data Column Names
**Problem:** Column names differ from expected

**Debug approach:** Always print column names first
```python
ratios = fun.equity(symbol).ratio(limit=4)
print(f"Columns: {list(ratios.columns)}")
print(f"Last row: {ratios.tail(1)}")
```

**Key findings for VCB (banking):**
- `ratio()` returns: `['period', 'trailing_eps', 'book_value_per_share', 'pe', 'pb', 'dividend_yield', 'beta']`
- `income_statement()`: Columns = time periods, index = metric names
- `balance_sheet()`: Similar structure
- `cash_flow()`: Similar structure

### 1.4 Income Statement Column Access Pattern
**Problem:** Data structure is transposed
```
Old assumption: rows = time periods, columns = metrics
Actual: rows = metrics, columns = time periods
```

**Fix pattern:**
```python
# Get latest period (newest = index 0 based on debug)
latest_row = income.index[0]  # Or find by period value

# Get value
net_income = income.loc[latest_row, 'net_profit_after_tax']
```

### 1.5 Period Parameter
**Problem:** Used wrong parameter names
```
Wrong: period="annual"
Right: limit=N (number of periods)
```

**Correct usage:**
```python
income = fun.equity(symbol).income_statement(limit=8)  # 8 periods
ratio = fun.equity(symbol).ratio(limit=4)  # 4 periods
```

---

## 2. Testing Strategy

### 2.1 Always Verify with Real Data
Before assuming code works, verify:
1. Print actual data from API
2. Compare with known real values (e.g., stock prices)
3. Check data types and scales

### 2.2 Debug Script Pattern
Create separate debug scripts to test API calls:
```python
# debug_fundamental.py
def debug_fundamental():
    fun = Fundamental()
    ratios = fun.equity(symbol).ratio(limit=4)
    print(f"Columns: {list(ratios.columns)}")
    print(f"Data: {ratios.tail(1)}")
```

### 2.3 Quick Test Command
```powershell
& "$env:USERPROFILE\.venv\Scripts\python.exe" -c "import warnings; warnings.filterwarnings('ignore'); from module import func; print(func())"
```

---

## 3. Common Pitfalls

### 3.1 Silent Exception Catching
**Bad:** Silently catching exceptions hides bugs
```python
except Exception:
    pass  # Don't do this!
```

**Better:** Log or print errors
```python
except Exception as e:
    print(f"Error: {e}")
    # Then handle gracefully
```

### 3.2 Hardcoded Column Names
**Bad:** Assuming exact column names
```python
if 'pe' in ratios.columns:  # Works
if 'P/E' in ratios.columns:  # May not work
```

**Better:** Flexible column matching
```python
def find_col(df_cols, *names):
    for name in names:
        for col in df_cols:
            if name.lower() in col.lower():
                return col
    return None
```

### 3.3 Data Type Assumptions
Always check:
- Is value already float or string?
- Is percentage already converted (0.12 vs 12)?
- Is price already scaled?

---

## 4. vnstock_data Structure Reference

### 4.1 Module Import
```python
from vnstock_data import Market, Fundamental, Listing, Reference
```

### 4.2 Market Layer
```python
mkt = Market()
df = mkt.equity("VCB").ohlcv(start="2026-01-01", end="2026-04-24")
df = mkt.equity("VCB").quote()  # Real-time quote
```

### 4.3 Fundamental Layer
```python
fun = Fundamental()
ratios = fun.equity("VCB").ratio(limit=4)
income = fun.equity("VCB").income_statement(limit=8)
balance = fun.equity("VCB").balance_sheet(limit=8)
cashflow = fun.equity("VCB").cash_flow(limit=8)
health = fun.equity("VCB").financial_health(scorecard="auto")
```

### 4.4 vnstock_ta Usage (v0.2.0+)
```python
from vnstock_ta import Indicator

ta = Indicator(df)
df['rsi'] = ta.rsi(period=14)
df['sma_20'] = ta.sma(period=20)
df['sma_50'] = ta.sma(period=50)
df['macd'] = ta.macd()
df['adx'] = ta.adx()
df['atr'] = ta.atr(period=14)
df['bollinger_upper'], df['bollinger_mid'], df['bollinger_lower'] = ta.bollinger()
df['cmf'] = ta.cmf(period=20)
df['mfi'] = ta.mfi(period=14)
df['supertrend'] = ta.supertrend()
df['vwap'] = ta.vwap()
```

---

## 5. Error Handling Patterns

### 5.1 Safe Value Extraction
```python
def safe_get(df, col, row=0):
    try:
        if df is None or col not in df.columns:
            return None
        val = df.iloc[row][col] if isinstance(df.iloc[row], pd.Series) else df.loc[row, col]
        return float(val) if pd.notna(val) else None
    except:
        return None
```

### 5.2 Graceful Degradation
```python
def get_metric(data, fallbacks):
    for key in fallbacks:
        if key in data.columns:
            val = data[key]
            if pd.notna(val) and val != 0:
                return float(val)
    return None  # All fallbacks failed
```

---

## 6. Testing Workflow

### 6.1 Phase Test Template
```python
"""
Test script for Phase X - Component Name
Run: python -m tests.unit.analyzers.test_component
"""
import sys
sys.path.insert(0, r"d:\OneDrive\Desktop\Trading")

def test_component():
    print("=" * 60)
    print("Phase X Test: Component Name")
    print("=" * 60)
    
    # Test cases
    symbols = ["VCB", "TCB", "HPG"]
    
    for symbol in symbols:
        print(f"\nAnalyzing: {symbol}")
        try:
            result = analyze(symbol)
            print(result)
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    test_component()
```

### 6.2 Verification Checklist
- [ ] Price values match real market data
- [ ] All indicators calculated correctly
- [ ] No silent exceptions
- [ ] Error messages are descriptive
- [ ] Edge cases handled (empty data, missing columns)

---

## 7. Key Learnings Summary

1. **Always verify API output** before using - print columns, shapes, sample data
2. **Price scaling** - vnstock_data divides by 1000 for stocks, but NOT for indices (index values are in points)
3. **API version changes** - vnstock_ta v0.2.0 uses unified `Indicator` class
4. **Data structure** - Income/balance/cashflow have metrics as rows, periods as columns
5. **Parameter names** - Use `limit=N` not `period="annual"`
6. **Silent exceptions** are dangerous - always log errors
7. **Flexible column matching** - Use partial string matching for robustness
8. **Test with real data** - Don't assume values are correct
9. **Listing API returns different types** - `symbols_by_group()` returns Series, `symbols_by_exchange()` returns DataFrame
10. **Commodity API** - Use `CommodityPrice()` class for gold_vn, oil_crude, etc. with `length` parameter
11. **Futures interval** - Use `interval="1D"` (capital D) not `"1d"` for daily data
12. **Futures symbol conversion** - API automatically converts VN30F1M to KRX format internally

---

## 8. Files Created During Development

### Phase 1 - Stock Analyzer
- `tests/unit/analyzers/test_stock_analyzer.py` - Main test script
- `tests/unit/analyzers/debug_fundamental.py` - Debug fundamental API
- `tests/unit/analyzers/debug_fundamental2.py` - Debug data structure

### Phase 2 - Index Analyzer
- `tests/unit/analyzers/test_index_analyzer.py` - Index analyzer test script

### Phase 3 - Gold & Futures
- `tests/unit/analyzers/test_gold_futures_analyzer.py` - Gold & Futures test script

### Phase 4 - ETF, Forex, Crypto, CW
- `tests/unit/analyzers/test_phase4_analyzers.py` - Phase 4 test script

### Phase 5 - Unified Dashboard Runner
- `dashboard/dashboard_runner.py` - Unified runner với caching
- `tests/unit/analyzers/test_phase5_runner.py` - Phase 5 test script

### Key Patterns for Phase 5
1. **StockAnalyzer** uses `to_string()` method
2. **Other analyzers** use `format_output()` method
3. **CacheManager** stores in `~/.trading_dashboard/cache/`
4. **Batch processing** via `run_market_overview()`
5. **BondAnalyzer** uses `get_government_bonds_list()` for listing

---

## 9. References

- vnstock_data docs: `vnstock-agent-guide-main/docs/vnstock-data/`
- vnstock_ta docs: `vnstock-agent-guide-main/docs/vnstock_ta/`
- Architecture: `docs/ARCHITECTURE_ROADMAP.md`

---

## 10. Phase 1 Stock Analyzer Fixes (2026-04-26)

### 10.1 ADX Interpretation
**Critical Rule**: ADX < 20 = NO TREND (Sideway), NOT a strong trend
```
ADX < 20: SIDEWAY - No directional trend
ADX 20-25: Weak trend
ADX >= 25: Strong trend
ADX >= 40: Very strong trend
```

### 10.2 Stop Loss Logic
**For LONG/BUY positions**: Stop Loss MUST be BELOW current price
```
WRONG: SL = Price + ATR (above current price)
RIGHT: SL = Price - (ATR * multiplier)
```

### 10.3 Master Score vs Action Consistency
**Critical**: Master Score and Action must be aligned
```
High Score (>=70) + Strong Bullish signals = BUY
Medium Score (50-70) + Mixed signals = HOLD/WATCH
Low Score (<=40) + Bearish signals = SELL
```

### 10.4 vnstock_ta Crash Handling
**vnstock_ta can crash** in some environments. Always implement full manual fallback:
```python
def _calculate_technical_fallback(self, df: pd.DataFrame):
    # Calculate ALL indicators manually:
    # - RSI: 100 - (100 / (1 + RS))
    # - MACD: EMA(fast) - EMA(slow)
    # - ADX: Calculate +DI, -DI, DX, then ADX
    # - ATR: max(H-L, |H-PC|, |L-PC|).mean()
    # - Bollinger: SMA ± (std * 2)
    # - Ichimoku: Tenkan, Kijun, Span A/B
```

### 10.5 vnstock Fallback for OHLCV
When vnstock_data is unavailable:
```python
def _get_ohlcv_fallback(self, symbol):
    from vnstock.explorer.vci.quote import Quote
    q = Quote(symbol=symbol, show_log=False)
    df = q.history(start=start, end=end, interval='1D')
    # Prices are in thousands (26.40 = 26,400 VND)
    df[col] = df[col] * 1000
```

### 10.6 Parameter Name Consistency
When defining methods, be consistent with parameter names:
```python
# WRONG: Define with 'std_mult' but call with 'std'
def _calculate_bollinger(close, period=20, std_mult=2):  # Definition
bb_values = self._calculate_bollinger(close, period=20, std=2)  # Call - ERROR!

# RIGHT: Use consistent parameter name
def _calculate_bollinger(close, period=20, std_mult=2):  # Definition
bb_values = self._calculate_bollinger(close, period=20, std_mult=2)  # Call - OK
```

---

## 11. Phase 2 Index Analyzer Fixes (2026-04-26)

### 11.1 SMA(50) = 0 Issue
**Problem:** Dataset doesn't have enough rows to calculate SMA(50)
- 90 calendar days only gives ~60 trading days (excluding weekends)
- Need at least 50 trading days for SMA50 calculation

**Fix:** 
- Use 90 calendar days for index data (vs 60 for stocks)
- Add `sma_50_available` flag to check if SMA50 is valid
- Display "N/A" when SMA50 is not available

```python
# In IndexData dataclass
sma_50_available: bool = False  # Flag để check dữ liệu đủ 50 phiên

# In _calculate_index_indicators
if len(close) >= 50:
    data.sma_50 = float(close.rolling(50).mean().iloc[-1])
    data.sma_50_available = True
```

### 11.2 Logic Contradiction (Uptrend vs Sideway)
**Problem:** AI Insight says "Sideway" while Trend section says "Uptrend"

**Root Cause:** Two different logic paths for trend determination

**Fix:** Unify logic in both places:
```
ADX < 20: SIDEWAY (no clear trend)
ADX >= 20 AND Price > SMA20 AND > SMA50: UPTREND
ADX >= 20 AND Price < SMA20 AND < SMA50: DOWNTREND
Otherwise: SIDEWAY
```

### 11.3 Market Breadth Scope Label
**Problem:** Output shows "100 mã" but VNINDEX has ~400 stocks on HOSE

**Fix:** Add scope note to clarify data subset:
```
📊 MARKET BREADTH (~100 mã (VN100/Index subset))
```

### 11.4 Volume Comparison
**Problem:** Volume 673.9M is meaningless without comparison

**Fix:** Add 20-day average comparison:
```
Khối lượng: 673.9M (↓ 11% so với TB 20 phiên)
```

```python
# Calculate average volume
if 'volume' in df.columns and len(df) >= 20:
    data.avg_volume_20 = int(df['volume'].tail(20).mean())

# Format comparison
if data.avg_volume_20 > 0:
    vol_change_pct = ((data.volume - data.avg_volume_20) / data.avg_volume_20) * 100
    vol_change_str = f"(↑ {vol_change_pct:.0f}% so với TB 20 phiên)" if vol_change_pct > 0 else f"(↓ {abs(vol_change_pct):.0f}% so với TB 20 phiên)"
```

### 11.5 Test Script Path Error
**Problem:** Test script used wrong path `d:\OneDrive\Desktop\Trading` instead of `Trading-1`

**Fix:** Update test script path:
```python
sys.path.insert(0, r"d:\OneDrive\Desktop\Trading-1")  # CORRECT
# sys.path.insert(0, r"d:\OneDrive\Desktop\Trading")  # WRONG
```

### 11.6 Index vs Stock Price Scaling
**Important:** Index values are NOT divided by 1000 like stock prices
```
Stock: API returns 60.6 → Actual 60,600 VND (multiply by 1000)
Index: API returns 1853 → Actual 1853 points (keep as-is)
```

### 11.7 Master Score Override Rules
**Critical Problem:** RSI 83.7 + Breadth 19% was giving "KHẢ QUAN" - extremely dangerous!

**Fix:** Added override rules to cap score when dangerous conditions exist:

```python
# Rule 1: RSI > 75 + Breadth < 40% = "Xanh vỏ đỏ lòng"
if data.rsi > 75 and data.breadth_percent < 40:
    score = min(score, 40)  # Cap at 40

# Rule 2: RSI > 80 = Extreme overbought
if data.rsi > 80:
    score = min(score, 35)

# Rule 3: Volume weakening at high prices
if vol_change_pct < -10 and data.change_percent > 0 and data.rsi > 65:
    score = min(score, 45)  # Distribution pattern

# Rule 4: RSI < 25 = Extreme oversold
if data.rsi < 25:
    score = max(score, 60)  # Potential rebound
```

**New Output:**
```
VNINDEX: RSI 83.7 + Breadth 19%
→ Master Score: 35/100
→ Recommendation: TIÊU CỰC - Cắt lỗ hoặc chờ
→ Override: RSI cực đại quá mua
```

### 11.8 Master Score Display
**Added:** Master Score display in output header
```
║  🤖 AI INSIGHT: 35/100 ★☆☆☆ 
║     Khuyến nghị: TIÊU CỰC - Cắt lờ hoặc chờ
```

### 11.9 Volume Weakening Insight
**Added:** Volume analysis insight for distribution pattern
```
⚠️ Vol giảm 11% ở vùng cao → Phân phối, cẩn trọng!
```

### 11.10 Weighted Scoring System
**New scoring approach:**
```
TREND COMPONENT (60%):
- ADX >= 40: +20 (Very strong)
- ADX >= 25: +15 (Strong)
- Price > SMA20 & > SMA50: +15 (Bullish position)

BREADTH COMPONENT (40%):
- RSI > 75: -20 (Extreme overbought)
- RSI > 70: -10 (Overbought)
- Breadth <= 25: -20 (Extreme bearish)
- Breadth <= 40: -10 (Bearish)

FINAL MAPPING:
- 75+: TÍCH CỰC
- 60-74: KHẢ QUAN
- 50-59: TRUNG LẬP
- 40-49: THẬN TRỌNG
- 25-39: TIÊU CỰC
- <25: NGUY HIỂM
```

### 11.11 Pillar Drag Detection (KÉO TRỤ)
**Critical:** Index up but Breadth < 35% = PILLAR DRAG - EXTREMELY DANGEROUS

```python
# RULE 0: PILLAR DRAG DETECTION
if data.breadth_percent < 35:
    if data.change_percent >= 0:
        # Index UP but most stocks DOWN = PILLAR DRAG
        score = min(score, 30)
        override_reason = "⚠️ KÉO TRỤ: Index lên nhưng chỉ {breadth}% mã tăng"
    elif data.change_percent > -1 and data.breadth_percent < 25:
        # Index flat/slight drop + very weak breadth = Warning
        score = min(score, 35)
        override_reason = "⚠️ KÉO TRỤ TIỀM ẨN: Chỉ {breadth}% mã tăng"
```

### 11.12 Override Message Format - Separate Breadth vs RSI
**Problem:** "KÉO TRỤ: RSI cực đại" mixes two different concepts

**Fix:** Separate Breadth (Kéo trụ) vs RSI (Động lượng)

```python
override_parts = []

# 1. Breadth warning (KÉO TRỤ)
if is_pillar_drag:
    override_parts.append("Breadth yếu ({:.0f}%) - Sự đồng thuận thấp".format(data.breadth_percent))

# 2. RSI warning (Động lượng)
if data.rsi > 80:
    override_parts.append("RSI Quá mua cực độ ({:.0f})".format(data.rsi))
elif data.rsi > 75 and not is_pillar_drag:
    override_parts.append("RSI Quá mua ({:.0f})".format(data.rsi))

# 3. Volume warning
if vol_change_pct < -10 and data.change_percent > 0 and data.rsi > 65:
    override_parts.append("Vol giảm ở vùng cao - Phân phối")

# Combine
if override_parts:
    override_reason = "⚠️ KÉO TRỤ: " + " | ".join(override_parts)
```

**Example Output:**
```
Override: ⚠️ KÉO TRỤ: Breadth yếu (19%) - Sự đồng thuận thấp | RSI Quá mua (84)
```

### 11.13 Enhanced AI Insight UI - Visual Hierarchy
**Improvement:** Add dedicated warning section with clear visual hierarchy

**New Structure:**
```
╠══════════════════════════════════════════════════════════════╣
║  AI INSIGHT: 30/100 *ooo 
║     Khuyen nghich: TIÊU CỰC - Cắt lỗ hoặc chờ
╠══════════════════════════════════════════════════════════════╣
║  ------------------------------------------------------------
║  [!] CANH BAO: PHAT HIEN KEO TRU (XANH VO DO LONG)
║  * 81% co phieu giam/di ngang du Index giam nhe.
║  * Phan ky nghiem trong: Tru giu gia - Midcap/Smallcap bi xa.
║  ------------------------------------------------------------
║  [X] Rui ro: Breadth 19% (Rat thap) -> Do tin cay Uptrend thap
║  [X] Rui ro: RSI 83.7 (Qua mua) -> Ap luc dieu chinh Cu lon
║  [X] Rui ro: Vol giam 11% -> Luc cay suy yeu o vung cao
║  [OK] Ky thuat: SMA & ADX van bao tang nhung bi "vo hieu hoa" 
╠══════════════════════════════════════════════════════════════╣
```

**Key Improvements:**
1. Score stars use `*` and `o` instead of Unicode stars (cross-platform compatibility)
2. Warning section clearly separated with visual divider
3. Each risk factor displayed with `[X]` (risk) or `[OK]` (confirmed) prefix
4. "Pillar Drag" warning includes:
   - Decline percentage (81% stocks down)
   - Index direction comparison
   - Phase divergence explanation
5. Technical signals marked as "vô hiệu hóa" when overridden

---

## 12. Phase 1 Stock Analyzer Fixes (2026-04-26)

### 12.1 Trend Label when ADX < 20
**Problem:** "Strong Uptrend (ADX: 19.4 - SIDEWAY)" is confusing

**Root Cause:** `_get_trend_status()` only considers price vs SMAs, not ADX

**Fix:** Override trend_status after calculation when ADX < 20

```python
# After calculating trend_status
if tech.adx and tech.adx < 20:
    tech.trend_status = "sideways"

# In display
trend_text = result.technical.trend_status.replace("_", " ").title()
if result.technical.adx and result.technical.adx < 20:
    trend_text = "SIDEWAY"  # ADX < 20 = No trend
```

**Result:**
```
Before: XU HƯỚNG: Strong Uptrend (ADX: 19.4 - SIDEWAY)
After:  XU HƯỚNG: SIDEWAY (ADX: 19.4 - Không xu hướng)
```

### 12.2 Banking Metrics (NIM/NPL)
**Problem:** Banking stocks show "Tăng trưởng LN: N/A"

**Fix:** Add banking-specific metrics (NIM, NPL) for bank stocks

```python
# In FundamentalData dataclass
nim: float = 0.0  # Net Interest Margin
npl_ratio: float = 0.0  # Non-Performing Loan ratio
is_banking: bool = False

# In display
if result.fundamental.is_banking and (result.fundamental.nim > 0 or result.fundamental.npl_ratio > 0):
    banking_parts = []
    if result.fundamental.nim > 0:
        banking_parts.append(f"NIM: {result.fundamental.nim:.2f}%")
    if result.fundamental.npl_ratio > 0:
        banking_parts.append(f"NPL: {result.fundamental.npl_ratio:.2f}%")
    lines.append(f"│     📊 Ngân hàng: {' | '.join(banking_parts)}...")
```

**Example Output for Bank:**
```
📊 Ngân hàng: NIM: 3.25% | NPL: 1.85%
```

## 13. Phase 3 Futures Analyzer Fixes (2026-04-26)

### 13.1 Zero Data Disaster - Insufficient Historical Data
**Problem:** Technical indicators (ATR, SMA, ADX, VWAP, Pivot) all return 0 because API only fetched ~30 periods

**Fix:** Increase data fetch period to 100+ days

```python
def __init__(self, period_ta: int = 100):
    self.period_ta = period_ta  # Need 100+ periods for valid indicators

# Get 100+ days for valid indicators
df = mkt.futures(contract).ohlcv(
    interval="1D",
    length=self.period_ta + 50
)
```

### 13.2 Manual Technical Indicators
**Problem:** Indicators using vnstock_ta library returned 0

**Fix:** Calculate indicators manually from OHLCV data

```python
# ATR (14) - Manual
tr = pd.concat([
    high - low,
    abs(high - close.shift(1)),
    abs(low - close.shift(1))
], axis=1).max(axis=1)
data.atr = float(tr.rolling(14).mean().iloc[-1])

# SMA(20) - Manual
data.sma_20 = float(close.rolling(20).mean().iloc[-1])

# ADX (14) - Manual
plus_dm = high.diff()
minus_dm = -low.diff()
# ... full ADX calculation ...

# RSI (14) - Manual
delta = close.diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
data.rsi = float(100 - (100 / (1 + rs)).iloc[-1])
```

### 13.3 Term Structure Logic - Backwardation is BEARISH
**Problem:** System showed Backwardation in "Ưu điểm" (Strengths) section - WRONG!

**Knowledge:** Backwardation means F1M > F2M > F3M (prices declining) = BEARISH signal

**Fix:**
```python
# Term structure determination
if data.current_price < data.futures_m2 < data.futures_m3:
    data.term_structure = "CONTANGO"
    data.term_signal = "Tín hiệu TĂNG - Thị trường kỳ vọng tích cực"
elif data.current_price > data.futures_m2 > data.futures_m3:
    data.term_structure = "BACKWARDATION"
    data.term_signal = "Tín hiệu GIẢM - Thị trường bi quan ngắn hạn"

# Score contribution
if data.term_structure == "CONTANGO":
    score += 5  # Bullish
elif data.term_structure == "BACKWARDATION":
    score -= 10  # Bearish - CORRECT!
```

**Display Fix:**
```python
# Ưu điểm - only show if bullish
if term_bullish:
    output += "• Contango - Kỳ vọng tích cực\n"

# Rủi ro - show Backwardation here
if data.term_structure == "BACKWARDATION":
    output += "• Backwardation - Cảnh báo giảm\n"
```

### 13.4 Trend Logic - Handle SMA=0 Cases
**Problem:** "Giá TRÊN cả 2 SMA → UPTREND" when SMA=0 is meaningless

**Fix:**
```python
# Only count trend if we have valid SMA data
if data.sma_20 > 0 and data.sma_50 > 0:
    if data.current_price > data.sma_20 and data.current_price > data.sma_50:
        score += 15
        data.trend = "UPTREND"
    else:
        data.trend = "CHƯA XÁC ĐỊNH"
```

### 13.5 Target/Stop Loss Based on ATR
**Problem:** Entry, SL, TP all returned 0 or nonsensical values

**Fix:**
```python
def _calculate_entry_exit(self, data: FuturesData):
    """Calculate Entry, Stop Loss, and Take Profit based on ATR"""
    if data.current_price > 0 and data.atr > 0:
        # For LONG positions
        data.stop_loss = data.current_price - 2 * data.atr
        data.take_profit = data.current_price + 3 * data.atr
        data.entry_target = data.current_price
    elif data.current_price > 0:
        # Fallback if ATR is 0
        data.stop_loss = data.current_price * 0.97
        data.take_profit = data.current_price * 1.03
```

**Example Output:**
```
📌 HÀNH ĐỘNG:
   • Mở vị thế quanh: 2,015
   • 🛑 Stop Loss: 1,942 (-73 điểm)
   • 🎯 Take Profit: 2,124 (+109 điểm)
```

### 13.6 Spot Proxy Fallback
**Problem:** Futures data API returns no data, all indicators fail

**Fix:** Use VN30 spot index as proxy for calculations
```python
def _get_spot_as_futures(self, data: FuturesData):
    """Use VN30 spot as proxy if futures data unavailable"""
    df = mkt.index("VN30").ohlcv(
        interval="1D",
        length=self.period_ta + 30
    )
    data.symbol = "VN30 (Spot Proxy)"
    data.current_price = float(df['close'].iloc[-1])
```

**Result (After Fix):**
```
=== Futures Data ===
Symbol: VN30F2606
ATR: 36.3 ✓
SMA20: 1925.56 ✓
SMA50: 1917.77 ✓
ADX: 53.6 ✓
RSI: 79.5 ✓
VWAP: 1916.68 ✓
Term Structure: N/A (F2M/F3M not available)
```
