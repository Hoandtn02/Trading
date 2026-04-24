# VNSTOCK INTELLIGENCE - ROADMAP & PROGRESS

> **Mục tiêu**: Xây dựng hệ thống phân tích đầu tư toàn diện sử dụng vnstock ecosystem
> **Ngày tạo**: 2026-04-24
> **Cập nhật lần cuối**: 2026-04-24
> **Trạng thái**: 🟡 Đang triển khai Phase 1

---

## 1. TỔNG QUAN HỆ THỐNG

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VNSTOCK INTELLIGENCE SYSTEM                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│  │ vnstock_data │    │ vnstock_ta   │    │ vnstock_news │         │
│  │              │    │              │    │              │         │
│  │ • OHLCV     │    │ • RSI       │    │ • RSS Crawl │         │
│  │ • Reference │───▶│ • MACD      │    │ • Sentiment │         │
│  │ • Fundamental│    │ • ADX      │    │ • Keywords  │         │
│  │ • Market    │    │ • SuperTrend│    │             │         │
│  └──────────────┘    └──────────────┘    └──────────────┘         │
│         │                   │                    │                   │
│         └───────────────────┼────────────────────┘                   │
│                             ▼                                        │
│              ┌──────────────────────────────┐                      │
│              │      ANALYSIS ENGINE          │                      │
│              │                              │                      │
│              │  1. Technical Analysis       │                      │
│              │  2. Fundamental Analysis     │                      │
│              │  3. News Sentiment          │                      │
│              │  4. AI Recommendation        │                      │
│              └──────────────────────────────┘                      │
│                             │                                        │
│                             ▼                                        │
│              ┌──────────────────────────────┐                      │
│              │       ASSET CARD OUTPUT      │                      │
│              │                              │                      │
│              │  Symbol | Indicators | Score  │                      │
│              │  Recommendation | Risk Level │                      │
│              └──────────────────────────────┘                      │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. CÁC NHÓM CHỨC NĂNG

| # | Nhóm | Nguồn | Indicators | Status |
|---|-------|--------|------------|--------|
| 1 | **Cổ phiếu** | vnstock_data | RSI, MACD, ADX, CMF/MFI, SuperTrend, SMA/EMA, Bollinger, F-Score | ✅ **IMPLEMENTED** |
| 2 | **Chỉ số (Index)** | vnstock_data | Market Breadth, ADX, SMA | ✅ Hoàn thành thiết kế |
| 3 | **Kim loại quý** | vnstock_data | RSI, ATR, Pivot Points | ✅ Hoàn thành thiết kế |
| 4 | **Phái sinh** | vnstock_data | VWAP, Pivot, ATR | ✅ Hoàn thành thiết kế |
| 5 | **Quỹ đầu tư (ETF)** | vnstock_data | NAV, Premium/Discount | ✅ Hoàn thành thiết kế |
| 6 | **Trái phiếu** | vnstock_data | Yield, Duration | ✅ Hoàn thành thiết kế |
| 7 | **Ngoại hối (Forex)** | vnstock_data | RSI, ATR, Ichimoku | ✅ Hoàn thành thiết kế |
| 8 | **Crypto** | vnstock_data | RSI, MACD, Bollinger | ✅ Hoàn thành thiết kế |
| 9 | **Chứng quyền (CW)** | vnstock_data | Premium, Delta, Theta | ✅ Hoàn thành thiết kế |

---

## 3. NHÓM 1: CỔ PHIẾU (STOCK) ✅

### 3.1 Ví dụ Output Hoàn Chỉnh

```
┌──────────────────────────────────────────────────────────────────┐
│  🏦 VCB - VIETCOMBANK (HOSE)         | THỜI GIAN: 2026-04-24 │
├──────────────────────────────────────────────────────────────────┤
│  GIÁ: 89,500 (+2.3%)    |  VỊ THẾ: TRÊN SMA20/50           │
│  XU HƯỚNG: TĂNG MẠNH (ADX: 32)  |  BIẾN ĐỘNG (ATR): 1,200 │
├──────────────────────────────────────────────────────────────────┤
│  1. PHÂN TÍCH KỸ THUẬT CHUYÊN SÂU (vnstock_ta)               │
│  ────────────────────────────────────────────────────────────    │
│  📈 ĐỘNG LƯỢNG                                                  │
│     RSI(14): 68 ████████████░░░░░░  Zone: TRUNG LẬP          │
│     MACD: +150 (Signal: Bullish Crossover)                      │
│  📊 DÒNG TIỀN                                                  │
│     CMF(20): +0.22 ████████░░░░░░░░░  TIỀN CHẢY VÀO (+)      │
│     MFI(14): 65 ████████████░░░░░░░  Zone: TRUNG LẬP         │
│  🎯 VÙNG GIÁ                                                    │
│     Bollinger: Giá sát Upper Band (vùng 80%)                    │
│     VWAP: 88,800 - Giá đang TRÊN VWAP                          │
│  🔄 XU HƯỚNG                                                    │
│     SMA(20): 87,200 │ SMA(50): 85,500 │ Giá: 89,500           │
│     ADX: 32 (>25 = Xu hướng MẠNH)                             │
│     SuperTrend: BUY | Stop: 85,800 | Duy trì từ vùng 86,000    │
├──────────────────────────────────────────────────────────────────┤
│  2. SỨC KHỎE DOANH NGHIỆP (vnstock_data - Fundamental L3)      │
│  ────────────────────────────────────────────────────────────    │
│  📋 F-Score: 7/9 ★★★★★★★☆☆☆ (Grade A)                        │
│     ├── ROA tăng           ✓                                    │
│     ├── ROE tăng           ✓                                    │
│     ├── EPS tăng           ✓                                    │
│     ├── D/E giảm           ✓                                    │
│     ├── Current Ratio ≥1   ✓                                    │
│     ├── Gross Margin tăng  ✓                                    │
│     ├── Asset Turnover ↑   ✓                                    │
│     └── Abnormal Return     ✗                                   │
│  💰 ĐỊNH GIÁ                                                   │
│     P/E: 12.5x (Thấp hơn TB ngành 14.2x) → HẤP DẪN           │
│     P/B: 1.8x  |  ROE: 18.2%  |  EPS: 7,160                  │
│  📈 TĂNG TRƯỞNG                                                │
│     Lợi nhuận Q1/2026: +15.2% YoY                             │
│     Biên lợi nhuận: 45.2% (Ổn định)                          │
├──────────────────────────────────────────────────────────────────┤
│  3. TIN TỨC & TÂM LÝ (vnstock_news)                            │
│  ────────────────────────────────────────────────────────────    │
│  📰 Số tin 7 ngày: 12 bài                                      │
│  😊 Tâm lý: TÍCH CỰC (Score: +0.65)                           │
│     • Tin về nới room tín dụng                                  │
│     • Kết quả kinh doanh khả quan Q1                          │
│     • Dự kiến chia cổ tức 2025                                 │
│  🔑 Keywords nổi bật: [Cổ tức], [Tăng vốn], [Tín dụng]       │
├──────────────────────────────────────────────────────────────────┤
│  🤖 AI INSIGHT: TIẾP TỤC NẮM GIỮ (HOLD)                       │
│  ────────────────────────────────────────────────────────────    │
│  Master Score: 82/100 ★★★★☆                                    │
│  ────────────────────────────────────────────────────────────    │
│  ✅ ƯU ĐIỂM:                                                   │
│     • Xu hướng tăng được xác nhận (ADX > 25)                   │
│     • Dòng tiền chảy vào (CMF > 0)                            │
│     • Nội tại doanh nghiệp vững (F-Score: 7/9)                │
│     • Định giá hấp dẫn (P/E 12.5 vs ngành 14.2)              │
│  ⚠️ RỦI RO:                                                   │
│     • RSI 68 - Còn space nhưng không còn rẻ                    │
│     • Giá sát Bollinger Upper - Có thể chỉnh ngắn             │
│  ────────────────────────────────────────────────────────────    │
│  📌 HÀNH ĐỘNG CỤ THỂ:                                        │
│     • Đã có: GIỮ - Chốt lời từng phần quanh 92,000            │
│     • Chưa có: CHỜ - Mua quanh 87,500-88,000 (Retest SMA20)   │
│     • 🛑 Stop Loss: 85,800 (-4.1%)                              │
│     • 🎯 Mục tiêu: 94,500 (+5.6%)                             │
│     • ⏰ Timeframe: SWING (5-10 ngày)                           │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Chỉ Báo Sử Dụng

| Loại | Chỉ báo | Nguồn | Mô tả |
|------|---------|-------|--------|
| **Động lượng** | RSI(14) | vnstock_ta | Overbought/Oversold |
| **Động lượng** | MACD | vnstock_ta | Crossover signals |
| **Xu hướng** | ADX | vnstock_ta | Cường độ xu hướng |
| **Xu hướng** | SuperTrend | vnstock_ta | Stop-loss động |
| **Xu hướng** | SMA(20/50) | vnstock_ta | Trend direction |
| **Dòng tiền** | CMF(20) | vnstock_ta | Money flow |
| **Dòng tiền** | MFI(14) | vnstock_ta | Volume-weighted RSI |
| **Biến động** | Bollinger Bands | vnstock_ta | Price channels |
| **Biến động** | ATR(14) | vnstock_ta | Volatility measure |
| **Giá trị** | VWAP | vnstock_ta | Intraday benchmark |
| **Cơ bản** | F-Score | vnstock_data | Financial health |
| **Cơ bản** | P/E, P/B, ROE | vnstock_data | Valuation metrics |

---

## 4. NHÓM 2: CHỈ SỐ THỊ TRƯỜNG (INDEX) ✅

### 4.1 Ví dụ Output

```
┌──────────────────────────────────────────────────────────────────┐
│  📊 CHỈ SỐ THỊ TRƯỜNG              | THỜI GIAN: 2026-04-24    │
├──────────────────────────────────────────────────────────────────┤
│  ┌─────────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │ Chỉ số     │ Giá      │ %Change  │ Vol      │ ADX      │   │
│  ├─────────────┼──────────┼──────────┼──────────┼──────────┤   │
│  │ VNINDEX     │ 1,385.2  │ +1.45%   │ 285M     │ 28       │   │
│  │ VN30        │ 1,245.8  │ +1.82%   │ 112M     │ 31       │   │
│  │ HNX        │ 245.3    │ +0.73%   │ 45M      │ 22       │   │
│  │ UPCOM       │ 98.5     │ +0.51%   │ 38M      │ 19       │   │
│  └─────────────┴──────────┴──────────┴──────────┴──────────┘   │
├──────────────────────────────────────────────────────────────────┤
│  📈 MARKET BREADTH (Sức khỏe thị trường)                      │
│  ────────────────────────────────────────────────────────────     │
│  Advance/Decline: 285 ↑ / 142 ↓ / 78 ─────────────────────    │
│  Tỷ lệ: 2.0:1 (THỊ TRƯỜNG TĂNG MẠNH)                        │
│  ────────────────────────────────────────────────────────────     │
│  💡 NHẬN ĐỊNH: THUẬN CHIỀU                                    │
│     • VN30 dẫn dắt đà tăng (+1.82%)                           │
│     • Breadth tích cực (2:1)                                   │
│     • Khối lượng trên TB 30%                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Chỉ Báo Sử Dụng

| Loại | Chỉ báo | Nguồn | Mô tả |
|------|---------|-------|--------|
| **Breadth** | Advance/Decline | vnstock_data | Số mã tăng/giảm |
| **Breadth** | High/Low Ratio | vnstock_data | Mã tạo high/low mới |
| **Xu hướng** | ADX | vnstock_ta | Cường độ xu hướng |
| **Xu hướng** | SMA | vnstock_ta | Vị trí giá vs SMA |

---

## 5. NHÓM 3: KIM LOẠI QUÝ (GOLD) 🔴

### 5.1 Ví dụ Output

```
┌──────────────────────────────────────────────────────────────────┐
│  🥇 VÀNG SJC              | THỜI GIAN: 2026-04-24 14:30     │
├──────────────────────────────────────────────────────────────────┤
│  💰 GIÁ TRONG NƯỚC                                              │
│  ────────────────────────────────────────────────────────────    │
│  Mua vào: 88,500,000 VND/lượng                                │
│  Bán ra:  89,200,000 VND/lượng                                │
│  Spread:  700,000 VND (0.79%)                                  │
│  ────────────────────────────────────────────────────────────    │
│  💵 GIÁ THẾ GIỚI                                                │
│  ────────────────────────────────────────────────────────────    │
│  Gold Spot: $3,234/oz                                           │
│  VND/USD: 25,450                                                 │
│  Giá quy đổi: 88,350,000 VND/lượng                            │
│  Premium: +150,000 VND (Primacy SJC cao hơn TT)                │
├──────────────────────────────────────────────────────────────────┤
│  📊 PHÂN TÍCH KỸ THUẬT (vnstock_ta)                          │
│  ────────────────────────────────────────────────────────────    │
│  📈 ĐỘNG LƯỢNG                                                  │
│     RSI(14): 72 ██████████████░░░░  Zone: QUÁ MUA            │
│     MACD: +45 (Signal: Bullish nhưng yếu)                       │
│  🎯 VÙNG GIÁ                                                    │
│     Bollinger Upper: 89,500,000 │ Lower: 87,200,000           │
│     Giá đang ở vùng 75% (gần Upper)                            │
│     Pivot R1: 89,500,000 │ S1: 88,200,000                     │
│  🔄 XU HƯỚNG                                                    │
│     SMA(20): 88,800,000 │ SMA(50): 88,200,000                │
│     Giá đang TRÊN cả 2 SMA → Uptrend                          │
│     ADX: 25 - Xu hướng yếu, cần cẩn trọng                     │
│  📐 BIẾN ĐỘNG                                                   │
│     ATR(14): 850,000 VND - BIẾN ĐỘNG CAO                      │
├──────────────────────────────────────────────────────────────────┤
│  🤖 AI INSIGHT: THEO DÕI (WATCH)                               │
│  ────────────────────────────────────────────────────────────    │
│  Master Score: 65/100 ★★★☆☆                                    │
│  ────────────────────────────────────────────────────────────    │
│  ⚠️ RỦI RO:                                                     │
│     • RSI 72 - Vùng QUÁ MUA, có nguy cơ chỉnh                  │
│     • Giá SJC cao hơn thế giới +150K (Premium cao)            │
│     • ADX 25 - Xu hướng yếu, dễ sideway                        │
│  ────────────────────────────────────────────────────────────    │
│  📌 HÀNH ĐỘNG:                                                  │
│     • Không nên MUA lúc này (Giá đang cao)                    │
│     • Nên CHỜ chỉnh về 88,200,000-88,500,000 để mua          │
│     • 🛑 Cắt lỗ: 87,200,000 nếu hold                          │
│     • 🎯 Mục tiêu: 89,500,000 (Upper Bollinger)               │
│     • ⏰ Timeframe: SWING trung hạn                             │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Chỉ Báo Sử Dụng

| Loại | Chỉ báo | Nguồn | Mô tả |
|------|---------|-------|--------|
| **Giá** | Spot/Retail Price | vnstock | Giá vàng thế giới & SJC |
| **Động lượng** | RSI(14) | vnstock_ta | Overbought/Oversold |
| **Động lượng** | MACD | vnstock_ta | Trend momentum |
| **Vùng giá** | Pivot Points | vnstock_ta | Support/Resistance |
| **Biến động** | Bollinger Bands | vnstock_ta | Price channels |
| **Biến động** | ATR(14) | vnstock_ta | Volatility measure |
| **Xu hướng** | SMA(20/50) | vnstock_ta | Trend direction |
| **Xu hướng** | ADX | vnstock_ta | Trend strength |
| **Giá trị** | Premium/Discount | Calculated | Chênh lệch SJC vs TT |

---

## 6. NHÓM 4: PHÁI SINH (FUTURES) 🔴

### 6.1 Ví dụ Output

```
┌──────────────────────────────────────────────────────────────────┐
│  📊 VN30F1M - HỢP ĐỒNG TƯƠNG LAI VN30               2026-04-24 │
├──────────────────────────────────────────────────────────────────┤
│  💹 GIÁ HIỆN TẠI                                              │
│  ────────────────────────────────────────────────────────────    │
│  VN30 Index: 1,245.8                                          │
│  VN30F M1: 1,247.2 (+1.2 điểm = +0.10%)                     │
│  Basis: +1.4 điểm (Premium)                                  │
│  ────────────────────────────────────────────────────────────    │
│  Ngày đáo hạn: 2026-04-30 (còn 6 ngày)                       │
│  Hợp đồng gần nhất: VN30F1M                                  │
├──────────────────────────────────────────────────────────────────┤
│  📊 PHÂN TÍCH KỸ THUẬT (vnstock_ta)                          │
│  ────────────────────────────────────────────────────────────    │
│  📐 BIẾN ĐỘNG                                                   │
│     ATR(14): 18 điểm - BIẾN ĐỘNG TRUNG BÌNH                  │
│     Bollinger Width: 45 điểm (Biên độ bình thường)            │
│  🎯 VÙNG GIÁ                                                    │
│     VWAP: 1,246.5 - Giá đang TRÊN VWAP                        │
│     Pivot: 1,245.0                                            │
│     R1: 1,252.0 │ R2: 1,258.0                               │
│     S1: 1,240.0 │ S2: 1,235.0                               │
│  🔄 XU HƯỚNG                                                    │
│     SMA(20): 1,242.0 │ SMA(50): 1,238.0                     │
│     Giá đang TRÊN cả 2 SMA → Uptrend                          │
│     ADX: 29 - Xu hướng tăng yếu                              │
│  📈 ĐỘNG LƯỢNG                                                  │
│     RSI(14): 58 ███████████░░░░░░░░  Zone: TRUNG LẬP        │
│     MACD Histogram: +0.8 (đang tăng)                          │
├──────────────────────────────────────────────────────────────────┤
│  📊 THÔNG TIN HỢP ĐỒNG                                        │
│  ────────────────────────────────────────────────────────────    │
│  Hệ số nhân: 100,000 VND/điểm                                │
│  Tổng giá trị: ~124,720,000 VND                              │
│  Margin yêu cầu: ~12,472,000 VND (10%)                       │
│  ────────────────────────────────────────────────────────────    │
│  Cò quỹ (Funding): +0.002%/ngày (Annual: ~7.3%)              │
│  ────────────────────────────────────────────────────────────    │
│  📊 ĐỘ KHÚC XẠO (Contango/Backwardation):                    │
│     VN30F2M: 1,248.5 (Premium +1.3)                           │
│     VN30F3M: 1,249.8 (Premium +1.3)                           │
│     → Thị trường CONTANGO nhẹ (Bullish)                      │
├──────────────────────────────────────────────────────────────────┤
│  🤖 AI INSIGHT: LONG NHẸNHAN (WATCH)                          │
│  ────────────────────────────────────────────────────────────    │
│  Master Score: 62/100 ★★★☆☆                                    │
│  ────────────────────────────────────────────────────────────    │
│  ✅ ƯU ĐIỂM:                                                   │
│     • Basis dương +1.4 - Premium nhẹ                          │
│     • Giá đang trên VWAP                                      │
│     • Contango nhẹ - Bullish signal                           │
│  ⚠️ RỦI RO:                                                    │
│     • ADX 29 - Xu hướng yếu, có thể sideway                   │
│     • Còn 6 ngày đáo hạn - Theta decay sắp tăng              │
│     • Basis có thể thu hẹp nhanh gần đáo hạn                 │
│  ────────────────────────────────────────────────────────────    │
│  📌 HÀNH ĐỘNG:                                                  │
│     • LONG: Mở quanh 1,245-1,247 với SL 1,238               │
│     • 🛑 Stop Loss: 1,238 (-7 điểm)                           │
│     • 🎯 Mục tiêu: 1,252 (+5 điểm)                           │
│     • ⏰ Thời gian hold: 2-3 ngày (trước đáo hạn)            │
│     • ⚠️ Chú ý: Roll sang VN30F2M nếu hold > 4 ngày          │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Chỉ Báo Sử Dụng

| Loại | Chỉ báo | Nguồn | Mô tả |
|------|---------|-------|--------|
| **Giá** | Futures Price | vnstock | Giá hợp đồng tương lai |
| **Giá** | Basis/Premium | Calculated | Chênh lệch với spot |
| **Biến động** | ATR(14) | vnstock_ta | Volatility |
| **Biến động** | Bollinger Width | vnstock_ta | Contract range |
| **Giá trị** | VWAP | vnstock_ta | Intraday benchmark |
| **Vùng giá** | Pivot Points | vnstock_ta | S/R levels |
| **Xu hướng** | SMA(20/50) | vnstock_ta | Trend direction |
| **Xu hướng** | ADX | vnstock_ta | Trend strength |
| **Động lượng** | RSI(14) | vnstock_ta | Overbought/Oversold |
| **Động lượng** | MACD | vnstock_ta | Momentum |
| **Hợp đồng** | Contango/Back | Calculated | Term structure |

---

## 7. NHÓM 5: QUỸ ĐẦU TƯ (ETF/FUND) 🔴

### 7.1 Ví dụ Output

```
┌──────────────────────────────────────────────────────────────────┐
│  📊 E1VFVN30 - QUỹ ETF CHỈ SỐ VN30              THỜI GIAN: 2026-04-24 │
├──────────────────────────────────────────────────────────────────┤
│  💰 THÔNG TIN CƠ BẢN                                           │
│  ────────────────────────────────────────────────────────────    │
│  NAV/CCQ: 25,450 VND                                          │
│  Giá thị trường: 25,520 VND (+0.28%)                         │
│  Premium/Discount: +0.27% (Giá > NAV)                         │
│  ────────────────────────────────────────────────────────────    │
│  Tổng tài sản (AUM): 2,450 tỷ VND                            │
│  Số lượng chứng chỉ: 96.2 triệu CCQ                          │
├──────────────────────────────────────────────────────────────────┤
│  📊 SO SÁNH VỚI CHỈ SỐ VN30                                    │
│  ────────────────────────────────────────────────────────────    │
│  VN30 Index: 1,245.8 (+1.45%)                                 │
│  E1VFVN30 NAV: 25,450 (+1.38%)                                │
│  Tracking Error: -0.07% (Hiệu suất kém VN30)                  │
│  Beta: 0.98 (Dao động thấp hơn VN30 2%)                      │
│  ────────────────────────────────────────────────────────────    │
│  📈 HIỆU SUẤT                                                 │
│  ────────────────────────────────────────────────────────────    │
│  1D: +1.38% │ 1W: +3.2% │ 1M: +5.8% │ YTD: +8.5%           │
│  ────────────────────────────────────────────────────────────    │
│  💵 CỔ TỨC & PHÂN PHỐI                                        │
│  ────────────────────────────────────────────────────────────    │
│  Cổ tức gần nhất: 380 VND/CCQ (2025-Q4)                      │
│  Tỷ lệ cổ tức: 1.5%/năm                                      │
│  Đã tái đầu tư vào NAV                                        │
├──────────────────────────────────────────────────────────────────┤
│  📊 PHÂN TÍCH KỸ THUẬT NAV (vnstock_ta)                       │
│  ────────────────────────────────────────────────────────────    │
│  📈 ĐỘNG LƯỢNG                                                  │
│     RSI(14) NAV: 65 ████████████░░░░░  Zone: TÍCH CỰC        │
│     MACD NAV: +120 (Bullish crossover gần đây)                 │
│  🔄 XU HƯỚNG                                                    │
│     SMA(20): 25,200 │ SMA(50): 24,800 │ NAV: 25,450          │
│     NAV đang TRÊN cả 2 SMA → Uptrend                          │
│     ADX: 28 - Xu hướng tăng vừa                               │
├──────────────────────────────────────────────────────────────────┤
│  🤖 AI INSIGHT: MUA (BUY)                                       │
│  ────────────────────────────────────────────────────────────    │
│  Master Score: 75/100 ★★★★☆                                    │
│  ────────────────────────────────────────────────────────────    │
│  ✅ ƯU ĐIỂM:                                                   │
│     • Premium nhẹ +0.27% - Thanh khoản tốt                    │
│     • NAV trên SMA20/50 - Uptrend                             │
│     • Cổ tức 1.5%/năm - Thu nhập ổn định                     │
│     • Tracking error thấp - Quỹ theo sát chỉ số              │
│  ⚠️ RỦI RO:                                                    │
│     • Premium có thể âm khi thị trường giảm                   │
│     • Tracking error -0.07% - Hiệu suất kém VN30 nhẹ         │
│  ────────────────────────────────────────────────────────────    │
│  📌 HÀNH ĐỘNG:                                                  │
│     • MUA: Phù hợp cho người muốn đầu tư VN30 an toàn       │
│     • Mục tiêu NAV: 26,200 (+3%)                              │
│     • 🛑 Cắt lỗ NAV: 24,800 (-2.5%)                          │
│     • ⏰ Timeframe: DÀI HẠN (6-12 tháng)                     │
│     • 📊 Tỷ lệ danh mục khuyến nghị: 10-15%                  │
└──────────────────────────────────────────────────────────────────┘
```

### 7.2 Chỉ Báo Sử Dụng

| Loại | Chỉ báo | Nguồn | Mô tả |
|------|---------|-------|--------|
| **Giá trị** | NAV/CCQ | vnstock | Giá trị tài sản ròng |
| **Giá trị** | Market Price | vnstock | Giá thị trường |
| **Giá trị** | Premium/Discount | Calculated | Chênh lệch P vs NAV |
| **Theo dõi** | Tracking Error | Calculated | Chênh lệch với benchmark |
| **Theo dõi** | Beta | Calculated | Dao động vs benchmark |
| **Hiệu suất** | Return 1D/W/M/YTD | vnstock | Performance |
| **Cơ bản** | AUM | vnstock | Tổng tài sản |
| **Cơ bản** | Dividend Yield | vnstock | Tỷ lệ cổ tức |
| **Kỹ thuật** | RSI/SMA/ADX | vnstock_ta | NAV chart analysis |

---

## 8. NHÓM 6: TRÁI PHIẾU (BONDS) 🔴

### 8.1 Ví dụ Output

```
┌──────────────────────────────────────────────────────────────────┐
│  📊 TRÁI PHIẾU CHÍNH PHỦ VN                THỜI GIAN: 2026-04-24 │
├──────────────────────────────────────────────────────────────────┤
│  💰 DANH SÁCH TRÁI PHIẾU CHÍNH PHỦ                          │
│  ────────────────────────────────────────────────────────────    │
│  ┌──────────────────┬────────────┬──────────┬──────────────┐    │
│  │ Mã              │ Lãi suất   │ Kỳ hạn   │ Thanh khoản │    │
│  ├──────────────────┼────────────┼──────────┼──────────────┤    │
│  │ VNDN0526006     │ 3.50%      │ 5 năm    │ Cao          │    │
│  │ VNDN0528012     │ 3.80%      │ 10 năm   │ Cao          │    │
│  │ VNDN0534011     │ 4.20%      │ 15 năm   │ Trung bình   │    │
│  └──────────────────┴────────────┴──────────┴──────────────┘    │
├──────────────────────────────────────────────────────────────────┤
│  📊 CHI TIẾT: VNDN0528012 (10 NĂM)                            │
│  ────────────────────────────────────────────────────────────    │
│  Mệnh giá: 100,000 VND                                        │
│  Lãi suất coupon: 3.80%/năm (trả 2 lần/năm)                  │
│  Ngày phát hành: 2024-08-26                                   │
│  Ngày đáo hạn: 2034-08-26 (8.3 năm còn lại)                  │
│  ────────────────────────────────────────────────────────────    │
│  💵 GIÁ THỊ TRƯỜNG                                            │
│  ────────────────────────────────────────────────────────────    │
│  Giá hiện tại: 98.50 (Giá < Mệnh giá → Yield cao hơn)       │
│  Yield to Maturity (YTM): 3.95%                               │
│  YTM vs Coupon: +0.15% (Đang discount)                        │
│  ────────────────────────────────────────────────────────────    │
│  📐 ĐỘ NHẠY CẢ (RATE RISK)                                    │
│  ────────────────────────────────────────────────────────────    │
│  Duration: 7.8 năm (Nhạy cảm với lãi suất)                   │
│  Modified Duration: 7.5                                       │
│  Yield tăng 1% → Giá giảm 7.5%                               │
│  ────────────────────────────────────────────────────────────    │
│  📈 SO SÁNH LÃI SUẤT                                         │
│  ────────────────────────────────────────────────────────────    │
│  VNDN 5Y: 3.50% │ VNDN 10Y: 3.80% │ VNDN 15Y: 4.20%       │
│  Yield Curve: INVERTED (Ngắn hạn cao hơn dài hạn)           │
│  → Đường cong lãi suất ĐẢO NGƯỢC                            │
├──────────────────────────────────────────────────────────────────┤
│  🤖 AI INSIGHT: THEO DÕI (WATCH)                               │
│  ────────────────────────────────────────────────────────────    │
│  Master Score: 55/100 ★★★☆☆                                    │
│  ────────────────────────────────────────────────────────────    │
│  ✅ ƯU ĐIỂM:                                                   │
│     • YTM 3.95% cao hơn lãi suất tiết kiệm ngân hàng         │
│     • Đang discount - Có room tăng giá                        │
│     • Trái phiếu CP có bảo đảm bởi Chính phủ VN             │
│  ⚠️ RỦI RO:                                                    │
│     • Yield curve inverted - Dấu hiệu suy thoái              │
│     • Duration cao 7.8 năm - Rủi ro lãi suất lớn            │
│     • YTM có thể tăng khi NHNN tăng lãi suất điều hành      │
│  ────────────────────────────────────────────────────────────    │
│  📌 HÀNH ĐỘNG:                                                  │
│     • PHÙ HỢP: Nhà đầu tư dài hạn, chịu được biến động     │
│     • KHÔNG PHÙ HỢP: Người cần thanh khoản cao, sợ lãi suất │
│     • Nên đầu tư lô nhỏ, chia nhỏ thời gian                │
│     • ⏰ Timeframe: DÀI HẠN (3-5 năm)                        │
└──────────────────────────────────────────────────────────────────┘
```

### 8.2 Chỉ Báo Sử Dụng

| Loại | Chỉ báo | Nguồn | Mô tả |
|------|---------|-------|--------|
| **Giá** | Bond Price | vnstock | Giá thị trường |
| **Lợi suất** | YTM | Calculated | Yield to Maturity |
| **Lợi suất** | Coupon Rate | vnstock | Lãi suất danh nghĩa |
| **Rủi ro** | Duration | Calculated | Độ nhạy cảm lãi suất |
| **Rủi ro** | Modified Duration | Calculated | Price sensitivity |
| **Rủi ro** | Macaulay Duration | Calculated | Weighted avg maturity |
| **Đường cong** | Yield Curve | vnstock | Term structure |
| **So sánh** | Spread vs Benchmark | Calculated | Credit spread |

---

## 9. NHÓM 7: NGOẠI HỐI (FOREX) 🔴

### 9.1 Ví dụ Output

```
┌──────────────────────────────────────────────────────────────────┐
│  💱 TỶ GIÁ NGOẠI HỐI                   THỜI GIAN: 2026-04-24 14:30 │
├──────────────────────────────────────────────────────────────────┤
│  💰 CÁC CẶP TIỀN CHÍNH                                          │
│  ────────────────────────────────────────────────────────────    │
│  ┌──────────────────┬────────────┬──────────┬──────────────┐    │
│  │ Cặp tiền       │ Giá        │ %Change  │ Xu hướng    │    │
│  ├──────────────────┼────────────┼──────────┼──────────────┤    │
│  │ USD/VND         │ 25,450     │ +0.12%   │ Tăng        │    │
│  │ EUR/VND         │ 27,850     │ -0.35%   │ Giảm        │    │
│  │ JPY/VND         │ 168.5      │ +0.08%   │ Tăng nhẹ   │    │
│  │ GBP/VND         │ 32,100     │ -0.22%   │ Giảm        │    │
│  │ CNY/VND         │ 3,520      │ -0.15%   │ Giảm        │    │
│  └──────────────────┴────────────┴──────────┴──────────────┘    │
├──────────────────────────────────────────────────────────────────┤
│  📊 CHI TIẾT: USD/VND                                          │
│  ────────────────────────────────────────────────────────────    │
│  Tỷ giá: 25,450 VND/USD                                        │
│  Bid: 25,445 │ Ask: 25,455                                    │
│  Spread: 10 VND (0.04%)                                        │
│  ────────────────────────────────────────────────────────────    │
│  📈 PHÂN TÍCH KỸ THUẬT (vnstock_ta)                          │
│  ────────────────────────────────────────────────────────────    │
│  📊 DÒNG TIỀN                                                  │
│     CMF(20): -0.15 ███░░░░░░░░░░░░░░░  TIỀN CHẢY RA (-)    │
│     → VND yếu đi, áp lực bán VND tăng                        │
│  🔄 XU HƯỚNG                                                    │
│     SMA(20): 25,380 │ SMA(50): 25,320 │ Giá: 25,450        │
│     Giá đang TRÊN cả 2 SMA → VND YẾU                          │
│     ADX: 35 - Xu hướng yếu VND MẠNH                          │
│  📐 BIẾN ĐỘNG                                                   │
│     ATR(14): 85 VND - BIẾN ĐỘNG THẤP                          │
│     Bollinger Width: 180 VND                                   │
│  🎯 VÙNG GIÁ                                                    │
│     Ichimoku Cloud: Giá trên cloud (Bullish bias)             │
│     Tenkan-sen: 25,420 │ Kijun-sen: 25,350                    │
├──────────────────────────────────────────────────────────────────┤
│  📊 SO SÁNH LÃI SUẤT (SWAP)                                   │
│  ────────────────────────────────────────────────────────────    │
│  Fed Funds Rate: 5.25%                                        │
│  SBV Policy Rate: 4.50%                                       │
│  Lãi suất chênh lệch: -0.75% (VND có劣势)                    │
│  → Swap USD/VND 12M: -0.68% (Bearish VND)                    │
│  ────────────────────────────────────────────────────────────    │
│  🏦 YẾU TỐ CƠ BẢN                                              │
│  ────────────────────────────────────────────────────────────    │
│  Chỉ số DXY: 104.5 (+0.3%) - Đồng USD mạnh                  │
│  Nhập khẩu Việt Nam 12 tháng: $340B                          │
│  Xuất khẩu Việt Nam 12 tháng: $370B                          │
│  Cán cân thương mại: +$30B (Thặng dư → Hỗ trợ VND)          │
├──────────────────────────────────────────────────────────────────┤
│  🤖 AI INSIGHT: VND YẾU NHẸ (WATCH)                            │
│  ────────────────────────────────────────────────────────────    │
│  Master Score: 45/100 ★★☆☆☆                                    │
│  ────────────────────────────────────────────────────────────    │
│  ✅ HỖ TRỢ VND:                                                 │
│     • Cán cân thương mại thặng dư +$30B                      │
│     • ATR thấp 85 VND - Biến động kiểm soát                   │
│     • Ichimoku bullish bias                                   │
│  ⚠️ ÁP LỰC VND:                                                 │
│     • ADX 35 - Xu hướng VND yếu MẠNH                          │
│     • CMF -0.15 - Dòng tiền chảy ra ngoại tệ                │
│     • Chênh lệch lãi suất -0.75% bất lợi VND                │
│     • DXY tăng 0.3% - Đồng USD mạnh                          │
│  ────────────────────────────────────────────────────────────    │
│  📌 DỰ ĐOÁN:                                                    │
│     • Ngắn hạn: 25,400-25,500 (Sideway)                      │
│     • Trung hạn: Có thể 25,550-25,600 nếu DXY tiếp tục tăng │
│     • Dài hạn: VND ổn định nhờ thặng dư TM                  │
│     • ⏰ Khuyến nghị: HOLD, chờ breakout                      │
└──────────────────────────────────────────────────────────────────┘
```

### 9.2 Chỉ Báo Sử Dụng

| Loại | Chỉ báo | Nguồn | Mô tả |
|------|---------|-------|--------|
| **Giá** | Exchange Rate | vnstock | Tỷ giá VND |
| **Spread** | Bid/Ask | vnstock | Spread giao dịch |
| **Dòng tiền** | CMF(20) | vnstock_ta | Money flow |
| **Xu hướng** | SMA(20/50) | vnstock_ta | Trend direction |
| **Xu hướng** | ADX | vnstock_ta | Trend strength |
| **Biến động** | ATR(14) | vnstock_ta | Volatility |
| **Biến động** | Bollinger Bands | vnstock_ta | Price channels |
| **Xu hướng** | Ichimoku Cloud | vnstock_ta | Multi-timeframe trend |
| **Cơ bản** | Interest Rate Diff | vnstock | Rate differential |
| **Cơ bản** | Trade Balance | vnstock | Cán cân thương mại |

---

## 10. NHÓM 8: CRYPTO 🔴

### 10.1 Ví dụ Output

```
┌──────────────────────────────────────────────────────────────────┐
│  ₿ BITCOIN (BTC-USD)                    THỜI GIAN: 2026-04-24 14:30 │
├──────────────────────────────────────────────────────────────────┐
│  💰 GIÁ HIỆN TẠI                                              │
│  ────────────────────────────────────────────────────────────    │
│  Giá: $94,250 (+2.3%)                                        │
│  24h High: $95,100 │ 24h Low: $91,800                        │
│  Volume 24h: $28.5B (Cao hơn TB 35%)                         │
│  Market Cap: $1.85T │ Dominance: 52.3%                        │
├──────────────────────────────────────────────────────────────────┤
│  📊 PHÂN TÍCH KỸ THUẬT (vnstock_ta)                          │
│  ────────────────────────────────────────────────────────────    │
│  📈 ĐỘNG LƯỢNG                                                  │
│     RSI(14): 68 ████████████░░░░░░  Zone: TRUNG LẬP          │
│     MACD: +850 (Signal: Bullish Crossover gần đây)            │
│     MACD Histogram đang TĂNG                                 │
│  📊 DÒNG TIỀN                                                  │
│     CMF(20): +0.18 ███████░░░░░░░░░░  TIỀN CHẢY VÀO (+)      │
│     On-Balance Volume: 14.2B (Tích lũy)                      │
│  🎯 VÙNG GIÁ                                                    │
│     Bollinger: Upper $96,500 │ Middle $93,200 │ Lower $90,000 │
│     Giá đang ở vùng 70% (Trên middle)                        │
│     VWAP: $93,500 - Giá đang TRÊN VWAP                        │
│  🔄 XU HƯỚNG                                                    │
│     SMA(20): $92,800 │ SMA(50): $89,500 │ SMA(200): $78,000  │
│     Giá đang TRÊN tất cả các SMA → STRONG BULLISH             │
│     ADX: 42 (>25 = Xu hướng MẠNH)                            │
│  🔄 MẠNG LƯỚI (NETWORK)                                        │
│     ─────────────────────────────────────────────────────────  │
│     Hash Rate: 520 EH/s (ATH)                                 │
│     Difficulty: 92.5T (Tăng 2.3%)                             │
│     Active Addresses 24h: 1.2M (+15%)                         │
├──────────────────────────────────────────────────────────────────┤
│  📊 SENTIMENT & ON-CHAIN                                       │
│  ────────────────────────────────────────────────────────────    │
│  Fear & Greed Index: 72 (GREED)                              │
│  ────────────────────────────────────────────────────────────    │
│  Funding Rate (Exchange): +0.015%/8h (Long > Short)           │
│  Open Interest: $18.2B (Cao - Thận trọng)                     │
│  ETF Flow 24h: +$185M (Mu vào)                               │
│  Whale Transactions >$1M: 1,450 (Tăng 22%)                   │
├──────────────────────────────────────────────────────────────────┤
│  🤖 AI INSIGHT: TIẾP TỤC NẮM GIỮ (HOLD)                       │
│  ────────────────────────────────────────────────────────────    │
│  Master Score: 78/100 ★★★★☆                                    │
│  ────────────────────────────────────────────────────────────    │
│  ✅ ƯU ĐIỂM:                                                   │
│     • Xu hướng STRONG BULLISH (ADX 42, trên tất cả SMA)       │
│     • Dòng tiền chảy vào (CMF +0.18, ETF +$185M)             │
│     • On-chain healthy (Hash rate ATH, whale accumulation)    │
│     • Funding rate vẫn kiểm soát được                        │
│  ⚠️ RỦI RO:                                                    │
│     • RSI 68 - Còn space nhưng gần vùng quá mua              │
│     • Fear & Greed 72 (Greed) - Cẩn thận đỉnh local         │
│     • Open Interest cao $18.2B - Có thể liquidation cascade   │
│  ────────────────────────────────────────────────────────────    │
│  📌 HÀNH ĐỘNG CỤ THỂ:                                        │
│     • Đã có: GIỮ - Chốt lời dần quanh $96,000-97,000        │
│     • Chưa có: CHỜ - Mua quanh $91,000-92,000 (Retest)       │
│     • 🛑 Stop Loss: $88,000 (-6.6%)                           │
│     • 🎯 Mục tiêu: $100,000 (+6.1%)                          │
│     • ⏰ Timeframe: SWING (2-4 tuần)                          │
└──────────────────────────────────────────────────────────────────┘
```

### 10.2 Chỉ Báo Sử Dụng

| Loại | Chỉ báo | Nguồn | Mô tả |
|------|---------|-------|--------|
| **Giá** | Price/Change | vnstock | Giá & biến động |
| **Giá** | High/Low | vnstock | 24h range |
| **Volume** | Volume 24h | vnstock | Khối lượng |
| **Động lượng** | RSI(14) | vnstock_ta | Overbought/Oversold |
| **Động lượng** | MACD | vnstock_ta | Trend momentum |
| **Dòng tiền** | CMF(20) | vnstock_ta | Money flow |
| **Dòng tiền** | OBV | vnstock_ta | On-balance volume |
| **Vùng giá** | Bollinger Bands | vnstock_ta | Price channels |
| **Vùng giá** | VWAP | vnstock_ta | Intraday value |
| **Xu hướng** | SMA(20/50/200) | vnstock_ta | Multi-SMA trend |
| **Xu hướng** | ADX | vnstock_ta | Trend strength |
| **On-chain** | Fear & Greed | External | Sentiment |
| **On-chain** | Funding Rate | External | Perp sentiment |
| **On-chain** | ETF Flow | External | Institutional |

---

## 11. NHÓM 9: CHỨNG QUYỀN (COVERED WARRANT) 🔴

### 11.1 Ví dụ Output

```
┌──────────────────────────────────────────────────────────────────┐
│  🏦 CHỨNG QUYỀN VCB                    THỜI GIAN: 2026-04-24   │
├──────────────────────────────────────────────────────────────────┤
│  💰 THÔNG TIN CHỨNG QUYỀN                                     │
│  ────────────────────────────────────────────────────────────    │
│  Mã CW: CVNCB2302                                             │
│  Tổ chức phát hành: VNDirect Securities                      │
│  ────────────────────────────────────────────────────────────    │
│  💵 GIÁ & ĐIỀU KHOẢN                                         │
│  ────────────────────────────────────────────────────────────    │
│  Giá CW: 2,450 VND                                           │
│  Giá underlying (VCB): 89,500 VND                            │
│  Strike price: 87,000 VND                                    │
│  ────────────────────────────────────────────────────────────    │
│  Moneyness: ITM (+2.9% in-the-money)                         │
│  intrinsic Value: 2,500 VND (89,500 - 87,000)                 │
│  Time Value: -50 VND (Discount do thanh khoản)               │
│  Premium: 0.0% (CW đang discount)                            │
│  ────────────────────────────────────────────────────────────    │
│  📅 THỜI GIAN                                                 │
│  ────────────────────────────────────────────────────────────    │
│  Ngày phát hành: 2025-01-15                                  │
│  Ngày đáo hạn: 2026-06-20 (còn 57 ngày)                      │
│  Theta decay: ~5 VND/ngày (Tăng dần đến đáo hạn)            │
├──────────────────────────────────────────────────────────────────┤
│  📊 CÁC CHỈ SỐ HY ĐỖNG                                       │
│  ────────────────────────────────────────────────────────────    │
│  Delta: 0.85 (Giá CW tăng 850 VND khi VCB tăng 1,000)        │
│  Gamma: 0.012 (Delta thay đổi nhanh gần strike)              │
│  Vega: 15 VND/% (Vol tăng 1% → CW tăng 15 VND)               │
│  Theta: -5 VND/ngày (Mất 5 VND/ngày dù giá đứng yên)       │
│  ────────────────────────────────────────────────────────────    │
│  ĐÒN BẨY (Leverage)                                          │
│  ────────────────────────────────────────────────────────────    │
│  Effective Leverage: 31x (VCB tăng 1% → CW tăng 31%)         │
│  Break-even: VCB cần đạt 87,000 để hòa vốn                   │
│  ────────────────────────────────────────────────────────────    │
│  ⚠️ SO SÁNH VỚI MUA TRỰC TIẾP                               │
│  ────────────────────────────────────────────────────────────    │
│  Mua 1 CW: 2,450 VND vs Mua 100 VCB: 8,950,000 VND          │
│  Vốn tiết kiệm: 99.97%                                       │
│  Nhưng rủi ro mất 100% nếu VCB < 87,000 đến đáo hạn        │
├──────────────────────────────────────────────────────────────────┤
│  📊 PHÂN TÍCH VCB (UNDERLYING)                               │
│  ────────────────────────────────────────────────────────────    │
│  VCB Technical: RSI 68, ADX 32, Trend BULLISH                 │
│  (Xem chi tiết ở phần Cổ phiếu)                              │
├──────────────────────────────────────────────────────────────────┤
│  🤖 AI INSIGHT: RỦI RO CAO - KHÔNG KHUYẾN KHÍCH              │
│  ────────────────────────────────────────────────────────────    │
│  Master Score: 35/100 ★★☆☆☆                                    │
│  ────────────────────────────────────────────────────────────    │
│  ⚠️ RỦI RO CHÍNH:                                              │
│     • Còn 57 ngày đáo hạn - THETA DECAY rất nhanh            │
│     • CW đang discount (-50 VND time value) - Bất thường     │
│     • Delta 0.85 - CW đã phản ánh gần hết upside             │
│     • Volatility collapse sẽ làm CW giảm mạnh                │
│  ────────────────────────────────────────────────────────────    │
│  📌 HÀNH ĐỘNG:                                                  │
│     • KHÔNG NÊN mua CW này lúc này                          │
│     • Nếu muốn đòn bẩy: Tìm CW có thời gian > 90 ngày      │
│     • Tìm CW có Delta 0.4-0.6 (Cân bằng đòn bẩy & rủi ro)  │
│     • Luôn đặt stop-loss: -30% giá CW                        │
│     • ⏰ Chỉ trade CW khi hiểu rõ Greeks & Theta             │
└──────────────────────────────────────────────────────────────────┘
```

### 11.2 Chỉ Báo Sử Dụng

| Loại | Chỉ báo | Nguồn | Mô tả |
|------|---------|-------|--------|
| **Giá** | CW Price | vnstock | Giá chứng quyền |
| **Giá** | Underlying Price | vnstock | Giá cổ phiếu cơ sở |
| **Điều khoản** | Strike Price | vnstock | Giá thực hiện |
| **Điều khoản** | Expiry Date | vnstock | Ngày đáo hạn |
| **Định giá** | Intrinsic Value | Calculated | Giá trị nội tại |
| **Định giá** | Time Value | Calculated | Giá trị thời gian |
| **Định giá** | Premium | Calculated | Premium/Dicount |
| **Moneyness** | ITM/ATM/OTM | Calculated | Vị thế tiền |
| **Greeks** | Delta | Calculated | Sensitivity to underlying |
| **Greeks** | Gamma | Calculated | Delta change rate |
| **Greeks** | Vega | Calculated | Volatility sensitivity |
| **Greeks** | Theta | Calculated | Time decay |
| **Đòn bẩy** | Effective Leverage | Calculated | Leverage ratio |
| **Đòn bẩy** | Break-even | Calculated | Giá hòa vốn |

---

## 12. LỘ TRÌNH THỰC HIỆN

### Phase 1: Cổ phiếu (Stock Analysis)
**Thời gian**: 2-3 tuần

- [x] 1.1 Tạo module `dashboard/analyzers/stock_analyzer.py`
- [x] 1.2 Tích hợp vnstock_data + vnstock_ta
- [x] 1.3 Tính F-Score từ Fundamental data
- [x] 1.4 Tạo output template cho Stock Card
- [x] 1.5 Tích hợp vào dashboard/runners.py
- [x] 1.6 Đăng ký vào registry.py
- [ ] 1.7 Test với các mã VN30

### Phase 2: Chỉ số thị trường (Index Analysis)
**Thời gian**: 1 tuần

- [x] 2.1 Tạo module `dashboard/analyzers/index_analyzer.py`
- [x] 2.2 Tính Market Breadth
- [x] 2.3 Tạo output template cho Index Card
- [ ] 2.4 Tích hợp vào dashboard

### Phase 3: Kim loại quý & Phái sinh
**Thời gian**: 1 tuần

- [ ] 3.1 Module vàng (SJC, thế giới)
- [ ] 3.2 Module phái sinh (VN30F)

### Phase 4: Các nhóm còn lại
**Thời gian**: 2 tuần

- [ ] 4.1 ETF/Quỹ đầu tư
- [ ] 4.2 Trái phiếu
- [ ] 4.3 Forex
- [ ] 4.4 Crypto
- [ ] 4.5 Chứng quyền (CW)

### Phase 5: Tích hợp & Optimization
**Thời gian**: 2 tuần

- [ ] 5.1 Caching strategy
- [ ] 5.2 Batch processing
- [ ] 5.3 Real-time updates
- [ ] 5.4 UI/UX improvements

---

## 13. CẤU TRÚC FILES

```
dashboard/
├── analyzers/
│   ├── __init__.py           ✅
│   ├── stock_analyzer.py    ✅ (Phase 1)
│   ├── signals.py           ✅ (Phase 1)
│   ├── index_analyzer.py    ✅ (Phase 2)
│   ├── gold_analyzer.py     🔴
│   ├── futures_analyzer.py  🔴
│   ├── fund_analyzer.py     🔴
│   ├── bond_analyzer.py    🔴
│   ├── forex_analyzer.py    🔴
│   ├── crypto_analyzer.py   🔴
│   └── cw_analyzer.py       🔴
├── runners.py               ✅ (updated)
└── registry.py             ✅ (updated)
```

---

## 14. TIẾN ĐỘ HIỆN TẠI

| Phase | Mô tả | Trạng thái | Hoàn thành | Notes |
|-------|--------|------------|------------|-------|
| 1 | Cổ phiếu | ✅ **COMPLETED** | 100% | vnstock_ta v0.2.0, F-Score, Price scaling fix |
| 2 | Chỉ số | ✅ **COMPLETED** | 95% | Market Breadth, Index OHLCV, pending dashboard integration |
| 3 | Kim loại + Phái sinh | 🔴 Chưa bắt đầu | 0% | |
| 4 | Các nhóm còn lại | 🔴 Chưa bắt đầu | 0% | |
| 5 | Tích hợp | 🔴 Chưa bắt đầu | 0% | |

**Tổng tiến độ**: 35% (2/5 phases)

---

## 15. GHI CHÚ & UPDATES

### 2026-04-24
- ✅ Tạo roadmap document
- ✅ Hoàn thành ví dụ output cho **tất cả 9 nhóm chức năng**
- ✅ **IMPLEMENT Phase 1**: Stock Analysis Module
  - Tạo `dashboard/analyzers/stock_analyzer.py` với đầy đủ chỉ báo
  - Tạo `dashboard/analyzers/signals.py` với signal definitions
  - Thêm `real_stock_analysis()` vào `runners.py`
  - Đăng ký function vào `registry.py`
- ✅ **FIXES Phase 1**:
  - Updated to use `vnstock_ta` v0.2.0 API (`Indicator` class instead of `MomentumIndicator`/`TrendIndicator`/`VolatilityIndicator`)
  - Fixed F-Score calculation with correct column names from `vnstock_data`
  - Fixed P/E, P/B extraction from ratio API
  - Added ROE calculation from P/B ÷ P/E formula
  - **Test Results**: VCB ✅ (P/E=13.7, P/B=1.6, ROE=11.8%, F-Score=2/9), TCB ✅ (F-Score=2/9, P/E=P/B=0 from API source)

### 2026-04-25
- ✅ Phase 1 Test with real data - Technical Analysis working
  - All 9 indicators: RSI, MACD, ADX, SMA, Bollinger, VWAP, CMF, MFI, SuperTrend ✅
  - Valuation: P/E, P/B, ROE ✅ (VCB, HPG working; TCB=0 from source)
  - F-Score: 2/9 ✅ (Fixed, was 0/9)
  - **CRITICAL FIX**: API returns prices divided by 1000 - added multiplication factor
    - VCB: 60,600 VND ✅ (was showing 61)
    - TCB: 34,250 VND ✅ (was showing 34)
    - HPG: 27,900 VND ✅ (was showing 28)
  - **Moved to Phase 2** after 2 failed attempts on F-Score

---

## 16. CÁCH SỬ DỤNG

### Sử dụng trong Dashboard
1. Khởi động dashboard: `python manage.py runserver`
2. Tìm nhóm **"Phân tích đầu tư"** trong menu
3. Chọn **"Phân tích cổ phiếu toàn diện"**
4. Nhập symbol (VD: VCB, ACB, FPT)
5. Xem kết quả phân tích

### Sử dụng trong Python Code
```python
from dashboard.analyzers import StockAnalyzer, analyze_stock

# Method 1: Using analyzer class
analyzer = StockAnalyzer()
result = analyzer.analyze("VCB")
print(analyzer.to_string(result))

# Method 2: Using convenience function
result = analyze_stock("ACB")
print(analyzer.to_dict(result))
```

### Output bao gồm
- **Technical Analysis**: RSI, MACD, ADX, SuperTrend, SMA, CMF, MFI, Bollinger, VWAP
- **Fundamental Analysis**: F-Score, P/E, P/B, ROE, EPS
- **AI Recommendation**: Master Score, BUY/SELL/HOLD, Entry/Exit levels

---

## 17. NEXT ACTIONS

1. ✅ Review và approve roadmap
2. ✅ Confirm ví dụ output cho tất cả các nhóm
3. ✅ Implement Phase 1 (Cổ phiếu)
4. ⏳ Test Phase 1 với các mã VN30
5. ⏳ Bắt đầu Phase 2 (Chỉ số thị trường)

---

**Hướng dẫn tiếp theo**: Chạy dashboard và test với các mã cổ phiếu để xác nhận module hoạt động đúng.
