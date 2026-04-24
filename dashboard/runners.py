from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd
import requests

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


# ─── Danh sách mã (Unified UI - vnstock_data) ─────────────────────────────────

def real_listing_all_symbols(**params: Any) -> dict[str, Any]:
    try:
        from vnstock_data import Reference
        ref = Reference()
        df = ref.equity.list()
        return _df_to_payload("Danh sách mã niêm yết", "table", df)
    except Exception as exc:
        return _payload("Danh sách mã niêm yết", kind="table", data={"error": str(exc)})


def real_listing_by_exchange(**params: Any) -> dict[str, Any]:
    try:
        from vnstock_data import Reference
        ref = Reference()
        df = ref.equity.list_by_exchange()
        return _df_to_payload("Danh sách mã theo sàn", "table", df)
    except Exception as exc:
        return _payload("Danh sách mã theo sàn", kind="table", data={"error": str(exc)})


def real_listing_by_group(**params: Any) -> dict[str, Any]:
    group = params.get("group", "VN30")
    try:
        from vnstock_data import Reference
        ref = Reference()
        result = ref.equity.list_by_group(group=group)
        # Unified UI tra ve Series, can chuyen thanh DataFrame
        if isinstance(result, pd.Series):
            df = result.to_frame(name="symbol")
        else:
            df = result
        return _df_to_payload(f"Danh sách nhóm {group}", "table", df)
    except Exception as exc:
        return _payload(f"Danh sách nhóm {group}", kind="table", data={"error": str(exc)})


def real_listing_all_indices(**params: Any) -> dict[str, Any]:
    try:
        from vnstock_data import Reference
        ref = Reference()
        df = ref.index.groups()
        return _df_to_payload("Danh sách chỉ số", "table", df)
    except Exception as exc:
        return _payload("Danh sách chỉ số", kind="table", data={"error": str(exc)})


# ─── Bảng giá (Unified UI) ───────────────────────────────────────────────────

def real_price_board(**params: Any) -> dict[str, Any]:
    symbols_str = params.get("symbols", "ACB,VNM,HPG,FPT")
    symbols_list = [s.strip() for s in symbols_str.split(",") if s.strip()]
    if not symbols_list:
        symbols_list = ["ACB"]
    try:
        from vnstock_data import Market
        mkt = Market()
        # Lay gia cuoi cua tung ma
        data = []
        for sym in symbols_list:
            try:
                df = mkt.equity(sym).ohlcv(
                    start=(pd.Timestamp.today() - pd.DateOffset(days=5)).strftime("%Y-%m-%d"),
                    end=pd.Timestamp.today().strftime("%Y-%m-%d")
                )
                if df is not None and len(df) > 0:
                    last = df.iloc[-1]
                    data.append({
                        "symbol": sym,
                        "close": last.get("close"),
                        "change": last.get("close") - df.iloc[0].get("close") if len(df) > 1 else 0,
                        "volume": last.get("volume"),
                    })
            except Exception:
                continue
        result_df = pd.DataFrame(data)
        if result_df.empty:
            return _payload("Bảng giá", kind="table", data={"error": "Khong lay duoc du lieu"})
        return _df_to_payload(f"Bang gia - {', '.join(symbols_list)}", "table", result_df)
    except Exception as exc:
        return _payload("Bang gia", kind="table", data={"error": str(exc)})


# ─── Cổ phiếu – giá realtime (Unified UI) ──────────────────────────────────

def real_stock_quote_realtime(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "ACB")
    try:
        from vnstock_data import Market
        mkt = Market()
        end = pd.Timestamp.today().strftime("%Y-%m-%d")
        start = (pd.Timestamp.today() - pd.DateOffset(days=7)).strftime("%Y-%m-%d")
        df = mkt.equity(symbol).ohlcv(start=start, end=end, interval="1D")
        if df is None or (hasattr(df, "empty") and df.empty):
            return _payload(f"Gia realtime - {symbol}", kind="json", data={"error": "Khong lay duoc du lieu realtime"})
        last = df.tail(1).reset_index(drop=True)
        return _df_to_payload(f"Gia realtime - {symbol}", "json", last)
    except Exception as exc:
        return _payload(f"Gia realtime - {symbol}", kind="json", data={"error": str(exc)})


# ─── Cổ phiếu – intraday ────────────────────────────────────────────────────

def real_stock_intraday(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "ACB")
    page_size = int(params.get("page_size", 100))
    try:
        from vnstock_data import Market
        mkt = Market()
        # Unified UI chi ho tro 1D, 1W, 1M - khong co intraday
        # Neu can intraday, su dung vnstock cu
        from vnstock.explorer.vci.quote import Quote
        q = Quote(symbol=symbol, show_log=False)
        df = q.intraday(page_size=page_size)
        return _df_to_payload(f"Intraday - {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Intraday - {symbol}", kind="table", data={"error": str(exc)})


# ─── Cổ phiếu – giá lịch sử (Unified UI) ────────────────────────────────────

def real_stock_historical(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "ACB")
    start_date, end_date = _parse_date_range(params)
    resolution = params.get("resolution", "daily")
    interval_map = {
        "daily": "1D",
        "weekly": "1W",
        "monthly": "1M",
    }
    interval = interval_map.get(resolution.lower(), "1D")
    try:
        from vnstock_data import Market
        mkt = Market()
        df = mkt.equity(symbol).ohlcv(start=start_date, end=end_date, interval=interval)
        return _df_to_payload(f"Gia lich su - {symbol} ({resolution})", "table", df)
    except Exception as exc:
        return _payload(f"Gia lich su - {symbol}", kind="table", data={"error": str(exc)})


# ─── Cổ phiếu – báo cáo tài chính (Unified UI) ──────────────────────────────

def real_stock_financial_reports(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT")
    report_type = params.get("report_type", "balance_sheet")
    period = params.get("period", "quarter")
    try:
        from vnstock_data import Fundamental
        fun = Fundamental()
        method_map = {
            "balance_sheet": lambda: fun.equity(symbol).balance_sheet(period=period),
            "income_statement": lambda: fun.equity(symbol).income_statement(),
            "cash_flow": lambda: fun.equity(symbol).cash_flow(),
        }
        method = method_map.get(report_type, fun.equity(symbol).balance_sheet)
        df = method()
        return _df_to_payload(f"Bao cao {report_type} - {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Bao cao tai chinh - {symbol}", kind="table", data={"error": str(exc)})


def real_stock_financial_ratios(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT")
    period = params.get("period", "quarter")
    try:
        from vnstock_data import Fundamental
        fun = Fundamental()
        df = fun.equity(symbol).ratio(period=period)
        return _df_to_payload(f"Chi so tai chinh - {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Chi so tai chinh - {symbol}", kind="table", data={"error": str(exc)})


# ─── Cổ phiếu – thông tin doanh nghiệp (Unified UI) ─────────────────────────

def real_company_profile(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT")
    try:
        from vnstock_data import Reference
        ref = Reference()
        # Lay thong tin co ban tu list
        df = ref.equity.list()
        company = df[df['symbol'] == symbol]
        if company.empty:
            return _payload(f"Thong tin doanh nghiep - {symbol}", kind="json", data={"error": "Khong tim thay ma nay"})
        return _df_to_payload(f"Thong tin doanh nghiep - {symbol}", "json", company)
    except Exception as exc:
        return _payload(f"Thong tin doanh nghiep - {symbol}", kind="json", data={"error": str(exc)})


# ─── Tin tức (vnstock_news EnhancedNewsCrawler) ──────────────────────────────

def real_stock_news(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT")
    try:
        from vnstock_news import EnhancedNewsCrawler
        import asyncio
        
        crawler = EnhancedNewsCrawler(cache_enabled=False)
        
        # Lay tin tu cac nguon
        df = asyncio.run(crawler.fetch_articles_async(
            sources=['https://cafef.vn/latest-news-sitemap.xml'],
            site_name='cafef',
            max_articles=20,
            time_frame='7d'
        ))
        
        # Loc tin theo symbol neu co
        if df is not None and len(df) > 0:
            if symbol:
                mask = df['title'].str.contains(symbol, case=False, na=False) | \
                       df['short_description'].str.contains(symbol, case=False, na=False)
                df = df[mask]
            if len(df) == 0:
                return _payload(f"Tin tuc - {symbol}", kind="table", data={"status": "no_data", "message": f"Khong co tin cho {symbol}"})
        
        return _df_to_payload(f"Tin tuc - {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Tin tuc - {symbol}", kind="table", data={"error": str(exc)})


# ─── Chỉ số thị trường (Unified UI) ────────────────────────────────────────

def real_index_history(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "VNINDEX")
    start_date, end_date = _parse_date_range(params)
    resolution = params.get("resolution", "daily")
    interval_map = {
        "daily": "1D",
        "weekly": "1W",
        "monthly": "1M",
    }
    interval = interval_map.get(resolution.lower(), "1D")
    try:
        from vnstock_data import Market
        mkt = Market()
        df = mkt.equity(symbol).ohlcv(start=start_date, end=end_date, interval=interval)
        return _df_to_payload(f"Chi so {symbol} ({resolution})", "table", df)
    except Exception as exc:
        return _payload(f"Chi so {symbol}", kind="table", data={"error": str(exc)})


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
    try:
        from vnstock.explorer.misc.gold_price import btmc_goldprice
        import pandas as pd
        df = btmc_goldprice()
        # Filter SJC gold rows which have world_price
        sjc = df[df['name'].str.contains('VÀNG MIẾNG SJC', case=False, na=False)].copy()
        if sjc.empty:
            return _payload("Giá vàng thế giới", kind="table", data={"status": "no_data", "message": "Không có dữ liệu."})
        # Build clean display table
        display = sjc[['name', 'buy_price', 'sell_price', 'world_price', 'time']].copy()
        display.columns = ['Loại', 'Giá mua (VND)', 'Giá bán (VND)', 'Giá thế giới (USD/oz)', 'Cập nhật']
        display = display.drop_duplicates()
        return _df_to_payload("Giá vàng SJC & thế giới (BTMC)", "table", display)
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


# ─── Quỹ đầu tư (Unified UI) ────────────────────────────────────────────────

def real_fund_etf_listing(**params: Any) -> dict[str, Any]:
    try:
        from vnstock_data import Reference
        ref = Reference()
        df = ref.etf.list()
        return _df_to_payload("Danh sach ETF", "table", df)
    except Exception as exc:
        return _payload("Danh sach ETF", kind="table", data={"error": str(exc)})


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
    symbol_id = params.get("symbol_id", "BTC-USD").upper().strip()
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

    # Map user-friendly symbol to Yahoo Finance format
    symbol_map = {
        "BTC": "BTC-USD", "ETH": "ETH-USD", "BNB": "BNB-USD",
        "XRP": "XRP-USD", "SOL": "SOL-USD", "ADA": "ADA-USD",
        "DOGE": "DOGE-USD", "DOT": "DOT-USD",
    }
    yf_symbol = symbol_map.get(symbol_id, symbol_id if "-" in symbol_id else f"{symbol_id}-USD")

    try:
        import time as _sleep
        _sleep.sleep(1)  # avoid Yahoo rate limit
        start_ts = int(pd.Timestamp(start_str).timestamp())
        end_ts = int(pd.Timestamp(end_str).timestamp())
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        resp = requests.get(url, params={"period1": start_ts, "period2": end_ts, "interval": "1d"}, headers=headers, timeout=15)
        if resp.status_code == 429:
            return _payload(f"Crypto {symbol_id}", kind="table", data={"error": "Rate limit Yahoo. Đợi vài giây rồi thử lại."})
        if resp.status_code != 200:
            return _payload(f"Crypto {symbol_id}", kind="table", data={"error": f"HTTP {resp.status_code}: Không lấy được dữ liệu."})
        json_data = resp.json()
        result = json_data.get("chart", {}).get("result", [])
        if not result:
            return _payload(f"Crypto {symbol_id}", kind="table", data={"error": "Không có dữ liệu cho mã này."})
        timestamps = result[0]["timestamp"]
        ohlc = result[0]["indicators"]["quote"][0]
        df = pd.DataFrame({"time": pd.to_datetime(timestamps, unit="s"), "open": ohlc["open"], "high": ohlc["high"], "low": ohlc["low"], "close": ohlc["close"], "volume": ohlc["volume"]})
        df = df.dropna()
        return _df_to_payload(f"Crypto {yf_symbol}", "table", df)
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


# ─── Tin tức tài chính ─────────────────────────────────────────────────────────

def real_financial_news(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT")
    try:
        from vnstock_news import EnhancedNewsCrawler
        import asyncio
        
        crawler = EnhancedNewsCrawler(cache_enabled=False)
        
        # Lay tin tu nhieu nguon tai chinh
        sources = [
            'https://cafef.vn/latest-news-sitemap.xml',
            'https://vietnamnet.vn/rss/kinh-doanh.rss',
        ]
        df = asyncio.run(crawler.fetch_articles_async(
            sources=sources,
            max_articles=30,
            time_frame='7d'
        ))
        
        if df is not None and len(df) > 0:
            if symbol:
                mask = df['title'].str.contains(symbol, case=False, na=False) | \
                       df['short_description'].str.contains(symbol, case=False, na=False)
                df = df[mask]
        
        return _df_to_payload("Tin tuc thi truong", "table", df)
    except Exception as exc:
        return _payload("Tin tuc thi truong", kind="table", data={"error": str(exc)})


def real_corporate_disclosure(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "ACB")
    try:
        from vnstock_news import EnhancedNewsCrawler
        import asyncio
        
        crawler = EnhancedNewsCrawler(cache_enabled=False)
        
        # Lay tin tu nguon cong bo
        df = asyncio.run(crawler.fetch_articles_async(
            sources=['https://cafef.vn/latest-news-sitemap.xml'],
            site_name='cafef',
            max_articles=50,
            time_frame='30d'
        ))
        
        if df is not None and len(df) > 0:
            if symbol:
                mask = df['title'].str.contains(symbol, case=False, na=False) | \
                       df['short_description'].str.contains(symbol, case=False, na=False)
                df = df[mask]
        
        return _df_to_payload(f"Cong bo doanh nghiep - {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Cong bo doanh nghiep - {symbol}", kind="table", data={"error": str(exc)})


# ─── Stock Analysis (Comprehensive Technical + Fundamental) ───────────────────

def real_stock_analysis(**params: Any) -> dict[str, Any]:
    """
    Comprehensive stock analysis combining technical indicators and fundamental data.
    
    This function provides:
    - Technical Analysis: RSI, MACD, ADX, SuperTrend, SMA, CMF, MFI, Bollinger, VWAP
    - Fundamental Analysis: F-Score, P/E, P/B, ROE, EPS, Profit Growth
    - AI Recommendation: Master Score, BUY/SELL/HOLD signal, entry/exit levels
    
    Parameters:
        symbol: Stock symbol (e.g., "VCB", "ACB", "FPT")
        include_sentiment: Include news sentiment analysis (default: False)
    
    Returns:
        Dictionary with analysis results including:
        - price: current price and change
        - technical: all technical indicators
        - fundamental: financial metrics and F-Score
        - recommendation: AI-generated trading signal
    """
    symbol = params.get("symbol", "ACB").upper().strip()
    include_sentiment = params.get("include_sentiment", False)
    
    try:
        from dashboard.analyzers import StockAnalyzer
        
        analyzer = StockAnalyzer(period_ta=90)
        result = analyzer.analyze(symbol, include_sentiment=include_sentiment)
        
        if result.recommendation.action == "ERROR":
            return _payload(
                f"Phân tích {symbol}",
                kind="json",
                data={
                    "status": "error",
                    "symbol": symbol,
                    "error": result.recommendation.reasons_negative[0] if result.recommendation.reasons_negative else "Unknown error"
                }
            )
        
        # Return structured JSON response
        return {
            "kind": "json",
            "title": f"Phân tích kỹ thuật & cơ bản - {symbol}",
            "summary": f"Master Score: {result.recommendation.master_score}/100 | Signal: {result.recommendation.action}",
            "data": {
                "status": "success",
                "symbol": result.symbol,
                "name": result.name,
                "exchange": result.exchange,
                "timestamp": result.timestamp.isoformat(),
                "price": {
                    "current": result.technical.current_price,
                    "change_percent": result.technical.change_percent,
                    "volume": result.technical.volume,
                },
                "technical": {
                    "momentum": {
                        "rsi": {
                            "value": result.technical.rsi,
                            "status": result.technical.rsi_status,
                            "zone": "QUÁ MUA" if result.technical.rsi >= 70 else "QUÁ BÁN" if result.technical.rsi <= 30 else "TRUNG LẬP"
                        },
                        "macd": {
                            "value": result.technical.macd,
                            "signal": result.technical.macd_signal,
                            "status": "TĂNG" if result.technical.macd > 0 else "GIẢM"
                        }
                    },
                    "trend": {
                        "adx": {
                            "value": result.technical.adx,
                            "status": result.technical.adx_status,
                            "description": f"Xu hướng {result.technical.adx_status.replace('_', ' ').title()}"
                        },
                        "sma": {
                            "sma_20": result.technical.sma_20,
                            "sma_50": result.technical.sma_50,
                            "trend": result.technical.trend_status,
                            "position": "TRÊN" if result.technical.current_price > result.technical.sma_20 else "DƯỚI"
                        },
                        "supertrend": {
                            "signal": result.technical.supertrend_signal,
                            "stop": result.technical.supertrend_stop
                        }
                    },
                    "money_flow": {
                        "cmf": {
                            "value": result.technical.cmf,
                            "status": result.technical.cmf_status,
                            "direction": "TIỀN CHẢY VÀO" if result.technical.cmf > 0 else "TIỀN CHẢY RA"
                        },
                        "mfi": {
                            "value": result.technical.mfi,
                            "status": result.technical.mfi_status
                        }
                    },
                    "volatility": {
                        "atr": {
                            "value": result.technical.atr,
                            "status": result.technical.atr_status
                        },
                        "bollinger": {
                            "upper": result.technical.bollinger_upper,
                            "lower": result.technical.bollinger_lower,
                            "middle": result.technical.bollinger_middle,
                            "position": result.technical.bollinger_position
                        }
                    },
                    "value": {
                        "vwap": {
                            "value": result.technical.vwap,
                            "status": result.technical.vwap_status,
                            "position": "TRÊN" if "above" in result.technical.vwap_status else "DƯỚI"
                        }
                    }
                },
                "fundamental": {
                    "f_score": {
                        "value": result.fundamental.f_score,
                        "max": result.fundamental.f_score_max,
                        "grade": result.fundamental.f_score_grade,
                        "description": f"F-Score {result.fundamental.f_score}/9 (Grade {result.fundamental.f_score_grade})"
                    },
                    "valuation": {
                        "pe": result.fundamental.pe,
                        "pb": result.fundamental.pb,
                        "roe": result.fundamental.roe,
                        "eps": result.fundamental.eps
                    },
                    "growth": {
                        "profit_growth": result.fundamental.profit_growth,
                        "profit_growth_yoy": result.fundamental.profit_growth_yoy,
                        "margin": result.fundamental.margin
                    }
                },
                "sentiment": {
                    "news_count": result.sentiment.news_count,
                    "score": result.sentiment.score,
                    "sentiment": result.sentiment.sentiment,
                    "keywords": result.sentiment.keywords,
                    "summary": result.sentiment.summary
                } if result.sentiment.news_count > 0 else None,
                "recommendation": {
                    "action": result.recommendation.action,
                    "master_score": result.recommendation.master_score,
                    "score_stars": result.recommendation.score_stars,
                    "reasons_positive": result.recommendation.reasons_positive,
                    "reasons_negative": result.recommendation.reasons_negative,
                    "support": result.recommendation.support,
                    "resistance": result.recommendation.resistance,
                    "entry_target": result.recommendation.entry_target,
                    "stop_loss": result.recommendation.stop_loss,
                    "profit_target": result.recommendation.profit_target,
                    "timeframe": result.recommendation.timeframe,
                    "risk_level": result.recommendation.risk_level,
                    "action_items": {
                        "if_holding": f"GIỮ - Chốt lời quanh {result.recommendation.resistance:,.0f}" if result.recommendation.action == "HOLD" else f"TIẾP TỤC NẮM GIỮ",
                        "if_not_holding": f"CHỜ - Mua quanh {result.recommendation.entry_target:,.0f}" if result.recommendation.action in ["BUY", "HOLD"] else "CHỜ XUỐNG",
                        "stop_loss": f"Cắt lỗ: {result.recommendation.stop_loss:,.0f} ({(result.recommendation.stop_loss/result.technical.current_price-1)*100:.1f}%)",
                        "target": f"Mục tiêu: {result.recommendation.profit_target:,.0f} (+{(result.recommendation.profit_target/result.technical.current_price-1)*100:.1f}%)"
                    }
                }
            }
        }
        
    except ImportError as exc:
        return _payload(
            f"Phân tích {symbol}",
            kind="json",
            data={
                "status": "error",
                "symbol": symbol,
                "error": f"Module not found. Please ensure vnstock_ta and vnstock_data are installed. {str(exc)}"
            }
        )
    except Exception as exc:
        return _payload(
            f"Phân tích {symbol}",
            kind="json",
            data={
                "status": "error",
                "symbol": symbol,
                "error": f"{type(exc).__name__}: {str(exc)}"
            }
        )