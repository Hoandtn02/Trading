from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from .services import iter_registry_functions


def _json_serial(v: Any) -> Any:
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, pd.Timestamp):
        return str(v)
    if isinstance(v, pd.Timedelta):
        return str(v)
    if isinstance(v, pd.Series):
        return v.to_dict()
    if isinstance(v, pd.Index):
        return [str(x) for x in v]
    if v is pd.NA or v is pd.NaT:
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v
    if hasattr(v, "item"):  # numpy generic types
        try:
            return v.item()
        except Exception:
            pass
    return v


def _payload(title: str, kind: str = "json", data: Any | None = None, rows: list[dict[str, Any]] | None = None, columns: list[str] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"kind": kind, "title": title, "summary": ""}
    if data is not None:
        payload["data"] = {k: _json_serial(v) for k, v in (data.items() if hasattr(data, "items") else [("value", data)])}
    if rows is not None:
        payload["rows"] = rows
    if columns is not None:
        payload["columns"] = columns
    return payload


def _df_to_payload(title: str, kind: str, df: Any) -> dict[str, Any]:
    if df is None:
        return _payload(title, kind=kind, data={"status": "no_data", "message": "Không có dữ liệu"})

    # Handle pandas Series (single column result)
    if isinstance(df, pd.Series):
        if df.empty:
            return _payload(title, kind=kind, data={"status": "no_data", "message": "Không có dữ liệu"})
        return _payload(
            title, kind=kind,
            data={"status": "series", "values": _json_serial(df)},
            columns=[str(df.name or "value")],
            rows=[{"index": str(idx), "value": _json_serial(val)} for idx, val in df.items()]
        )

    # If it's not a DataFrame-like object, treat as error/empty
    if not hasattr(df, "to_dict"):
        return _payload(title, kind=kind, data={"status": "no_data", "message": "Không có dữ liệu"})

    try:
        has_rows = len(df) > 0
    except (TypeError, ValueError):
        has_rows = False
    if not has_rows:
        return _payload(title, kind=kind, data={"status": "no_data", "message": "Không có dữ liệu"})

    if hasattr(df, "dtypes"):
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df = df.copy()
            df.columns = ["_".join(str(c).strip() for c in col if str(c).strip()) for col in df.columns]

    rows = []
    if hasattr(df, "to_dict"):
        raw = df.to_dict(orient="records")
        for row in raw:
            rows.append({k: _json_serial(v) for k, v in row.items()})

    cols = []
    _cols = getattr(df, "columns", None)
    if _cols is not None and hasattr(_cols, "__iter__"):
        try:
            cols = [str(c) for c in list(_cols)]
        except Exception:
            cols = []
    return {
        "kind": kind,
        "title": title,
        "summary": f"{len(rows)} dòng, {len(cols)} cột",
        "rows": rows,
        "columns": cols,
    }


def _parse_date_range(params: dict[str, Any]) -> tuple[str, str]:
    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    default_start = (pd.Timestamp.today() - pd.DateOffset(years=1)).strftime("%Y-%m-%d")

    def _to_str(val: Any) -> str:
        if val is None or val == "":
            return ""
        if hasattr(val, "strftime"):  # date or datetime object
            return val.strftime("%Y-%m-%d")
        return str(val)

    return _to_str(params.get("start_date")), _to_str(params.get("end_date"))


# ─── Nền tảng chung ──────────────────────────────────────────────────────────

def placeholder_api_quickstart(**params: Any) -> dict[str, Any]:
    return _payload(
        "Truy xuất dữ liệu qua API đơn giản",
        data={"symbol": params.get("symbol", "ACB"), "source": params.get("source", "KBS"), "note": "Chức năng demo – chọn chức năng khác để lấy dữ liệu thật"}
    )


def placeholder_registry_overview(**_: Any) -> dict[str, Any]:
    data = [
        {"group": item["group"]["name"], "label": item["label"], "status": item.get("status", "planned"), "function_id": item["function_id"]}
        for item in iter_registry_functions()
    ]
    df = pd.DataFrame(data)
    return _df_to_payload("Registry overview", "table", df)


# ─── Danh sách mã ────────────────────────────────────────────────────────────

def real_listing_all_symbols(**params: Any) -> dict[str, Any]:
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.listing import Listing
        listing = Listing(show_log=False)
        df = listing.all_symbols()
        return _df_to_payload("Danh sách mã niêm yết", "table", df)
    except Exception as exc:
        return _payload("Danh sách mã niêm yết", kind="table", data={"error": str(exc)})


def real_listing_by_exchange(**params: Any) -> dict[str, Any]:
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.listing import Listing
        listing = Listing(show_log=False)
        df = listing.symbols_by_exchange(lang="vi")
        return _df_to_payload("Danh sách mã theo sàn", "table", df)
    except Exception as exc:
        return _payload("Danh sách mã theo sàn", kind="table", data={"error": str(exc)})


def real_listing_by_group(**params: Any) -> dict[str, Any]:
    source = params.get("source", "vci")
    group = params.get("group", "VN30")
    try:
        from vnstock.explorer.vci.listing import Listing
        listing = Listing(show_log=False)
        df = listing.symbols_by_group(group=group)
        if hasattr(df, "to_frame"):
            df = df.to_frame(name="symbol")
        return _df_to_payload(f"Danh sách nhóm {group}", "table", df)
    except Exception as exc:
        return _payload(f"Danh sách nhóm {group}", kind="table", data={"error": str(exc)})


def real_listing_all_indices(**params: Any) -> dict[str, Any]:
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.listing import Listing
        listing = Listing(show_log=False)
        df = listing.all_indices()
        return _df_to_payload("Danh sách chỉ số", "table", df)
    except Exception as exc:
        return _payload("Danh sách chỉ số", kind="table", data={"error": str(exc)})


# ─── Bảng giá ────────────────────────────────────────────────────────────────

def real_price_board(**params: Any) -> dict[str, Any]:
    source = params.get("source", "kbs")
    symbols_str = params.get("symbols", "ACB,VNM,HPG,FPT")
    symbols_list = [s.strip() for s in symbols_str.split(",") if s.strip()]
    if not symbols_list:
        symbols_list = ["ACB"]
    try:
        from vnstock.explorer.kbs.trading import Trading
        trading = Trading(show_log=False)
        df = trading.price_board(symbols_list=symbols_list, get_all=False)
        return _df_to_payload(f"Bảng giá realtime - {', '.join(symbols_list)}", "table", df)
    except Exception as exc:
        return _payload("Bảng giá realtime", kind="table", data={"error": str(exc)})


# ─── Cổ phiếu – giá realtime ─────────────────────────────────────────────────

def real_stock_quote_realtime(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "ACB")
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.quote import Quote
        end = pd.Timestamp.today().strftime("%Y-%m-%d")
        start = (pd.Timestamp.today() - pd.DateOffset(days=7)).strftime("%Y-%m-%d")
        q = Quote(symbol=symbol, show_log=False)
        df = q.history(start=start, end=end, interval="1D")
        if df is None or (hasattr(df, "empty") and df.empty):
            return _payload(f"Giá realtime – {symbol}", kind="json", data={"error": "Không lấy được dữ liệu realtime"})
        last = df.tail(1).reset_index(drop=True)
        return _df_to_payload(f"Giá realtime – {symbol}", "json", last)
    except Exception as exc:
        return _payload(f"Giá realtime – {symbol}", kind="json", data={"error": str(exc)})


# ─── Cổ phiếu – intraday ────────────────────────────────────────────────────

def real_stock_intraday(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "ACB")
    source = params.get("source", "vci")
    page_size = int(params.get("page_size", 100))
    try:
        from vnstock.explorer.vci.quote import Quote
        q = Quote(symbol=symbol, show_log=False)
        df = q.intraday(page_size=page_size)
        return _df_to_payload(f"Intraday – {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Intraday – {symbol}", kind="table", data={"error": str(exc)})


# ─── Cổ phiếu – giá lịch sử ─────────────────────────────────────────────────

def real_stock_historical(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "ACB")
    source = params.get("source", "vci")
    start_date, end_date = _parse_date_range(params)
    resolution = params.get("resolution", "daily")
    interval_map = {
        "daily": "1D",
        "weekly": "1W",
        "monthly": "1M",
    }
    interval = interval_map.get(resolution.lower(), "1D")
    try:
        from vnstock.explorer.vci.quote import Quote
        q = Quote(symbol=symbol, show_log=False)
        df = q.history(start=start_date, end=end_date, interval=interval)
        return _df_to_payload(f"Giá lịch sử – {symbol} ({resolution})", "table", df)
    except Exception as exc:
        return _payload(f"Giá lịch sử – {symbol}", kind="table", data={"error": str(exc)})


# ─── Cổ phiếu – báo cáo tài chính ──────────────────────────────────────────

def real_stock_financial_reports(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT")
    source = params.get("source", "vci")
    report_type = params.get("report_type", "balance_sheet")
    period = params.get("period", "quarter")
    lang = params.get("lang", "vi")
    try:
        from vnstock.explorer.vci.financial import Finance
        f = Finance(symbol=symbol, show_log=False)
        method_map = {
            "balance_sheet": lambda: f.balance_sheet(period=period, lang=lang, dropna=True),
            "income_statement": lambda: f.income_statement(lang=lang, dropna=True),
            "cash_flow": lambda: f.cash_flow(),
        }
        method = method_map.get(report_type, f.balance_sheet)
        df = method()
        return _df_to_payload(f"Báo cáo {report_type} – {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Báo cáo tài chính – {symbol}", kind="table", data={"error": str(exc)})


def real_stock_financial_ratios(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT")
    source = params.get("source", "vci")
    period = params.get("period", "quarter")
    try:
        from vnstock.explorer.vci.financial import Finance
        f = Finance(symbol=symbol, show_log=False)
        df = f.ratio(flatten_columns=True, separator=" – ")
        return _df_to_payload(f"Chỉ số tài chính – {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Chỉ số tài chính – {symbol}", kind="table", data={"error": str(exc)})


# ─── Cổ phiếu – thông tin doanh nghiệp ─────────────────────────────────────

def real_company_profile(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT")
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.company import Company
        c = Company(symbol=symbol, show_log=False)
        df = c.overview()
        return _df_to_payload(f"Thông tin doanh nghiệp – {symbol}", "json", df)
    except Exception as exc:
        return _payload(f"Thông tin doanh nghiệp – {symbol}", kind="json", data={"error": str(exc)})


# ─── Cổ phiếu – tin tức ────────────────────────────────────────────────────

def real_stock_news(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT")
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.company import Company
        c = Company(symbol=symbol, show_log=False)
        df = c.news()
        return _df_to_payload(f"Tin tức – {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Tin tức – {symbol}", kind="table", data={"error": str(exc)})


# ─── Chỉ số thị trường ──────────────────────────────────────────────────────

def real_index_history(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "VNINDEX")
    source = params.get("source", "vci")
    start_date, end_date = _parse_date_range(params)
    resolution = params.get("resolution", "daily")
    interval_map = {
        "daily": "1D",
        "weekly": "1W",
        "monthly": "1M",
    }
    interval = interval_map.get(resolution.lower(), "1D")
    try:
        from vnstock.explorer.kbs.quote import Quote
        q = Quote(symbol=symbol, show_log=False)
        df = q.history(start=start_date, end=end_date, interval=interval)
        return _df_to_payload(f"Chỉ số {symbol} ({resolution})", "table", df)
    except Exception as exc:
        return _payload(f"Chỉ số {symbol}", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


def real_global_indices(**params: Any) -> dict[str, Any]:
    symbol_id = params.get("symbol_id", "^GSPC")
    start_date, end_date = _parse_date_range(params)
    try:
        from vnstock.explorer.msn.quote import Quote
        q = Quote(symbol_id=symbol_id)
        df = q.history(start=start_date, end=end_date, interval="1D")
        return _df_to_payload(f"Chỉ số quốc tế {symbol_id}", "table", df)
    except Exception as exc:
        return _payload(f"Chỉ số quốc tế {symbol_id}", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


# ─── Chứng quyền ────────────────────────────────────────────────────────────

def real_cw_listing(**params: Any) -> dict[str, Any]:
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.listing import Listing
        listing = Listing(show_log=False)
        df = listing.all_covered_warrant()
        if hasattr(df, "to_frame"):
            df = df.to_frame(name="symbol")
        return _df_to_payload("Danh sách chứng quyền", "table", df)
    except Exception as exc:
        return _payload("Danh sách chứng quyền", kind="table", data={"error": str(exc)})


def real_cw_price(**params: Any) -> dict[str, Any]:
    symbols_str = params.get("symbols", "")
    source = params.get("source", "kbs")
    symbols_list = [s.strip() for s in symbols_str.split(",") if s.strip()] if symbols_str else []
    if not symbols_list:
        return _payload("Giá chứng quyền", kind="table", data={"error": "Vui lòng nhập ít nhất một mã chứng quyền."})
    try:
        from vnstock.explorer.kbs.trading import Trading
        trading = Trading(show_log=False)
        df = trading.price_board(symbols_list=symbols_list, get_all=False)
        return _df_to_payload(f"Giá chứng quyền - {', '.join(symbols_list)}", "table", df)
    except Exception as exc:
        return _payload("Giá chứng quyền", kind="table", data={"error": str(exc)})


def real_cw_expiry_list(**params: Any) -> dict[str, Any]:
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.listing import Listing
        listing = Listing(show_log=False)
        df = listing.all_covered_warrant()
        if hasattr(df, "to_frame"):
            df = df.to_frame(name="symbol")
        return _df_to_payload("Danh sách chứng quyền (tra cứu ngày đáo hạn trong chi tiết từng mã)", "table", df)
    except Exception as exc:
        return _payload("Danh sách chứng quyền", kind="table", data={"error": str(exc)})


# ─── Kim loại quý ────────────────────────────────────────────────────────────

def real_gold_domestic(**params: Any) -> dict[str, Any]:
    try:
        from vnstock.explorer.misc.gold_price import btmc_goldprice
        df = btmc_goldprice()
        return _df_to_payload("Giá vàng trong nước (BTMC)", "table", df)
    except Exception as exc:
        return _payload("Giá vàng trong nước", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


def real_gold_global(**params: Any) -> dict[str, Any]:
    start_date, end_date = _parse_date_range(params)
    try:
        from vnstock.explorer.msn.quote import Quote
        q = Quote(symbol_id="GC=F")
        df = q.history(start=start_date, end=end_date, interval="1D")
        return _df_to_payload("Giá vàng thế giới (GC=F)", "table", df)
    except Exception as exc:
        return _payload("Giá vàng thế giới", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


# ─── Phái sinh ───────────────────────────────────────────────────────────────

def real_vn30f_history(**params: Any) -> dict[str, Any]:
    start_date, end_date = _parse_date_range(params)
    resolution = params.get("resolution", "daily")
    interval_map = {
        "daily": "1D",
        "weekly": "1W",
    }
    interval = interval_map.get(resolution.lower(), "1D")
    try:
        from vnstock.explorer.kbs.quote import Quote
        q = Quote(symbol="VN30F", show_log=False)
        df = q.history(start=start_date, end=end_date, interval=interval)
        return _df_to_payload(f"VN30F Futures ({resolution})", "table", df)
    except Exception as exc:
        return _payload("VN30F Futures", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


def real_futures_listing(**params: Any) -> dict[str, Any]:
    try:
        from vnstock.explorer.kbs.listing import Listing
        listing = Listing(show_log=False)
        df = listing.symbols_by_group(group='FU_INDEX')
        if not hasattr(df, "to_dict"):
            df = df.to_frame(name="symbol")
        return _df_to_payload("Danh sách hợp đồng phái sinh", "table", df)
    except Exception as exc:
        return _payload("Danh sách hợp đồng phái sinh", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


# ─── Quỹ đầu tư ────────────────────────────────────────────────────────────

def real_fund_etf_listing(**params: Any) -> dict[str, Any]:
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.listing import Listing
        listing = Listing(show_log=False)
        df = listing.symbols_by_group(group="ETF")
        if hasattr(df, "to_frame"):
            df = df.to_frame(name="symbol")
        return _df_to_payload("Danh sách ETF", "table", df)
    except Exception as exc:
        return _payload("Danh sách ETF", kind="table", data={"error": str(exc)})


def real_fund_open_listing(**params: Any) -> dict[str, Any]:
    fund_type = params.get("fund_type", "")
    try:
        from vnstock.explorer.fmarket.fund import Fund
        fund = Fund()
        df = fund.listing(fund_type=fund_type)
        return _df_to_payload("Danh sách quỹ mở", "table", df)
    except Exception as exc:
        return _payload("Danh sách quỹ mở", kind="table", data={"error": str(exc)})


def real_fund_nav(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "SSISCA")
    fund_id = int(params.get("fund_id", 23))
    try:
        from vnstock.explorer.fmarket.fund import Fund
        fund = Fund()
        df = fund.nav_report(fundId=fund_id)
        return _df_to_payload(f"NAV {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"NAV {symbol}", kind="table", data={"error": str(exc)})


# ─── Tỷ giá ─────────────────────────────────────────────────────────────────

def real_forex_vcb(**params: Any) -> dict[str, Any]:
    date_val = params.get("date", "")
    try:
        from vnstock.explorer.misc.exchange_rate import vcb_exchange_rate
        if not date_val:
            import datetime as dt
            date_val = dt.date.today().strftime("%Y-%m-%d")
        df = vcb_exchange_rate(date=date_val)
        return _df_to_payload("Tỷ giá VCB", "table", df)
    except Exception as exc:
        return _payload("Tỷ giá VCB", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


# ─── Trái phiếu ─────────────────────────────────────────────────────────────

def real_gov_bonds_listing(**params: Any) -> dict[str, Any]:
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.listing import Listing
        listing = Listing(show_log=False)
        df = listing.all_government_bonds()
        if hasattr(df, "to_frame"):
            df = df.to_frame(name="symbol")
        return _df_to_payload("Danh sách trái phiếu chính phủ", "table", df)
    except Exception as exc:
        return _payload("Danh sách trái phiếu chính phủ", kind="table", data={"error": str(exc)})


# ─── Crypto ─────────────────────────────────────────────────────────────────

def real_crypto_price(**params: Any) -> dict[str, Any]:
    symbol_id = params.get("symbol_id", "BTC-USD")
    start_raw = params.get("start_date", "")
    end_raw = params.get("end_date", "")

    def _to_str(val: Any) -> str:
        if val is None or val == "":
            return None
        if hasattr(val, "strftime"):
            return val.strftime("%Y-%m-%d")
        return str(val)

    start_str = _to_str(start_raw)
    end_str = _to_str(end_raw)

    if start_str is None:
        start_str = (pd.Timestamp.today() - pd.DateOffset(days=30)).strftime("%Y-%m-%d")
    if end_str is None:
        end_str = pd.Timestamp.today().strftime("%Y-%m-%d")

    try:
        from vnstock.explorer.msn.quote import Quote
        q = Quote(symbol_id=symbol_id)
        df = q.history(
            start=start_str,
            end=end_str,
            interval="1D"
        )
        return _df_to_payload(f"Crypto {symbol_id}", "table", df)
    except Exception as exc:
        return _payload(f"Crypto {symbol_id}", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


# ─── Tiện ích ──────────────────────────────────────────────────────────────────

def real_market_events(**params: Any) -> dict[str, Any]:
    from vnstock.core.utils.market_events import MARKET_EVENTS
    import pandas as pd
    year_filter = params.get("year", "")
    rows = []
    for date, info in MARKET_EVENTS.items():
        if year_filter and not date.startswith(str(year_filter)):
            continue
        rows.append({"date": date, "event": info.get("event", ""), "type": info.get("type", "")})
    if not rows:
        return _payload("Sự kiện thị trường", kind="table", data={"status": "no_data", "message": "Không có dữ liệu cho năm này."})
    df = pd.DataFrame(rows)
    return _df_to_payload(f"Sự kiện thị trường Việt Nam {year_filter if year_filter else '(từ 2000-2026)'}", "table", df)


def placeholder_disabled_feature(**_: Any) -> dict[str, Any]:
    return _payload("Bộ lọc cổ phiếu", kind="json", data={"status": "disabled", "message": "Tính năng tạm thời không hoạt động do thay đổi API TCBS."})


# ─── Tin tức ─────────────────────────────────────────────────────────────────

def real_financial_news(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT")
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.company import Company
        c = Company(symbol=symbol, show_log=False)
        df = c.news()
        return _df_to_payload(f"Tin tức thị trường", "table", df)
    except Exception as exc:
        return _payload("Tin tức thị trường", kind="table", data={"error": str(exc)})


def real_corporate_disclosure(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "ACB")
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.company import Company
        c = Company(symbol=symbol, show_log=False)
        df = c.news()
        return _df_to_payload(f"Công bố doanh nghiệp – {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Công bố doanh nghiệp – {symbol}", kind="table", data={"error": str(exc)})