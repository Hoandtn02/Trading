# Tài liệu Tích hợp Hệ thống: TradingView API & Vnstock (Hybrid Model)

**Phiên bản:** 1.0
**Mục đích:** Đặc tả quy trình chuyển đổi kiến trúc thu thập dữ liệu từ thuần túy sử dụng `vnstock` sang mô hình lai (Hybrid), tận dụng thế mạnh của **TradingView API** cho phân tích kỹ thuật (TA) và **Vnstock** cho phân tích cơ bản (FA) & dòng tiền thị trường Việt Nam.

---

## 1. Tổng quan Kiến trúc Mới (Hybrid Architecture)

Hệ thống phân tích giao dịch hiện tại đang phụ thuộc hoàn toàn vào hệ sinh thái `vnstock` (`vnstock_data`, `vnstock_ta`) cho mọi tác vụ từ lấy nến giá (OHLCV) đến tính toán chỉ báo và lấy báo cáo tài chính.

Với việc bổ sung thư viện `TradingView-API` (`@mathieuc/tradingview`), kiến trúc sẽ được phân tách nhiệm vụ (Separation of Concerns):
- **Node.js Service (TradingView API):** Đảm nhiệm việc stream dữ liệu nến (Real-time), kéo lịch sử giá phân giải cao và tính toán/trích xuất các chỉ báo kỹ thuật gốc.
- **Python Django Service (Vnstock):** Đảm nhiệm việc thu thập dữ liệu định giá, báo cáo tài chính, danh sách mã, và giao dịch khối lượng của quỹ/khối ngoại.
- **Analyzer Engine:** Nơi tổng hợp dữ liệu từ cả hai nguồn để đưa ra tín hiệu (Signals).

---

## 2. Phân tích & Đối chiếu Dữ liệu: TradingView API vs. Vnstock

Dưới đây là bảng đối chiếu chi tiết các nhóm dữ liệu mà hệ thống yêu cầu, chỉ rõ những gì TradingView API **có** và **không có** để phân bổ nhiệm vụ hợp lý.

### 2.1. Dữ liệu Giá & Khối lượng (Market Data - OHLCV)

| Loại dữ liệu / Tài sản | TradingView API | Vnstock / Vnstock_data | Quyết định tích hợp |
| :--- | :--- | :--- | :--- |
| **Cổ phiếu VN (HOSE/HNX/UPCOM)** | ✅ Cực nhanh, hỗ trợ Intraday, Real-time tốt. (Mã: `HNX:SHS`, `HOSE:SSI`) | ✅ Dữ liệu EOD chuẩn, Intraday bị giới hạn rate-limit. | **Chuyển sang TradingView API** để lấy nến và theo dõi giá real-time. |
| **Crypto, Forex, Vàng thế giới** | ✅ Dữ liệu toàn cầu, cực kỳ chi tiết (`BINANCE:BTCUSDT`, `FX:EURUSD`). | ⚠️ Chỉ có một số tỷ giá nội địa (VCB) và vàng SJC/DOJI. | **Chuyển 100% sang TradingView API.** |
| **Phái sinh VN (VN30F...)** | ✅ Có hỗ trợ tùy nguồn cấp. | ✅ Hỗ trợ đầy đủ dữ liệu nội địa. | **TradingView API** làm chính, backup bằng Vnstock. |
| **Chứng quyền (CW), CC Quỹ nội địa** | ❌ Thiếu hụt hoặc mã không chuẩn hóa. | ✅ Đầy đủ (NAV, giá CW). | **Giữ lại Vnstock** để lấy dữ liệu. |

### 2.2. Chỉ báo Phân tích Kỹ thuật (Technical Indicators)

| Loại Chỉ báo | TradingView API | Vnstock_ta | Khả năng thay thế |
| :--- | :--- | :--- | :--- |
| **RSI, MACD, ADX, SMA/EMA** | ✅ Tính toán phía Server TV, độ chính xác 100% như trên web. | ✅ Tự tính bằng Python (đôi khi lệch thông số mượt). | Thay thế bằng **TradingView API**. |
| **Bollinger Bands, SuperTrend** | ✅ Hỗ trợ gọi thẳng Pine Script gốc. | ✅ Phải tự config thuật toán phức tạp. | Thay thế bằng **TradingView API**. |
| **CMF (Chaikin Money Flow), MFI** | ✅ Hỗ trợ đầy đủ. | ✅ Hỗ trợ cơ bản. | Thay thế bằng **TradingView API**. |
| **Custom Pine Script (Chỉ báo tự viết)** | ✅ Có thể chạy nếu tài khoản TV có quyền truy cập. | ❌ Không hỗ trợ mã Pine. | **Độc quyền TradingView API.** |

### 2.3. Báo cáo tài chính & Thông tin doanh nghiệp (Fundamentals & Metadata)

| Số liệu / Thông tin | TradingView API | Vnstock | Phân tích giới hạn của TradingView API |
| :--- | :--- | :--- | :--- |
| **Danh sách mã & Ngành nghề** | ✅ Có screener nhưng phân ngành chuẩn quốc tế. | ✅ Chuẩn ICB, phù hợp TTCK Việt Nam. | Dùng Vnstock để chuẩn hóa phân ngành VN. |
| **P/E, P/B, EPS, ROE, ROA** | ⚠️ Có nhưng chậm cập nhật đối với thị trường VN. | ✅ Cập nhật tức thời từ các CTCK VN. | **Bắt buộc dùng Vnstock**. |
| **BCTC Quý (Doanh thu, Lợi nhuận)** | ❌ Rất thiếu hoặc không sát với chuẩn VAS của Việt Nam. | ✅ Dữ liệu đầy đủ (Bảng CĐKT, KQKD, LCTT). | **Bắt buộc dùng Vnstock**. |
| **F-Score (Chấm điểm tài chính)** | ❌ Không có sẵn. | ⚠️ Không cung cấp trực tiếp, nhưng cung cấp dữ liệu thô (ROA, ROC) để hệ thống tự tính F-Score. | **Dùng Vnstock lấy dữ liệu thô, tự tính**. |

### 2.4. Dữ liệu Dòng tiền & Giao dịch đặc thù (Smart Money Flow)

| Loại dữ liệu | TradingView API | Vnstock | Phân tích giới hạn của TradingView API |
| :--- | :--- | :--- | :--- |
| **Khối ngoại Mua/Bán ròng** | ❌ **Không có** dữ liệu định danh riêng cho khối ngoại tại VN. | ✅ Chi tiết từng ngày, từng mã. | **Giới hạn lớn nhất của TV API**. Đây là dữ liệu sống còn ở VN, phải dùng Vnstock. |
| **Tự doanh Mua/Bán ròng** | ❌ Không có. | ✅ Có dữ liệu chi tiết. | Bắt buộc dùng Vnstock. |

---

## 3. Quy trình Tích hợp Đồng bộ (Integration Workflow)

Để kết hợp hai nguồn dữ liệu không đồng nhất thành một luồng xử lý tín hiệu hợp nhất, quy trình sau cần được thiết lập:

### Bước 1: Symbol Mapping (Chuẩn hóa Mã giao dịch)
*   TradingView yêu cầu định dạng `EXCHANGE:SYMBOL` (VD: `HOSE:SSI`, `HNX:SHS`).
*   Vnstock sử dụng định dạng ticker thuần (VD: `SSI`, `SHS`).
*   **Quy trình:** Tạo một mapping table (hoặc hàm chuyển đổi) trong Django. Khi phân tích mã `SSI`, hệ thống sẽ truy vấn `HOSE:SSI` qua microservice Node.js của TradingView.

### Bước 2: Khởi tạo Microservice TradingView (Node.js)
Do thư viện `@mathieuc/tradingview` chạy trên Node.js/Bun, ta cần viết một REST API hoặc gRPC server nhỏ:
1.  Nhận yêu cầu: `{ "symbol": "HOSE:SSI", "indicators": ["RSI", "MACD"], "timeframe": "1D" }`.
2.  Dùng thư viện gọi hàm `getCandles` và `getIndicatorData`.
3.  Trả về JSON mảng dữ liệu đã chuẩn hóa timestamp.

### Bước 3: Đồng bộ Timezone & Merge Dữ liệu (Python Django)
Tại lớp phân tích (`dashboard/analyzers/stock_analyzer.py`), Python sẽ gọi:
1.  API nội bộ Node.js lấy OHLCV + Tín hiệu kỹ thuật (RSI, MACD) theo chuẩn **UTC Unix Timestamp**.
2.  `vnstock_data` lấy dữ liệu BCTC thô (để hệ thống tự tính F-Score) và Khối ngoại Mua/Bán theo chuẩn **Asia/Ho_Chi_Minh**.
3.  **Hợp nhất (Merge):** Dùng `pandas.merge_asof` hoặc join theo ngày (Date) để ghép dữ liệu Fundamental (Ví dụ EPS quý) và Dòng tiền khối ngoại vào từng thanh nến ngày tương ứng của TradingView.

### Bước 4: Chạy Strategy Engine
Hệ thống AI/Simulator lúc này sẽ có một tập DataFrame hoàn chỉnh bao gồm:
`[Date, Open, High, Low, Close, Volume, RSI_TV, MACD_TV, Foreign_Buy_Val, EPS, PE]`
Từ đó đưa ra các quyết định Backtest hoặc Trading an toàn và chính xác nhất.

---

## 4. Tổng kết

Việc chuyển hướng sang dùng **TradingView API** là một bước tiến chiến lược, giúp giải quyết triệt để bài toán **Real-time, giới hạn request (Rate Limit) và độ chính xác của các chỉ báo phân tích kỹ thuật phức tạp**. 

Tuy nhiên, **TradingView API hoàn toàn mù tịt về cơ cấu dòng tiền đặc thù (Khối ngoại, Tự doanh) và chuẩn mực kế toán tài chính (BCTC) của Việt Nam**. Do đó, sự tồn tại của `vnstock` trong hệ thống là không thể thay thế đối với mảng phân tích cơ bản. Mô hình kiến trúc Lai (Node.js + Python) như đặc tả trên là giải pháp tối ưu nhất để xây dựng một cỗ máy giao dịch hoàn hảo.
