# Hướng dẫn chạy Vnstock Dashboard

## Yêu cầu

- Python 3.10 trở lên
- Windows / macOS / Linux
- Mạng internet (để lấy dữ liệu chứng khoán từ API)
- **Gói thành viên Silver/Golden** (để sử dụng đầy đủ tính năng)

---

## 1. Môi trường Python

Dashboard sử dụng **Unified UI** (`vnstock_data`) cần **gói Silver trở lên**.

### Cách 1: Dùng môi trường có sẵn (Khuyến nghị)

Nếu bạn đã cài qua `vnstock-installer`, môi trường đã có đủ thư viện:

```powershell
# Windows PowerShell
& "$env:USERPROFILE\.venv\Scripts\python.exe" manage.py runserver
```

```bash
# macOS / Linux
~/.venv/bin/python manage.py runserver
```

### Cách 2: Tạo môi trường mới

```bash
# Tạo môi trường ảo
python -m venv .venv

# Kích hoạt môi trường
# Windows PowerShell:
.venv\Scripts\activate

# macOS / Linux:
source .venv/bin/activate

# Cài đặt thư viện (yêu cầu gói Silver+)
pip install django django-htmx pandas
pip install --index-url https://vnstocks.com/api/simple vnstock_data
```

---

## 2. Chạy migration (tạo database)

```bash
python manage.py migrate
```

Thao tác này tạo file `db.sqlite3` và các bảng cần thiết cho dashboard.

---

## 3. Khởi động server

```powershell
# Windows PowerShell - Dùng môi trường ~/.venv
& "$env:USERPROFILE\.venv\Scripts\python.exe" manage.py runserver
```

```bash
# macOS / Linux
~/.venv/bin/python manage.py runserver
```

Mở trình duyệt và truy cập:

```
http://127.0.0.1:8000/
```

---

## 4. Kiểm tra môi trường

Để xác nhận `vnstock_data` hoạt động:

```bash
python -c "from vnstock_data import Market; print('OK')"
```

Nếu lỗi `No module named 'vnstock_data'`, đảm bảo đang dùng Python từ `~/.venv`.

---

## 5. Các màn hình chính

| URL | Mô tả |
|---|---|
| `/` | Màn hình chính – danh sách chức năng, form nhập tham số, kết quả |
| `/history/` | Lịch sử các lần chạy gần nhất |

---

## 6. Cách sử dụng

### 6.1. Chạy một chức năng

1. Chọn **nhóm chức năng** ở sidebar bên trái (ví dụ: **Cổ phiếu**)
2. Chọn **chức năng** trong danh sách giữa màn hình (ví dụ: **Giá lịch sử**)
3. Nhập **tham số** trong form bên phải (mã cổ phiếu, ngày bắt đầu, ngày kết thúc…)
4. Bấm **Chạy thử**
5. Kết quả hiển thị ngay bên dưới form

### 6.2. Lưu preset

Sau khi nhập tham số ưng ý:

1. Bấm **Lưu preset** bên dưới form
2. Nhập tên preset (ví dụ: `FPT daily 2024`)
3. Bấm **Lưu**
4. Preset sẽ xuất hiện trong khung **Preset đã lưu** bên dưới
5. Bấm **Áp dụng** để điền lại tham số nhanh

### 6.3. Export dữ liệu

Sau khi có kết quả dạng bảng, bấm:

- **Export CSV** – tải file `.csv`
- **Export Excel** – tải file `.xls`

### 6.4. Vẽ biểu đồ

Sau khi có kết quả (ví dụ: giá lịch sử), bấm **Mở chart**.

Hệ thống tự tìm cột ngày và cột số trong bảng kết quả, vẽ line chart tương ứng bằng ECharts.

---

## 7. Các trạng thái chức năng

| Trạng thái | Ý nghĩa |
|---|---|
| `ready` | Đã nối dữ liệu thật – có thể chạy ngay |
| `partial` | Có khung UI nhưng chưa nối dữ liệu đầy đủ |
| `planned` | Đã có trong registry, chưa triển khai |
| `disabled` | Tạm thời không hoạt động |

Nhóm **Cổ phiếu** hiện đã ở trạng thái `ready` hết (nối `vnstock` thật).

---

## 8. Xem lịch sử chạy

Truy cập `/history/` để xem 100 lần chạy gần nhất, gồm:
- Tên chức năng
- Tham số đã dùng
- Thời gian chạy
- Trạng thái (thành công / lỗi)

---

## 9. Xử lý lỗi thường gặp

### Lỗi `ModuleNotFoundError: No module named 'dashboard'`

Đảm bảo đang chạy đúng thư mục gốc project và đã kích hoạt `.venv`:

```bash
cd c:\Users\lantr\Downloads\vnstock-main\vnstock-main
.venv\Scripts\activate
python manage.py runserver
```

### Lỗi `no such table`

Chạy lại migration:

```bash
python manage.py migrate
```

### Lỗi khi chạy chức năng cổ phiếu

Kiểm tra đã cài `vnstock`:

```bash
pip show vnstock
```

Nếu chưa, cài lại:

```bash
pip install vnstock
```

---

## 10. Thông tin kỹ thuật

| Thành phần | Công nghệ |
|---|---|
| Backend | Django 5 |
| Frontend | Django Templates + Tailwind CSS inline |
| Tương tác | HTMX (AJAX không cần viết JS) |
| Biểu đồ | ECharts 5 |
| Database | SQLite 3 (`db.sqlite3`) |
| Dữ liệu | `vnstock_data` Unified UI (gói Silver+) |

---

## 11. Cấu trúc thư mục dashboard

```
dashboard/
├── models.py          # FunctionGroup, FunctionDefinition, ExecutionResult, UserPreset
├── views.py           # home, run_function, save_preset, load_presets, history
├── urls.py            # Định tuyến URL
├── registry.py        # Khai báo metadata tất cả chức năng
├── runners.py         # Hàm thật gọi vnstock cho từng chức năng
├── services.py        # Logic chung: iter_registry, run_registry_function
├── forms.py           # DynamicFunctionForm sinh form theo param_schema
├── templates/dashboard/
│   ├── home.html      # Giao diện chính
│   ├── history.html   # Lịch sử chạy
│   └── result_partial.html  # Kết quả trả về (HTMX)
└── templatetags/
    └── dashboard_extras.py  # Filter: get_item, json_dumps, pprint
```
