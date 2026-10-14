# Kế hoạch Triển khai Di chuyển: Vnstock → TradingView API (Hybrid Model)

**Phiên bản:** 1.0  
**Ngày tạo:** 2026-10-03  
**Phạm vi:** Thay thế các lời gọi `vnstock`/`vnstock_data`/`vnstock_ta` bằng `TradingView API` cho những dữ liệu mà TradingView hỗ trợ tương đương hoặc vượt trội.  
**Loại trừ khỏi phạm vi này:** Dữ liệu dòng tiền Khối ngoại (`foreign_flow`, `foreign_trade`) và Tự doanh (`prop_trade`) — sẽ được thiết kế riêng ở giai đoạn sau.

---

## 1. Kiểm toán & Ánh xạ (Audit & Mapping)

### 1.1. Tổng quan thống kê lời gọi hiện tại

| File | Số lượng import vnstock/vnstock_data/vnstock_ta | Ghi chú |
|:---|:---:|:---|
| `dashboard/sync_service.py` | ~15 lời gọi động (inside hàm) | File trung tâm, phức tạp nhất |
| `dashboard/analyzers/stock_analyzer.py` | ~8 lời gọi | Analyzer đơn cổ phiếu |
| `dashboard/runners.py` | ~25 lời gọi | Wrapper mọi loại tài sản |
| `dashboard/views.py` | ~8 lời gọi | Các endpoint Django |
| `dashboard/analyzers/crypto_analyzer.py` | 2 lời gọi | Crypto |
| `dashboard/analyzers/forex_analyzer.py` | 4 lời gọi | Forex/Tỷ giá |
| `dashboard/analyzers/futures_analyzer.py` | 5 lời gọi | Phái sinh |
| `dashboard/analyzers/fund_analyzer.py` | 4 lời gọi | Chứng chỉ quỹ |
| `dashboard/analyzers/index_analyzer.py` | 2 lời gọi | Index |
| `dashboard/analyzers/bond_analyzer.py` | 2 lời gọi | Trái phiếu |

---

### 1.2. Bảng Ánh xạ Chi tiết Từng Lời gọi

#### NHÓM A: Dữ liệu OHLCV Lịch sử (Thay thế được 100%)

| File | Dòng | Hàm vnstock hiện tại | Dữ liệu | Lời gọi TradingView thay thế |
|:---|:---:|:---|:---|:---|
| `sync_service.py` | 3828–3843 | `vnstock_data.Market().equity(sym).ohlcv(start, end)` | Giá ngày cổ phiếu VN | `getCandles({ symbol: 'HOSE:SSI', timeframe: 'D', count: 250 })` |
| `sync_service.py` | 3848–3860 | `vnstock.Quote(sym, 'vci').history(start, end, interval='1D')` | Giá ngày (fallback) | `getCandles({ symbol: 'HOSE:SSI', timeframe: 'D' })` |
| `sync_service.py` | 4009–4015 | `vnstock.Quote(sym).history(...)` | Giá ngày, chiến lược backtest | `getCandles(...)` |
| `sync_service.py` | 4512–4520 | `vnstock.Quote(sym).history(...)` | Giá ngày, diagnosis | `getCandles(...)` |
| `stock_analyzer.py` | 226–251 | `vnstock_data.Market().equity(sym).ohlcv(...)` | OHLCV cho TA | `getCandles(...)` |
| `stock_analyzer.py` | 259–280 | `vnstock.explorer.vci.quote.Quote(...).history(...)` | OHLCV fallback | Bỏ fallback, TV là primary |
| `views.py` | 1627–1656 | `vnstock_data.Market().equity(sym).ohlcv(...)` | WealthGuard backtest | `getCandles(...)` |
| `views.py` | 1462–1493 | `get_stock_data_from_vnstock(...)` | Strategy Lab | `getCandles(...)` |
| `analyzers/crypto_analyzer.py` | 131 | `vnstock_data.Market().crypto(sym).ohlcv(...)` | Crypto OHLCV | `getCandles({ symbol: 'BINANCE:BTCUSDT', timeframe: 'D' })` |
| `analyzers/forex_analyzer.py` | 110–174 | `vnstock_data.Market().fx(sym).ohlcv(...)` | Forex OHLCV | `getCandles({ symbol: 'FX:EURUSD', timeframe: 'D' })` |
| `analyzers/futures_analyzer.py` | 154–182 | `vnstock_data.Market().equity(sym).ohlcv(...)` | Phái sinh OHLCV | `getCandles({ symbol: 'HNX:VN30F1M', timeframe: 'D' })` |
| `analyzers/fund_analyzer.py` | 87–169 | `vnstock_data.Market().etf(sym).ohlcv(...)` | ETF/Quỹ NAV | `getCandles({ symbol: 'HOSE:E1VFVN30', timeframe: 'D' })` |
| `analyzers/index_analyzer.py` | 112–228 | `vnstock_data.Market().index(sym).ohlcv(...)` | VN-Index/VN30 | `getCandles({ symbol: 'HOSE:VNINDEX', timeframe: 'D' })` |
| `runners.py` | 772–801 | `vnstock.explorer.vci.quote.Quote.history(...)` | Giá ngày (các hàm tool) | `getCandles(...)` |
| `runners.py` | 885 | `vnstock.explorer.msn.quote.Quote(...)` | Giá quốc tế | `getCandles({ symbol: 'NASDAQ:AAPL' })` |
| `sync_service.py` | 1252–1265 | `vnstock_data.Quote().history(symbol='VNINDEX', ...)` | VN-Index RS calculation | `getCandles({ symbol: 'HOSE:VNINDEX', timeframe: 'D' })` |

#### NHÓM B: Chỉ báo Kỹ thuật (Thay thế được 100%)

| File | Dòng | Hàm vnstock_ta hiện tại | Chỉ báo | Hàm TradingView thay thế |
|:---|:---:|:---|:---|:---|
| `sync_service.py` | 3593–3803 | `vnstock_ta.Indicator(df).rsi(14)` | RSI | `getIndicatorData({ indicator: 'STD;RSI', inputs: { length: 14 } })` |
| `sync_service.py` | 3604–3640 | `ind.adx(14)` | ADX + DI+/DI- | `getIndicatorData({ indicator: 'STD;ADX' })` |
| `sync_service.py` | 3641–3660 | `ind.macd(...)` | MACD + Signal | `getIndicatorData({ indicator: 'STD;MACD' })` |
| `sync_service.py` | 3661–3690 | `ind.bollinger_bands(...)` | BB Upper/Mid/Lower | `getIndicatorData({ indicator: 'STD;Bollinger_Bands' })` |
| `sync_service.py` | 3691–3720 | `ind.sma(10/20/50/200)` | SMA đa khung | `getIndicatorData({ indicator: 'STD;MA' })` |
| `sync_service.py` | 3720–3750 | *Tự tính (manual)* | VWAP | `getIndicatorData({ indicator: 'STD;VWAP' })` |
| `sync_service.py` | 3767–3788 | *Tự tính (manual)* | Ichimoku Tenkan/Kijun | `getIndicatorData({ indicator: 'STD;Ichimoku_Cloud' })` |
| `sync_service.py` | 3791–3798 | *Tự tính (manual)* | SuperTrend | `getIndicatorData({ indicator: 'STD;Supertrend' })` |
| `sync_service.py` | *manual* | *Tự tính CMF* | CMF | `getIndicatorData({ indicator: 'STD;CMF' })` |
| `sync_service.py` | *manual* | *Tự tính MFI* | MFI | `getIndicatorData({ indicator: 'STD;MFI' })` |
| `stock_analyzer.py` | 309–440 | `vnstock_ta.Indicator(df).*` | RSI, MACD, ADX, BB, SuperTrend | Toàn bộ thay bằng TV API |
| `crypto/forex/futures_analyzer.py` | ~195/274/-- | `vnstock_ta.Indicator(df).*` | TA chung | Thay bằng TV API |

#### NHÓM C: Danh sách Mã & Thông tin Tham chiếu (Thay thế một phần)

| File | Dòng | Hàm vnstock hiện tại | Dữ liệu | Quyết định |
|:---|:---:|:---|:---|:---|
| `runners.py` | 896, 924, 971, 1030 | `Listing.all_symbols()`, `Listing.indices()` | Danh sách mã HOSE/HNX | `searchMarkets(...)` của TV **hoặc giữ vnstock** (ít quan trọng) |
| `sync_service.py` | 368 | `vnstock_data.Reference` + `Market` | Danh sách HOSE đầy đủ | Dùng `searchMarkets` của TV |
| `runners.py` | 713–744 | `vnstock_data.Reference` | 4 loại tài sản lookup | Thay bằng `searchMarkets` |
| `bond_analyzer.py` | 100–274 | `vnstock_data.Reference` / `Listing` | Danh sách trái phiếu | **Giữ lại vnstock** (TV không có trái phiếu VN) |

#### NHÓM D: Dữ liệu Tài chính & Định giá Cơ bản (KHÔNG thay thế được)

| File | Dòng | Hàm vnstock hiện tại | Dữ liệu | Quyết định |
|:---|:---:|:---|:---|:---|
| `sync_service.py` | 637–738 | `vnstock_data.Fundamental`, `vnstock.Finance` | ROE, PE, PB, dữ liệu BCTC cho F-Score | **BẮT BUỘC giữ lại** |
| `sync_service.py` | 1323, 1472 | `vnstock_data.Fundamental` | Fundamental cho RS Score | **BẮT BUỘC giữ lại** |
| `stock_analyzer.py` | 793–960 | `vnstock_data.Fundamental` | BCTC quý, ROE, FCF | **BẮT BUỘC giữ lại** |
| `views.py` | 2079–2169 | `vnstock_data.Finance`, `vnstock.Finance` | Nạp BCTC quý vào DB | **BẮT BUỘC giữ lại** |
| `sync_service.py` | 1463–1655 | `calculate_f_score()` | Tự tính F-Score từ dữ liệu thô vnstock | **BẮT BUỘC giữ lại** (hệ thống tự tính) |
| `sync_service.py` | 1299–1460 | `calculate_profit_growth()` | Tính tăng trưởng lợi nhuận QoQ/YoY | **BẮT BUỘC giữ lại** |

#### NHÓM E: Dữ liệu Hàng hóa & Tỷ giá đặc thù VN (KHÔNG thay thế được)

| File | Dòng | Hàm vnstock hiện tại | Dữ liệu | Quyết định |
|:---|:---:|:---|:---|:---|
| `runners.py` | 936–945 | `vnstock.explorer.misc.gold_price.btmc_goldprice` | Giá vàng SJC/DOJI nội địa | **Giữ lại** (TV chỉ có vàng thế giới) |
| `forex_analyzer.py` | 144–215 | `vnstock.explorer.misc.exchange_rate.vcb_exchange_rate` | Tỷ giá VCB (USD/VND) | Có thể thay bằng `HOSE:USDVND` nếu TV có |
| `runners.py` | 1017 | `vcb_exchange_rate` | Tỷ giá VCB | Xem xét |
| `gold_analyzer.py` | — | `vnstock_data.CommodityPrice` | Giá vàng tổng hợp | **Giữ lại** cho SJC; TV cho XAUUSD |

#### NHÓM F: Tin tức & Công bố (KHÔNG thay thế được)

| File | Dòng | Hàm vnstock hiện tại | Dữ liệu | Quyết định |
|:---|:---:|:---|:---|:---|
| `stock_analyzer.py` | 1085 | `vnstock_news.EnhancedNewsCrawler` | Tin tức doanh nghiệp VN | **Giữ lại** (TV không có) |
| `runners.py` | 858, 1116, 1129 | `vnstock.News`, `vnstock_news`, `Disclosure` | Tin tức, công bố thông tin | **Giữ lại** |

---

## 2. Năng lực TradingView API Cần Khai thác

### 2.1. Bản đồ Symbol VN cho TradingView

| Loại tài sản | Ví dụ mã VN | Định dạng TV | Nguồn TV |
|:---|:---|:---|:---|
| Cổ phiếu HOSE | `SSI`, `VCB`, `HPG` | `HOSE:SSI`, `HOSE:VCB` | TV Vietnam feed |
| Cổ phiếu HNX | `SHS`, `VGS` | `HNX:SHS` | TV Vietnam feed |
| Cổ phiếu UPCOM | `OIL`, `MVN` | `UPCOM:OIL` | TV Vietnam feed |
| VN-Index | `VNINDEX` | `HOSE:VNINDEX` | TV Vietnam feed |
| VN30 | `VN30` | `HOSE:VN30` | TV Vietnam feed |
| Phái sinh VN30 | `VN30F1M` | `HNX:VN30F1M` | TV Vietnam feed |
| ETF VN | `E1VFVN30` | `HOSE:E1VFVN30` | TV Vietnam feed |
| Crypto | `BTCUSDT` | `BINANCE:BTCUSDT` | TV Crypto feed |
| Forex | `EURUSD` | `FX:EURUSD` | TV Forex feed |
| Vàng thế giới | `XAUUSD` | `OANDA:XAUUSD` | TV Commodities |

### 2.2. Khung thời gian (Timeframe) hỗ trợ

| Khung | Tham số TV | Ghi chú |
|:---|:---|:---|
| 1 phút | `'1'` | Chỉ có vài ngày gần nhất với tài khoản free |
| 5 phút | `'5'` | Intraday ngắn |
| 15 phút | `'15'` | Intraday |
| 1 giờ | `'60'` | Intraday |
| Ngày | `'D'` | **Chủ yếu dùng cho hệ thống này** |
| Tuần | `'W'` | Phân tích trung hạn |
| Tháng | `'M'` | Phân tích dài hạn |

### 2.3. Danh sách Indicators TV API có thể gọi

```js
// Một số mã indicator chuẩn của TradingView
'STD;RSI'                  // RSI (14)
'STD;MACD'                 // MACD (12, 26, 9)
'STD;ADX'                  // ADX + DI+/DI- (14)
'STD;Bollinger_Bands'       // BB (20, 2)
'STD;MA'                   // Moving Average (SMA/EMA)
'STD;VWAP'                 // Volume Weighted Average Price
'STD;Supertrend'           // SuperTrend (ATR-based)
'STD;Ichimoku_Cloud'        // Ichimoku (9, 26, 52)
'STD;CMF'                  // Chaikin Money Flow
'STD;MFI'                  // Money Flow Index
'STD;ATR'                  // Average True Range
```

---

## 3. Các Bước Di chuyển Theo Giai đoạn (Phased Migration)

### Phase 0: Cơ sở hạ tầng — Xây dựng TV Data Service (Node.js)

**Mục tiêu:** Tạo một REST microservice Node.js trả về JSON chuẩn hóa cho Python Django gọi.

**Thực hiện:**

1. Tạo file `tv_service/server.js`:

```js
// tv_service/server.js
import express from 'express';
import { getCandles, getIndicatorData, getQuote } from '@mathieuc/tradingview/data';

const app = express();
app.use(express.json());

// Endpoint 1: Lấy OHLCV
app.get('/candles', async (req, res) => {
  const { symbol, timeframe = 'D', count = 250 } = req.query;
  try {
    const candles = await getCandles({ symbol, timeframe, count: parseInt(count) });
    // Chuẩn hóa: thêm giá trị * 1000 cho cổ phiếu VN (nếu cần)
    res.json({ ok: true, data: candles });
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

// Endpoint 2: Lấy Indicators
app.post('/indicators', async (req, res) => {
  const { symbol, indicator, timeframe = 'D' } = req.body;
  try {
    const result = await getIndicatorData({ symbol, indicator });
    res.json({ ok: true, data: result.values });
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

// Endpoint 3: Quote real-time
app.get('/quote', async (req, res) => {
  const { symbol } = req.query;
  try {
    const q = await getQuote(symbol);
    res.json({ ok: true, data: q });
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

app.listen(7788, () => console.log('TV Service running on :7788'));
```

2. Tạo Python client wrapper `dashboard/tv_client.py`:

```python
# dashboard/tv_client.py
import requests
from typing import Optional
import pandas as pd

TV_SERVICE_URL = "http://localhost:7788"

# Mapping Sàn → Prefix TradingView
EXCHANGE_MAP = {
    'HOSE': 'HOSE',
    'HNX': 'HNX',
    'UPCOM': 'UPCOM',
}

def to_tv_symbol(symbol: str, exchange: str = 'HOSE') -> str:
    """Chuyển mã VN sang định dạng TradingView."""
    return f"{EXCHANGE_MAP.get(exchange.upper(), 'HOSE')}:{symbol.upper()}"


def get_ohlcv(
    symbol: str,
    exchange: str = 'HOSE',
    timeframe: str = 'D',
    count: int = 250,
) -> Optional[pd.DataFrame]:
    """
    Lấy OHLCV từ TradingView Service.
    
    Returns:
        DataFrame với index là datetime (Asia/Ho_Chi_Minh),
        cột: open, high, low, close, volume
    """
    tv_sym = to_tv_symbol(symbol, exchange)
    try:
        r = requests.get(
            f"{TV_SERVICE_URL}/candles",
            params={"symbol": tv_sym, "timeframe": timeframe, "count": count},
            timeout=10
        )
        data = r.json()
        if not data.get('ok'):
            return None
        
        df = pd.DataFrame(data['data'])
        # Chuẩn hóa thời gian: UNIX seconds UTC → datetime Asia/HCM
        df['time'] = pd.to_datetime(df['time'], unit='s', utc=True) \
                       .dt.tz_convert('Asia/Ho_Chi_Minh') \
                       .dt.tz_localize(None)
        df.set_index('time', inplace=True)
        df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        return df
    except Exception as e:
        print(f"[TV Client] get_ohlcv error for {symbol}: {e}")
        return None


def get_indicators(symbol: str, exchange: str = 'HOSE', indicator: str = 'STD;RSI') -> Optional[dict]:
    """Lấy giá trị Indicator từ TradingView."""
    tv_sym = to_tv_symbol(symbol, exchange)
    try:
        r = requests.post(
            f"{TV_SERVICE_URL}/indicators",
            json={"symbol": tv_sym, "indicator": indicator, "timeframe": "D"},
            timeout=15
        )
        data = r.json()
        return data.get('data') if data.get('ok') else None
    except Exception as e:
        print(f"[TV Client] get_indicators error: {e}")
        return None
```

---

### Phase 1: Di chuyển `analyze_stock()` — Dữ liệu OHLCV (Ưu tiên cao nhất)

**Hàm bị thay thế:** `vnstock_data.Market().equity(sym).ohlcv(...)` tại `sync_service.py:3828`  
**Thay thế bằng:** `tv_client.get_ohlcv(symbol)`

**Trước (vnstock):**
```python
from vnstock_data import Market
mkt = Market()
df = mkt.equity(symbol).ohlcv(
    start=(datetime.now() - pd.Timedelta(days=250)).strftime("%Y-%m-%d"),
    end=datetime.now().strftime("%Y-%m-%d")
)
# Xử lý price_multiplier = 1000
```

**Sau (TradingView):**
```python
from dashboard.tv_client import get_ohlcv
df = get_ohlcv(symbol, exchange='HOSE', timeframe='D', count=250)
# Không cần nhân * 1000 — TV trả về giá đầy đủ theo VND
```

**Logic chuyển đổi cần thiết:**

| Bước | Hành động |
|:---|:---|
| Xóa `price_multiplier = 1000` | TV trả về giá nguyên VND (ví dụ: 26400.0, không phải 26.4) |
| Kiểm tra tên cột | TV trả `open, high, low, close, volume` — khớp tên hiện tại |
| Index | TV → datetime `Asia/HCM` (đã xử lý trong client) |
| Fallback | Nếu TV Service down: thử `vnstock.Quote(sym).history()` như cũ |

---

### Phase 2: Di chuyển `calculate_technical_indicators()` — Chỉ báo TA

**Hàm bị thay thế:** Toàn bộ logic trong `sync_service.py:3531–3804` dùng `vnstock_ta.Indicator`  
**Thay thế bằng:** `tv_client.get_indicators()` cho từng chỉ báo

**Chiến lược:** Giữ nguyên schema output `result = {...}`, chỉ thay nguồn tính toán.

```python
def calculate_technical_indicators_tv(df: pd.DataFrame, symbol: str, exchange: str = 'HOSE') -> Dict[str, Any]:
    """
    Phiên bản mới: Lấy indicators từ TradingView thay vì tự tính bằng vnstock_ta.
    Input df vẫn cần thiết để tính các giá trị đơn giản (price, volume_ratio).
    Output schema: GIỮ NGUYÊN 100% so với calculate_technical_indicators() cũ.
    """
    from dashboard.tv_client import get_indicators

    result = { /* ... giữ nguyên dict cũ ... */ }

    # Tính nhanh từ df (không cần TV)
    result['price'] = float(df['close'].iloc[-1])
    result['volume'] = int(df['volume'].iloc[-1])
    result['change_percent'] = ...
    result['volume_ratio'] = ...

    # RSI từ TV
    rsi_data = get_indicators(symbol, exchange, 'STD;RSI')
    if rsi_data:
        result['rsi'] = round(float(rsi_data[-1]['RSI']), 1)

    # MACD từ TV
    macd_data = get_indicators(symbol, exchange, 'STD;MACD')
    if macd_data:
        result['macd'] = float(macd_data[-1]['MACD'])
        result['macd_signal'] = float(macd_data[-1]['Signal'])

    # ADX từ TV
    adx_data = get_indicators(symbol, exchange, 'STD;ADX')
    if adx_data:
        result['adx'] = float(adx_data[-1]['ADX'])

    # Bollinger Bands từ TV
    bb_data = get_indicators(symbol, exchange, 'STD;Bollinger_Bands')
    # ... map các trường tương ứng

    # SuperTrend, Ichimoku, VWAP, CMF, MFI tương tự

    return result
```

---

### Phase 3: Di chuyển các Analyzer phụ trợ

Áp dụng `get_ohlcv()` vào lần lượt:

| Analyzer | Thay đổi chính |
|:---|:---|
| `crypto_analyzer.py` | `vnstock_data.Market().crypto(sym).ohlcv()` → `get_ohlcv(sym, exchange='BINANCE')` |
| `forex_analyzer.py` | `vnstock_data.Market().fx(sym).ohlcv()` → `get_ohlcv(sym, exchange='FX')` |
| `futures_analyzer.py` | `vnstock_data.Market().equity(sym).ohlcv()` → `get_ohlcv(sym, exchange='HNX')` |
| `fund_analyzer.py` | `vnstock_data.Market().etf(sym).ohlcv()` → `get_ohlcv(sym, exchange='HOSE')` |
| `index_analyzer.py` | `vnstock_data.Market().index('VNINDEX').ohlcv()` → `get_ohlcv('VNINDEX', exchange='HOSE')` |
| `runners.py` | Mọi `Quote.history()` → `get_ohlcv()` |

---

### Phase 4: Di chuyển VNINDEX RS Calculation (sync_service.py:1252)

**Trước:**
```python
from vnstock_data import Quote
quote_vn = Quote()
vn_from_api = quote_vn.history(symbol='VNINDEX', length='30D', interval='1D')
```

**Sau:**
```python
from dashboard.tv_client import get_ohlcv
vn_from_api = get_ohlcv('VNINDEX', exchange='HOSE', timeframe='D', count=30)
```

---

## 4. Hợp đồng Dữ liệu (Data Contracts)

Schema chuẩn hóa mà lớp TV Data phải xuất ra (tương thích ngược hoàn toàn với pipeline hiện tại):

### 4.1. OHLCV DataFrame

```python
# Schema bắt buộc đầu ra của get_ohlcv()
pd.DataFrame(
    index=pd.DatetimeIndex,          # dtype: datetime64[ns], KHÔNG có timezone
                                     # (đã convert về Asia/HCM và strip tz)
                                     # name: 'time'
    data={
        'open':   float64,           # VND đầy đủ (VD: 26400.0)
        'high':   float64,           # VND đầy đủ
        'low':    float64,           # VND đầy đủ
        'close':  float64,           # VND đầy đủ
        'volume': float64,           # Khối lượng (đơn vị: cổ phiếu)
    }
)
```

### 4.2. Technical Indicators Dict

```python
# Schema bắt buộc của calculate_technical_indicators() — không thay đổi
{
    "price":              float,   # Giá đóng cửa mới nhất (VND)
    "change_percent":     float,   # % thay đổi so với phiên trước
    "volume":             int,     # Khối lượng phiên mới nhất
    "rsi":                float,   # RSI(14), range 0-100
    "mfi":                float,   # MFI(14), range 0-100
    "adx":                float,   # ADX(14)
    "plus_di":            float,   # DI+ (14)
    "minus_di":           float,   # DI- (14)
    "cmf":                float,   # CMF, range -1 to 1
    "sma_10":             float,   # SMA(10) giá VND
    "sma_20":             float,   # SMA(20) giá VND
    "sma_50":             float,   # SMA(50) giá VND
    "sma_200":            float,   # SMA(200) giá VND
    "bb_upper":           float,   # Bollinger Band Upper
    "bb_middle":          float,   # Bollinger Band Middle
    "bb_lower":           float,   # Bollinger Band Lower
    "bb_percent":         float,   # %B, range 0-100
    "macd":               float,   # MACD line
    "macd_signal":        float,   # Signal line
    "atr":                float,   # ATR(14)
    "vwap":               float,   # VWAP giá VND
    "vwap_status":        str,     # "bullish" | "bearish" | "neutral"
    "ichimoku_tenkan":    float,   # Tenkan-sen
    "ichimoku_kijun":     float,   # Kijun-sen
    "ichimoku_status":    str,     # "bullish" | "bearish" | "neutral"
    "supertrend":         float,   # SuperTrend value
    "supertrend_signal":  str,     # "bullish" | "bearish"
    "volume_ratio":       float,   # Vol hiện tại / Vol TB 20 phiên
}
```

---

## 5. Chiến lược Kiểm thử & Xác nhận (Testing & Validation)

### 5.1. Shadow Mode (Chạy song song)

Chạy 2 nguồn dữ liệu đồng thời trong giai đoạn chuyển tiếp. Ghi log sai lệch:

```python
def analyze_stock_with_shadow(symbol: str, ...) -> Dict:
    """Shadow mode: chạy cả vnstock và TV, so sánh kết quả."""
    # Nguồn cũ
    df_vnstock = get_ohlcv_vnstock(symbol)
    tech_old = calculate_technical_indicators(df_vnstock)

    # Nguồn mới
    df_tv = get_ohlcv(symbol)
    tech_new = calculate_technical_indicators_tv(df_tv, symbol)

    # So sánh & log sai lệch
    _log_deviation(symbol, tech_old, tech_new)

    # Trả về kết quả của nguồn cũ (chưa cutover)
    return tech_old
```

### 5.2. Ngưỡng sai lệch chấp nhận được

| Chỉ số | Ngưỡng sai lệch tối đa | Lý do |
|:---|:---:|:---|
| `close` (giá) | ±0.01% | Phải khớp gần như tuyệt đối |
| `rsi` | ±1.0 điểm | Do chênh lệch ngày dữ liệu |
| `macd` | ±0.5% tương đối | Tham số mặc định có thể khác |
| `adx` | ±2.0 điểm | ADX nhạy cảm với lookback |
| `sma_50` | ±0.05% | Gần như tuyệt đối |
| `bb_upper/lower` | ±0.5% | Do multiplier |

### 5.3. Test cases tối thiểu phải pass trước cutover

```python
# test_tv_migration.py

def test_ohlcv_schema():
    """Kiểm tra schema DataFrame đầu ra đúng kiểu dữ liệu."""
    df = get_ohlcv('SSI', 'HOSE')
    assert df is not None
    assert list(df.columns) == ['open', 'high', 'low', 'close', 'volume']
    assert df.index.dtype == 'datetime64[ns]'
    assert df['close'].iloc[-1] > 1000  # Giá VND, không phải ÷1000

def test_indicators_schema():
    """Kiểm tra dict indicators có đủ 17 key."""
    tech = calculate_technical_indicators_tv(df, 'SSI')
    required_keys = ['rsi', 'macd', 'adx', 'sma_50', 'bb_upper', 'supertrend', ...]
    for k in required_keys:
        assert k in tech, f"Thiếu key: {k}"

def test_price_deviation_vs_vnstock():
    """Giá TV không được lệch quá 0.01% so với vnstock."""
    close_tv = get_ohlcv('SSI')['close'].iloc[-1]
    close_vn = get_ohlcv_vnstock('SSI')['close'].iloc[-1]
    deviation = abs(close_tv - close_vn) / close_vn * 100
    assert deviation < 0.01, f"Lệch quá: {deviation:.4f}%"

def test_rsi_deviation():
    """RSI TV không lệch quá 1 điểm so với vnstock_ta."""
    ...
```

---

## 6. Rủi ro & Phương án Dự phòng (Risk & Fallback)

### 6.1. Bảng Rủi ro & Khoảng trống

| Rủi ro | Mức độ | Khoảng trống cụ thể | Phương án dự phòng |
|:---|:---:|:---|:---|
| **Tỷ giá VCB nội địa** | Thấp | TV có `HOSE:USDVND` nhưng không phải tỷ giá ngân hàng thực tế. Với `forex_analyzer.py` cần tỷ giá chuyển khoản VCB | Giữ nguyên `vcb_exchange_rate()` từ vnstock |
| **Vàng SJC/DOJI** | Thấp | TV chỉ có `XAUUSD` (vàng thế giới). Giá vàng nội địa SJC/DOJI là đặc thù VN | Giữ nguyên `btmc_goldprice()` từ vnstock |
| **Chứng chỉ quỹ mở nội địa (Fmarket)** | Trung bình | TV không có NAV của quỹ VCBF, SSIAM... | Giữ nguyên `vnstock.explorer.fmarket.Fund` |
| **Trái phiếu Chính phủ VN** | Cao | TV không có bảng giá trái phiếu HNX | Giữ nguyên vnstock `Listing` + `bond_analyzer` |
| **TV Service Down** | Trung bình | Microservice Node.js offline | Auto-fallback: thử `vnstock.Quote.history()` |
| **Rate Limit TV** | Thấp | TV không giới hạn như vnstock CTCK | Thêm cache Redis 5 phút cho candle data |
| **Mã cổ phiếu mới niêm yết** | Thấp | TV có thể chậm hơn vài ngày | Dùng `searchMarkets()` để xác minh mã tồn tại |

### 6.2. Cơ chế Fallback Tự động

```python
# dashboard/tv_client.py

def get_ohlcv_with_fallback(symbol: str, exchange: str = 'HOSE', **kwargs) -> Optional[pd.DataFrame]:
    """
    Ưu tiên TradingView, tự động fallback sang vnstock nếu thất bại.
    Ghi log để monitor tỷ lệ fallback.
    """
    import logging
    logger = logging.getLogger('tv_client')

    # Thử TradingView trước
    df = get_ohlcv(symbol, exchange, **kwargs)
    if df is not None and len(df) > 20:
        return df

    # Fallback sang vnstock
    logger.warning(f"[TV Fallback] {symbol}: TV failed, using vnstock")
    try:
        from vnstock.api.quote import Quote
        q = Quote(source='vci', symbol=symbol)
        df_vn = q.history(start='2024-01-01', interval='1D')
        # ... normalize
        return df_vn
    except Exception as e:
        logger.error(f"[TV Fallback] {symbol}: Both sources failed: {e}")
        return None
```

### 6.3. Tiêu chí kích hoạt Fallback tự động

| Điều kiện | Hành động |
|:---|:---|
| TV Service không phản hồi trong 10 giây | Auto-fallback ngay lập tức |
| Tỷ lệ fallback > 20% trong 1 giờ | Gửi alert, kiểm tra service |
| Giá trả về lệch > 1% so với cache ngày hôm qua | Log cảnh báo, giữ nguyên giá cũ |

---

## 7. Tóm tắt Lộ trình Ưu tiên

```
Phase 0: Dựng TV Service (Node.js) + Python client        [1-2 ngày]
Phase 1: Thay OHLCV trong analyze_stock() + shadow mode   [1 ngày]
Phase 2: Validate shadow mode ≥ 3 ngày giao dịch          [3 ngày]
Phase 3: Thay indicators trong calculate_technical_*()    [1-2 ngày]
Phase 4: Thay OHLCV trong tất cả các Analyzers phụ        [1-2 ngày]
Phase 5: Cutover chính thức, xóa fallback vnstock_data    [1 ngày]
```

**Kết quả mong đợi sau migration:**
- Loại bỏ hoàn toàn `vnstock_data.Market()` và `vnstock_ta.Indicator` ra khỏi luồng TA.
- Tốc độ lấy dữ liệu nhanh hơn, không bị rate-limit từ phía CTCK VN.
- Chỉ báo kỹ thuật chính xác 100% như TradingView (nguồn chuẩn).
- Giữ nguyên `vnstock` cho: Fundamentals, F-Score (dữ liệu thô), Dòng tiền, Vàng SJC, Tỷ giá VCB, Quỹ mở, Trái phiếu, Tin tức.
