FUNCTION_REGISTRY = [
    {
        "group": {
            "name": "Nền tảng chung",
            "slug": "core",
            "description": "Truy xuất dữ liệu qua API đơn giản và làm nền cho các nhóm dữ liệu khác.",
        },
        "functions": [
            {
                "function_id": "api_quickstart",
                "label": "Truy xuất dữ liệu qua API đơn giản",
                "status": "ready",
                "description": "Điểm vào nhanh để gọi dữ liệu từ web mà không phải viết code.",
                "runner_path": "dashboard.runners.placeholder_api_quickstart",
                "output_type": "json",
                "param_schema": {
                    "symbol": {"type": "string", "required": False, "default": "ACB"},
                    "source": {"type": "string", "required": False, "default": "KBS"},
                },
            },
            {
                "function_id": "readme_registry",
                "label": "Seed registry từ README",
                "status": "ready",
                "description": "Xem toàn bộ registry được seed từ nội dung README.",
                "runner_path": "dashboard.runners.placeholder_registry_overview",
                "output_type": "table",
                "param_schema": {},
            },
        ],
    },
    {
        "group": {"name": "Danh sách mã", "slug": "listing", "description": "Danh sách mã chứng khoán, nhóm cổ phiếu, chỉ số."},
        "functions": [
            {
                "function_id": "listing_all_symbols",
                "label": "Danh sách mã niêm yết",
                "status": "ready",
                "description": "Danh sách toàn bộ mã và tên cổ phiếu trên thị trường Việt Nam.",
                "runner_path": "dashboard.runners.real_listing_all_symbols",
                "output_type": "table",
                "param_schema": {
                    "source": {"type": "string", "required": False, "default": "vci"},
                },
            },
            {
                "function_id": "listing_by_exchange",
                "label": "Danh sách theo sàn",
                "status": "ready",
                "description": "Danh sách mã chứng khoán theo sàn HOSE, HNX, UPCOM.",
                "runner_path": "dashboard.runners.real_listing_by_exchange",
                "output_type": "table",
                "param_schema": {
                    "source": {"type": "string", "required": False, "default": "vci"},
                },
            },
            {
                "function_id": "listing_by_group",
                "label": "Danh sách mã theo nhóm",
                "status": "ready",
                "description": "Danh sách mã theo nhóm VN30, VN100, HNX, ETF...",
                "runner_path": "dashboard.runners.real_listing_by_group",
                "output_type": "table",
                "param_schema": {
                    "source": {"type": "string", "required": False, "default": "vci"},
                    "group": {"type": "string", "required": False, "default": "VN30"},
                },
            },
            {
                "function_id": "listing_all_indices",
                "label": "Danh sách chỉ số",
                "status": "ready",
                "description": "Danh sách tất cả chỉ số tiêu chuẩn VN30, VNMID, VN100...",
                "runner_path": "dashboard.runners.real_listing_all_indices",
                "output_type": "table",
                "param_schema": {
                    "source": {"type": "string", "required": False, "default": "vci"},
                },
            },
        ],
    },
    {
        "group": {"name": "Bảng giá", "slug": "priceboard", "description": "Bảng giá realtime cho nhiều mã chứng khoán."},
        "functions": [
            {
                "function_id": "price_board",
                "label": "Bảng giá realtime",
                "status": "ready",
                "description": "Giá realtime cho danh sách mã chứng khoán (lô chẵn).",
                "runner_path": "dashboard.runners.real_price_board",
                "output_type": "table",
                "param_schema": {
                    "symbols": {"type": "string", "required": False, "default": "ACB,VNM,HPG,FPT"},
                    "source": {"type": "string", "required": False, "default": "kbs"},
                },
            },
        ],
    },
    {
        "group": {"name": "Cổ phiếu", "slug": "stocks", "description": "Giá realtime, intraday, báo cáo tài chính, chỉ số tài chính và thông tin doanh nghiệp."},
        "functions": [
            {
                "function_id": "stock_quote_realtime",
                "label": "Giá realtime / quote",
                "status": "ready",
                "description": "Giá giao dịch hiện tại của cổ phiếu.",
                "runner_path": "dashboard.runners.real_stock_quote_realtime",
                "output_type": "json",
                "param_schema": {
                    "symbol": {"type": "string", "required": True, "default": "ACB"},
                    "source": {"type": "string", "required": False, "default": "vci"},
                },
            },
            {
                "function_id": "stock_intraday",
                "label": "Intraday",
                "status": "ready",
                "description": "Dữ liệu khớp lệnh theo từng tick.",
                "runner_path": "dashboard.runners.real_stock_intraday",
                "output_type": "table",
                "param_schema": {
                    "symbol": {"type": "string", "required": True, "default": "ACB"},
                    "source": {"type": "string", "required": False, "default": "vci"},
                    "page_size": {"type": "integer", "required": False, "default": 100},
                },
            },
            {
                "function_id": "stock_historical",
                "label": "Giá lịch sử",
                "status": "ready",
                "description": "Giá theo ngày/tuần/tháng.",
                "runner_path": "dashboard.runners.real_stock_historical",
                "output_type": "table",
                "param_schema": {
                    "symbol": {"type": "string", "required": True, "default": "ACB"},
                    "source": {"type": "string", "required": False, "default": "vci"},
                    "start_date": {"type": "date", "required": False, "default": ""},
                    "end_date": {"type": "date", "required": False, "default": ""},
                    "resolution": {"type": "string", "required": False, "default": "daily"},
                },
            },
            {
                "function_id": "stock_financial_reports",
                "label": "Báo cáo tài chính",
                "status": "ready",
                "description": "Bảng cân đối, kết quả kinh doanh, lưu chuyển tiền tệ.",
                "runner_path": "dashboard.runners.real_stock_financial_reports",
                "output_type": "table",
                "param_schema": {
                    "symbol": {"type": "string", "required": True, "default": "FPT"},
                    "source": {"type": "string", "required": False, "default": "vci"},
                    "report_type": {"type": "string", "required": False, "default": "balance_sheet"},
                    "period": {"type": "string", "required": False, "default": "quarter"},
                    "lang": {"type": "string", "required": False, "default": "vi"},
                },
            },
            {
                "function_id": "stock_financial_ratios",
                "label": "Chỉ số tài chính",
                "status": "ready",
                "description": "Các chỉ số tài chính của doanh nghiệp.",
                "runner_path": "dashboard.runners.real_stock_financial_ratios",
                "output_type": "table",
                "param_schema": {
                    "symbol": {"type": "string", "required": True, "default": "FPT"},
                    "source": {"type": "string", "required": False, "default": "vci"},
                    "period": {"type": "string", "required": False, "default": "quarter"},
                },
            },
            {
                "function_id": "company_profile",
                "label": "Thông tin doanh nghiệp chi tiết",
                "status": "ready",
                "description": "Tổng quan và thông tin chi tiết doanh nghiệp.",
                "runner_path": "dashboard.runners.real_company_profile",
                "output_type": "json",
                "param_schema": {
                    "symbol": {"type": "string", "required": True, "default": "FPT"},
                    "source": {"type": "string", "required": False, "default": "vci"},
                },
            },
            {
                "function_id": "stock_news",
                "label": "Tin tức cổ phiếu",
                "status": "ready",
                "description": "Tin tức liên quan đến cổ phiếu.",
                "runner_path": "dashboard.runners.real_stock_news",
                "output_type": "table",
                "param_schema": {
                    "symbol": {"type": "string", "required": True, "default": "FPT"},
                    "source": {"type": "string", "required": False, "default": "vci"},
                },
            },
        ],
    },
    {
        "group": {"name": "Chỉ số thị trường", "slug": "indices", "description": "VNIndex, HNXIndex, UPCOM và các index quốc tế."},
        "functions": [
            {
                "function_id": "vnindex",
                "label": "VNIndex",
                "status": "ready",
                "description": "Chỉ số VNIndex - biến động toàn bộ thị trường HOSE.",
                "runner_path": "dashboard.runners.real_index_history",
                "output_type": "table",
                "param_schema": {
                    "symbol": {"type": "string", "required": False, "default": "VNINDEX"},
                    "start_date": {"type": "date", "required": False, "default": ""},
                    "end_date": {"type": "date", "required": False, "default": ""},
                    "resolution": {"type": "string", "required": False, "default": "daily"},
                },
            },
            {
                "function_id": "hnxindex",
                "label": "HNXIndex",
                "status": "ready",
                "description": "Chỉ số HNXIndex trên sàn HNX.",
                "runner_path": "dashboard.runners.real_index_history",
                "output_type": "table",
                "param_schema": {
                    "symbol": {"type": "string", "required": False, "default": "HNXINDEX"},
                    "start_date": {"type": "date", "required": False, "default": ""},
                    "end_date": {"type": "date", "required": False, "default": ""},
                    "resolution": {"type": "string", "required": False, "default": "daily"},
                },
            },
            {
                "function_id": "upcom_index",
                "label": "UPCOM",
                "status": "ready",
                "description": "Chỉ số UPCOM trên sàn UPCOM.",
                "runner_path": "dashboard.runners.real_index_history",
                "output_type": "table",
                "param_schema": {
                    "symbol": {"type": "string", "required": False, "default": "UPCOMINDEX"},
                    "start_date": {"type": "date", "required": False, "default": ""},
                    "end_date": {"type": "date", "required": False, "default": ""},
                    "resolution": {"type": "string", "required": False, "default": "daily"},
                },
            },
            {
                "function_id": "global_indices",
                "label": "Chỉ số quốc tế",
                "status": "partial",
                "description": "Các chỉ số quốc tế phổ biến qua MSN (API bên thứ ba - có thể chậm hoặc lỗi).",
                "runner_path": "dashboard.runners.real_global_indices",
                "output_type": "table",
                "param_schema": {
                    "symbol_id": {"type": "string", "required": False, "default": "^GSPC"},
                    "start_date": {"type": "date", "required": False, "default": ""},
                    "end_date": {"type": "date", "required": False, "default": ""},
                },
            },
        ],
    },
    {
        "group": {"name": "Chứng quyền", "slug": "warrants", "description": "Giá, ngày đáo hạn, tổ chức phát hành và trạng thái thị trường chứng quyền."},
        "functions": [
            {
                "function_id": "cw_listing",
                "label": "Danh sách chứng quyền",
                "status": "ready",
                "description": "Danh sách tất cả chứng quyền đang lưu hành.",
                "runner_path": "dashboard.runners.real_cw_listing",
                "output_type": "table",
                "param_schema": {
                    "source": {"type": "string", "required": False, "default": "vci"},
                },
            },
            {
                "function_id": "cw_price",
                "label": "Giá chứng quyền",
                "status": "ready",
                "description": "Giá realtime của chứng quyền.",
                "runner_path": "dashboard.runners.real_cw_price",
                "output_type": "table",
                "param_schema": {
                    "symbols": {"type": "string", "required": False, "default": ""},
                    "source": {"type": "string", "required": False, "default": "kbs"},
                },
            },
            {
                "function_id": "cw_expiry",
                "label": "Ngày đáo hạn",
                "status": "ready",
                "description": "Tra cứu danh sách chứng quyền (xem ngày đáo hạn trong chi tiết từng mã qua Bảng giá).",
                "runner_path": "dashboard.runners.real_cw_expiry_list",
                "output_type": "table",
                "param_schema": {
                    "source": {"type": "string", "required": False, "default": "vci"},
                },
            },
        ],
    },
    {
        "group": {"name": "Kim loại quý", "slug": "metals", "description": "Giá vàng trong nước và thế giới."},
        "functions": [
            {
                "function_id": "gold_domestic",
                "label": "Giá vàng trong nước (BTMC)",
                "status": "ready",
                "description": "Giá vàng trong nước theo thời gian thực từ Bảo Tín Minh Châu (BTMC).",
                "runner_path": "dashboard.runners.real_gold_domestic",
                "output_type": "table",
                "param_schema": {},
            },
            {
                "function_id": "gold_global",
                "label": "Giá vàng thế giới",
                "status": "partial",
                "description": "Giá vàng quốc tế qua MSN (API bên thứ ba - có thể chậm hoặc lỗi).",
                "runner_path": "dashboard.runners.real_gold_global",
                "output_type": "table",
                "param_schema": {
                    "start_date": {"type": "date", "required": False, "default": ""},
                    "end_date": {"type": "date", "required": False, "default": ""},
                },
            },
        ],
    },
    {
        "group": {"name": "Phái sinh", "slug": "derivatives", "description": "Hợp đồng tương lai VN30F và dữ liệu hợp đồng theo kỳ hạn."},
        "functions": [
            {
                "function_id": "vn30f_quote",
                "label": "VN30F - Giá phái sinh",
                "status": "ready",
                "description": "Giá hợp đồng tương lai VN30F.",
                "runner_path": "dashboard.runners.real_vn30f_history",
                "output_type": "table",
                "param_schema": {
                    "start_date": {"type": "date", "required": False, "default": ""},
                    "end_date": {"type": "date", "required": False, "default": ""},
                    "resolution": {"type": "string", "required": False, "default": "daily"},
                },
            },
            {
                "function_id": "futures_by_expiry",
                "label": "Danh sách hợp đồng phái sinh",
                "status": "ready",
                "description": "Danh sách tất cả hợp đồng tương lai đang giao dịch.",
                "runner_path": "dashboard.runners.real_futures_listing",
                "output_type": "table",
                "param_schema": {
                    "source": {"type": "string", "required": False, "default": "vci"},
                },
            },
        ],
    },
    {
        "group": {"name": "Quỹ đầu tư", "slug": "funds", "description": "ETF, quỹ mở, danh mục, hiệu suất và chỉ số liên quan (API bên thứ ba - có thể chậm hoặc lỗi)."},
        "functions": [
            {
                "function_id": "etf_overview",
                "label": "ETF - Danh sách ETF",
                "status": "ready",
                "description": "Thông tin cơ bản về các ETF đang niêm yết (VCI).",
                "runner_path": "dashboard.runners.real_fund_etf_listing",
                "output_type": "table",
                "param_schema": {
                    "source": {"type": "string", "required": False, "default": "vci"},
                },
            },
            {
                "function_id": "open_fund",
                "label": "Quỹ mở",
                "status": "partial",
                "description": "Danh sách quỹ mở trên Fmarket (API bên thứ ba - có thể chậm hoặc lỗi).",
                "runner_path": "dashboard.runners.real_fund_open_listing",
                "output_type": "table",
                "param_schema": {
                    "fund_type": {"type": "string", "required": False, "default": ""},
                },
            },
            {
                "function_id": "fund_nav_report",
                "label": "NAV quỹ mở - Lịch sử",
                "status": "partial",
                "description": "Lịch sử NAV của một quỹ mở cụ thể (Fmarket API - có thể chậm hoặc lỗi).",
                "runner_path": "dashboard.runners.real_fund_nav",
                "output_type": "table",
                "param_schema": {
                    "symbol": {"type": "string", "required": False, "default": "SSISCA"},
                    "fund_id": {"type": "integer", "required": False, "default": 23},
                },
            },
        ],
    },
    {
        "group": {"name": "Tỷ giá & Ngoại hối", "slug": "forex", "description": "Tỷ giá ngoại tệ và dữ liệu forex (API bên thứ ba - có thể chậm hoặc lỗi)."},
        "functions": [
            {
                "function_id": "forex_vcb",
                "label": "Tỷ giá VCB",
                "status": "partial",
                "description": "Tỷ giá ngoại tệ tại Vietcombank (API bên thứ ba - có thể chậm hoặc lỗi).",
                "runner_path": "dashboard.runners.real_forex_vcb",
                "output_type": "table",
                "param_schema": {
                    "date": {"type": "date", "required": False, "default": ""},
                },
            },
        ],
    },
    {
        "group": {"name": "Trái phiếu", "slug": "bonds", "description": "Trái phiếu chính phủ và doanh nghiệp."},
        "functions": [
            {
                "function_id": "gov_bonds",
                "label": "Danh sách trái phiếu chính phủ",
                "status": "ready",
                "description": "Danh sách trái phiếu chính phủ đang giao dịch.",
                "runner_path": "dashboard.runners.real_gov_bonds_listing",
                "output_type": "table",
                "param_schema": {
                    "source": {"type": "string", "required": False, "default": "vci"},
                },
            },
        ],
    },
    {
        "group": {"name": "Crypto", "slug": "crypto", "description": "Giá và biến động thị trường tiền mã hóa (API bên thứ ba - có thể chậm hoặc lỗi)."},
        "functions": [
            {
                "function_id": "crypto_price",
                "label": "Giá Crypto",
                "status": "partial",
                "description": "Giá tiền mã hóa qua MSN (API bên thứ ba - có thể chậm hoặc lỗi).",
                "runner_path": "dashboard.runners.real_crypto_price",
                "output_type": "table",
                "param_schema": {
                    "symbol_id": {"type": "string", "required": False, "default": "BTC-USD"},
                    "start_date": {"type": "date", "required": False, "default": ""},
                    "end_date": {"type": "date", "required": False, "default": ""},
                },
            },
        ],
    },
    {
        "group": {"name": "Tin tức & sự kiện tài chính", "slug": "news", "description": "Tin tức, công bố doanh nghiệp và lịch sự kiện thị trường."},
        "functions": [
            {
                "function_id": "financial_news",
                "label": "Tin tức tài chính",
                "status": "partial",
                "description": "Tin tức tài chính chứng khoán Việt Nam (API có thể chậm hoặc lỗi).",
                "runner_path": "dashboard.runners.real_financial_news",
                "output_type": "table",
                "param_schema": {
                    "symbol": {"type": "string", "required": False, "default": "FPT"},
                    "source": {"type": "string", "required": False, "default": "vci"},
                },
            },
            {
                "function_id": "corporate_disclosure",
                "label": "Công bố doanh nghiệp",
                "status": "partial",
                "description": "Công bố thông tin doanh nghiệp trên thị trường (API có thể chậm hoặc lỗi).",
                "runner_path": "dashboard.runners.real_corporate_disclosure",
                "output_type": "table",
                "param_schema": {
                    "symbol": {"type": "string", "required": False, "default": "ACB"},
                    "source": {"type": "string", "required": False, "default": "vci"},
                },
            },
        ],
    },
    {
        "group": {"name": "Bộ lọc cổ phiếu", "slug": "screener", "description": "Hiện tạm thời không hoạt động nên để trạng thái disabled."},
        "functions": [
            {
                "function_id": "stock_screener",
                "label": "Bộ lọc cổ phiếu",
                "status": "disabled",
                "description": "Tạm thời không hoạt động.",
                "runner_path": "dashboard.runners.placeholder_disabled_feature",
                "output_type": "json",
                "param_schema": {},
            },
        ],
    },
    {
        "group": {"name": "Sự kiện thị trường", "slug": "events", "description": "Lịch nghỉ lễ và sự kiện đặc biệt của thị trường Việt Nam."},
        "functions": [
            {
                "function_id": "market_events",
                "label": "Lịch nghỉ lễ & sự kiện",
                "status": "ready",
                "description": "Lịch nghỉ lễ và sự kiện đặc biệt thị trường Việt Nam (từ 2000 - 2026).",
                "runner_path": "dashboard.runners.real_market_events",
                "output_type": "table",
                "param_schema": {
                    "year": {"type": "string", "required": False, "default": ""},
                },
            },
        ],
    },
]
