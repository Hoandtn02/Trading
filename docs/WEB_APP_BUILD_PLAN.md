# Kế hoạch xây dựng web điều khiển chức năng Vnstock

## 1. Mục tiêu
Xây dựng một web ứng dụng cho phép người dùng:

- xem danh sách các chức năng dữ liệu của Vnstock
- chọn một chức năng bằng giao diện trực quan
- nhập tham số cần thiết
- bấm chạy ngay trên web
- nhận kết quả trả về dưới dạng bảng, JSON hoặc biểu đồ

Mục tiêu của sản phẩm là biến Vnstock từ một thư viện Python thành một bảng điều khiển chức năng tương tác cho người dùng không cần viết code.

## 2. Hướng đi được quyết định

### Hướng kiến trúc
Chọn mô hình Function Registry + Execution API + Dynamic UI.

Nghĩa là:

- mỗi chức năng của Vnstock được khai báo bằng metadata
- frontend đọc metadata đó để hiển thị danh sách chức năng và form nhập tham số
- backend chỉ cho phép chạy các hàm nằm trong danh sách trắng
- kết quả được chuẩn hóa để hiển thị đồng nhất trên giao diện

### Lý do chọn hướng này

- an toàn hơn so với cho người dùng nhập code trực tiếp
- dễ mở rộng khi thêm chức năng mới
- phù hợp với các hàm có tham số khác nhau như `symbol`, `start`, `end`, `period`, `source`
- có thể tái sử dụng tốt với các nhóm chức năng trong README
- dễ nâng cấp từ MVP lên bản hoàn chỉnh

## 3. Phạm vi chức năng ban đầu
Dựa trên README, web nên ưu tiên các nhóm chức năng sau trước:

### 3.1. Nhóm cổ phiếu
- giá lịch sử
- intraday
- thông tin công ty
- báo cáo tài chính
- bảng giá giao dịch
- danh sách mã niêm yết

### 3.2. Nhóm thị trường
- index
- CW
- ETF / quỹ mở
- trái phiếu
- futures

### 3.3. Nhóm dữ liệu khác
- forex
- crypto
- vàng
- tin tức và sự kiện tài chính

### 3.4. Nhóm tiện ích
- tìm mã
- xem lịch sử truy vấn
- tải dữ liệu ra CSV hoặc Excel

## 4. Trải nghiệm người dùng mong muốn

### Màn hình chính
- sidebar hiển thị nhóm chức năng
- ô tìm kiếm để lọc nhanh chức năng
- danh sách function cards ở giữa
- panel bên phải để nhập tham số và xem kết quả

### Khi người dùng chọn một chức năng
Web sẽ hiển thị:

1. mô tả ngắn
2. danh sách tham số
3. giá trị mặc định gợi ý
4. nút Run
5. khu vực kết quả

### Cách hiển thị kết quả
- nếu dữ liệu dạng bảng: hiển thị table
- nếu là chuỗi thời gian: hiển thị table và chart
- nếu là dữ liệu cấu trúc: hiển thị JSON viewer
- nếu lỗi: hiển thị thông báo dễ hiểu

## 5. Kiến trúc hệ thống đề xuất

### 5.1. Frontend
Khuyến nghị dùng:

- Django Templates
- HTMX
- Tailwind CSS hoặc Bootstrap 5
- Alpine.js nếu cần tương tác nhẹ
- TanStack Table nếu render bảng bằng JavaScript
- ECharts hoặc Chart.js cho biểu đồ

### 5.2. Backend
Khuyến nghị dùng:

- Django
- Django ORM để lưu dữ liệu và quản lý lịch sử truy vấn
- Python để gọi trực tiếp vnstock
- xác thực tham số bằng schema hoặc form validation
- trả response theo JSON hoặc HTML partial thống nhất

### 5.3. Execution layer
Backend chỉ chạy các chức năng đã khai báo trong registry.

Mỗi function trong registry nên có:

- id
- label
- group
- description
- params
- output_type
- example
- runner

## 6. Luồng hoạt động

1. Người dùng mở web
2. Frontend gọi API lấy danh sách chức năng
3. Người dùng chọn một chức năng
4. Frontend render form theo schema tham số
5. Người dùng nhập giá trị và bấm chạy
6. Frontend gửi request đến backend
7. Backend validate tham số
8. Backend gọi hàm Vnstock tương ứng
9. Backend chuẩn hóa dữ liệu đầu ra
10. Frontend hiển thị kết quả

## 7. Thiết kế API backend

### 7.1. GET /api/functions
Trả về danh sách chức năng có thể chạy.

Response gồm:

- thông tin nhóm
- tên chức năng
- mô tả
- schema tham số
- loại dữ liệu trả về

### 7.2. POST /api/execute
Nhận:

- function_id
- params

Backend trả về:

- status
- data
- columns
- rows
- chart
- error nếu có

### 7.3. GET /api/history
Trả về lịch sử các truy vấn gần nhất của người dùng, lưu bằng Django ORM.

### 7.4. GET /api/health
Kiểm tra trạng thái hệ thống.

## 8. Chuẩn hóa dữ liệu trả về

### 8.1. Với DataFrame
Chuyển sang:

- list of records
- danh sách cột
- số dòng

### 8.2. Với Series
Chuyển sang:

- key/value pairs
- hoặc table 2 cột

### 8.3. Với text hoặc dict
Trả nguyên JSON để frontend render.

### 8.4. Với lỗi
Trả thông báo ngắn, rõ ràng, có gợi ý sửa.

## 9. Quy tắc an toàn

- không cho người dùng nhập và chạy Python code tự do
- chỉ cho gọi các hàm có trong danh sách trắng
- giới hạn kiểu và phạm vi tham số
- kiểm tra định dạng ngày, mã chứng khoán, lựa chọn period, source
- cache các truy vấn phổ biến nếu cần
- giới hạn tần suất request để tránh quá tải dữ liệu

## 10. MVP đề xuất
Bản đầu tiên chỉ cần:

- danh sách chức năng
- form nhập tham số động
- chạy một chức năng bất kỳ
- hiển thị bảng kết quả
- hiển thị lỗi
- lịch sử 10 truy vấn gần nhất

## 11. Các bước triển khai tiếp theo

### Bước 1
Tạo file registry mô tả các chức năng từ README.

### Bước 2
Xây FastAPI backend với endpoint danh sách và thực thi chức năng.

### Bước 3
Xây frontend động để render danh sách chức năng và form tham số.

### Bước 4
Thêm bảng, chart và export dữ liệu.

### Bước 5
Thêm cache, lịch sử, đăng nhập nếu cần.

## 12. Kết luận
Hướng đi phù hợp nhất cho project này là xây một web điều khiển chức năng Vnstock theo registry bằng Django, nơi mỗi chức năng được mô tả rõ, có form nhập tham số, có nút chạy và có vùng hiển thị kết quả ngay lập tức. Cách làm này cân bằng được giữa tính an toàn, khả năng mở rộng, lưu dữ liệu bằng Django ORM và trải nghiệm người dùng.

## 13. Tiến độ thực tế đã hoàn thành

### 13.1. Hoàn thành
- [x] Dựng `Function Registry` theo README với đầy đủ nhóm chức năng chính
- [x] Gắn trạng thái chức năng theo 4 mức: `ready`, `partial`, `disabled`, `planned`
- [x] Seed dữ liệu registry vào DB qua `FunctionGroup` và `FunctionDefinition`
- [x] Dựng dashboard 3 cột: nhóm chức năng, danh sách function, panel chạy function
- [x] Có tìm kiếm theo `q` và lọc theo nhóm `group`
- [x] Có lọc theo trạng thái chức năng `status`
- [x] Có khung lịch sử chạy (`ExecutionResult`) và màn hình lịch sử riêng
- [x] Có khung hiển thị kết quả theo `table` / `json` / `chart` (placeholder)
- [x] Có khung nút UI cho `Lưu preset`, `Export CSV/Excel`, `Mở chart`
- [x] Giữ README làm nguồn chuẩn, không chỉnh sửa nội dung README

### 13.2. Đang làm
- [ ] Nối dữ liệu thật cho nhóm vàng, chỉ số thị trường, phái sinh, quỹ, crypto
- [ ] Hoàn thiện lịch sử chạy nâng cao (lọc sâu, phân trang, lưu mẫu truy vấn)
- [ ] Tối ưu hiệu năng và cache cho các truy vấn nặng

### 13.3. Chưa làm
- [ ] Xác thực người dùng (login/đăng ký) nếu cần
- [ ] Triển khai production (collectstatic, gunicorn, database cấu hình)

### 13.4. Ghi chú triển khai chi tiết

#### Preset (hoàn thành 2026-04-15)
- Model `UserPreset` đã có sẵn (name, function FK, params JSON)
- Thêm URL `preset/save/` (POST) và `preset/load/<function_id>/` (HTMX GET)
- Template: nút "Lưu preset" mở modal, nhập tên → gửi POST → lưu DB
- Template: khung "Preset đã lưu" tự động tải lại, bấm "Áp dụng" → fill lại form
- JS: `getFormData()` đọc toàn bộ field form, `loadPreset(params)` điền lại

#### Export CSV/Excel (hoàn thành 2026-04-15)
- JS: `exportResult('csv')` → parse table trong `#result-panel` → generate CSV → download
- JS: `exportResult('xlsx')` → generate XML Excel (SpreadsheetML) → download
- Không cần thư viện phụ thuộc, dùng pure JS + Data URI

#### Chart thời gian (hoàn thành 2026-04-15)
- Thêm ECharts CDN vào template
- JS: `openChart()` tìm cột ngày + cột số đầu tiên trong bảng kết quả
- Vẽ line chart với smooth curve + area fill, tooltip, dark theme
- Tự tạo `#chart-area` div nếu chưa có, hoặc cập nhật chart có sẵn

#### Runner thật cho cổ phiếu (hoàn thành 2026-04-15)
- `runners.py`: viết hàm thật dùng `vnstock.Quote`, `vnstock.Finance`, `vnstock.Company`
- Các hàm đã nối: `real_stock_quote_realtime`, `real_stock_intraday`, `real_stock_historical`, `real_stock_financial_reports`, `real_stock_financial_ratios`, `real_company_profile`, `real_stock_news`
- Thêm function mới `stock_historical` (giá lịch sử theo ngày/tuần/tháng)
- Thêm function mới `stock_news` (tin tức cổ phiếu)
- Registry: chuyển 6 function cổ phiếu từ `partial` → `ready`, trỏ sang runner thật
- Mô hình xử lý lỗi: try/except wrapper trả về payload với `{"error": str(exc)}`
