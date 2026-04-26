"""
Dashboard Runners - Phase 2-5 Analysis Functions
Returns full analysis with technical indicators and AI insights
"""
from __future__ import annotations

import warnings
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
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            pass
    return v


def _extract_technical_data(result: Any) -> dict:
    """Extract technical data from StockAnalysis result"""
    if not hasattr(result, 'technical'):
        return {}
    
    tech = result.technical
    return {
        "momentum": {
            "rsi": {
                "value": getattr(tech, 'rsi', 50),
                "zone": getattr(tech, 'rsi_status', 'neutral').upper().replace('_', ' ')
            },
            "macd": {
                "value": getattr(tech, 'macd', 0),
                "status": getattr(tech, 'macd_signal', 'neutral').upper()
            }
        },
        "trend": {
            "adx": {
                "value": getattr(tech, 'adx', 0),
                "status": getattr(tech, 'adx_status', 'no_trend').upper().replace('_', ' ')
            },
            "sma": {
                "sma_20": getattr(tech, 'sma_20', 0),
                "sma_50": getattr(tech, 'sma_50', 0),
                "position": "ABOVE" if getattr(tech, 'current_price', 0) > getattr(tech, 'sma_20', 0) else "BELOW"
            }
        }
    }


def _extract_fundamental_data(result: Any) -> dict:
    """Extract fundamental data from StockAnalysis result"""
    if not hasattr(result, 'fundamental'):
        return {}
    
    fund = result.fundamental
    return {
        "f_score": {
            "value": getattr(fund, 'f_score', 0),
            "max": getattr(fund, 'f_score_max', 9),
            "grade": getattr(fund, 'f_score_grade', 'N/A')
        },
        "valuation": {
            "pe": getattr(fund, 'pe', 0),
            "pb": getattr(fund, 'pb', 0),
            "roe": getattr(fund, 'roe', 0)
        }
    }


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
        return _payload(title, kind=kind, data={"status": "no_data", "message": "Không co du lieu"})

    if isinstance(df, pd.Series):
        if df.empty:
            return _payload(title, kind=kind, data={"status": "no_data"})
        return _payload(
            title, kind=kind,
            data={"status": "series", "values": _json_serial(df)},
            columns=[str(df.name or "value")],
            rows=[{"index": str(idx), "value": _json_serial(val)} for idx, val in df.items()]
        )

    if not hasattr(df, "to_dict"):
        return _payload(title, kind=kind, data={"status": "no_data"})

    try:
        has_rows = len(df) > 0
    except (TypeError, ValueError):
        has_rows = False
    if not has_rows:
        return _payload(title, kind=kind, data={"status": "no_data"})

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
        "summary": f"{len(rows)} dong, {len(cols)} cot",
        "rows": rows,
        "columns": cols,
    }


def _parse_date_range(params: dict[str, Any]) -> tuple[str, str]:
    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    default_start = (pd.Timestamp.today() - pd.DateOffset(years=1)).strftime("%Y-%m-%d")

    def _to_str(val: Any) -> str:
        if val is None or val == "":
            return ""
        if hasattr(val, "strftime"):
            return val.strftime("%Y-%m-%d")
        return str(val)

    return _to_str(params.get("start_date")), _to_str(params.get("end_date"))


# ─── Placeholder runners ──────────────────────────────────────────────────────

def placeholder_api_quickstart(**params: Any) -> dict[str, Any]:
    return _payload(
        "Truy xuat du lieu qua API don gian",
        data={"symbol": params.get("symbol", "ACB"), "source": params.get("source", "KBS"), "note": "Chuc nang demo"}
    )


def placeholder_registry_overview(**_: Any) -> dict[str, Any]:
    data = [
        {"group": item["group"]["name"], "label": item["label"], "status": item.get("status", "planned"), "function_id": item["function_id"]}
        for item in iter_registry_functions()
    ]
    df = pd.DataFrame(data)
    return _df_to_payload("Registry overview", "table", df)


# ─── Phase 1: Stock Analysis (Full) ──────────────────────────────────────────

def real_stock_analysis(**params: Any) -> dict[str, Any]:
    """
    Full stock analysis with technical indicators and AI insights
    Returns comprehensive analysis like ARCHITECTURE_ROADMAP.md
    """
    symbol = params.get("symbol", "VCB").upper().strip()

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            from dashboard.analyzers import StockAnalyzer

            analyzer = StockAnalyzer(period_ta=90)
            result = analyzer.analyze(symbol)

            if result is None:
                return _payload(f"Phan tich {symbol}", kind="json", data={"error": f"Khong the phan tich {symbol}"})

            # Get analysis output
            output = analyzer.to_string(result) if hasattr(analyzer, 'to_string') else str(result)

            # Calculate master score from the StockAnalysis object
            master_score = result.recommendation.master_score if hasattr(result, 'recommendation') else 50

            return _payload(
                f"Phan tich {symbol}",
                kind="analysis",
                data={
                    "status": "success",
                    "symbol": symbol,
                    "name": result.name if hasattr(result, 'name') else "",
                    "price": {
                        "current": result.technical.current_price if hasattr(result, 'technical') else 0,
                        "change_percent": result.technical.change_percent if hasattr(result, 'technical') else 0,
                    },
                    "technical": _extract_technical_data(result),
                    "fundamental": _extract_fundamental_data(result),
                    "recommendation": {
                        "master_score": master_score,
                        "action": result.recommendation.action if hasattr(result, 'recommendation') else "HOLD",
                        "reasons_positive": result.recommendation.reasons_positive if hasattr(result, 'recommendation') else [],
                        "reasons_negative": result.recommendation.reasons_negative if hasattr(result, 'recommendation') else [],
                        "action_items": {
                            "if_holding": f"Nắm giữ - Chốt lời quanh {result.recommendation.profit_target:,.0f}" if hasattr(result, 'recommendation') and hasattr(result.recommendation, 'profit_target') else "Nắm giữ",
                            "stop_loss": f"{result.recommendation.stop_loss:,.0f}" if hasattr(result, 'recommendation') and hasattr(result.recommendation, 'stop_loss') else "N/A",
                        }
                    },
                    "analysis": output
                }
            )
    except Exception as exc:
        return _payload(f"Phan tich {symbol}", kind="json", data={"error": f"{type(exc).__name__}: {exc}"})


# ─── Phase 2: Index Analysis (Full) ───────────────────────────────────────────

def real_index_analysis(**params: Any) -> dict[str, Any]:
    """
    Full index analysis with market breadth and technical indicators
    Returns comprehensive analysis like ARCHITECTURE_ROADMAP.md
    """
    symbol = params.get("symbol", "VNINDEX").upper().strip()

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            from dashboard.analyzers import IndexAnalyzer

            analyzer = IndexAnalyzer(period_ta=60)
            result = analyzer.analyze(symbol)

            if result is None:
                return _payload(f"Chi so {symbol}", kind="json", data={"error": f"Khong the phan tich {symbol}"})

            # Format full output
            output = analyzer.format_output(result)

            return _payload(
                f"Phan tich chi so {symbol}",
                kind="analysis",
                data={
                    "kind": "analysis",
                    "symbol": symbol,
                    "name": f"Chi so {symbol}",
                    "analysis": output,
                    "current_value": result.current_value if hasattr(result, 'current_value') else 0,
                    "change_percent": result.change_percent if hasattr(result, 'change_percent') else 0,
                    "trend": result.trend if hasattr(result, 'trend') else "NEUTRAL",
                    "market_breadth": result.market_breadth if hasattr(result, 'market_breadth') else {},
                    "technical_status": result.technical_status if hasattr(result, 'technical_status') else "NEUTRAL",
                    "sma_20": result.sma_20 if hasattr(result, 'sma_20') else 0,
                    "sma_50": result.sma_50 if hasattr(result, 'sma_50') else 0,
                    "adx": result.adx if hasattr(result, 'adx') else 0,
                    "rsi": result.rsi if hasattr(result, 'rsi') else 0,
                    "master_score": result.master_score if hasattr(result, 'master_score') else 50
                }
            )
    except Exception as exc:
        return _payload(f"Chi so {symbol}", kind="json", data={"error": f"{type(exc).__name__}: {exc}"})


def real_market_breadth(**params: Any) -> dict[str, Any]:
    """Get market breadth data for all indices"""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            from dashboard.analyzers import IndexAnalyzer

            indices = ["VNINDEX", "VN30", "HNXIndex", "UPCOM"]
            results = []

            for symbol in indices:
                analyzer = IndexAnalyzer(period_ta=30)
                data = analyzer.analyze(symbol)
                if data:
                    results.append({
                        "symbol": symbol,
                        "value": data.current_value,
                        "change_percent": data.change_percent,
                        "trend": data.trend,
                        "advance": data.market_breadth.get("advance", 0) if data.market_breadth else 0,
                        "decline": data.market_breadth.get("decline", 0) if data.market_breadth else 0,
                    })

            df = pd.DataFrame(results)
            return _df_to_payload("Market Breadth - Chi so thi truong", "table", df)
    except Exception as exc:
        return _payload("Market Breadth", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


# ─── Phase 3: Gold Analysis (Full) ────────────────────────────────────────────

def real_gold_analysis(**params: Any) -> dict[str, Any]:
    """
    Full gold analysis with technical indicators and AI insights
    Returns comprehensive analysis like ARCHITECTURE_ROADMAP.md
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            from dashboard.analyzers import GoldAnalyzer

            analyzer = GoldAnalyzer(period_ta=90)
            result = analyzer.analyze()

            if result is None:
                return _payload("Phan tich vang", kind="json", data={"error": "Khong the phan tich vang"})

            # Format full output
            output = analyzer.format_output(result)

            return _payload(
                "Phan tich vang SJC",
                kind="analysis",
                data={
                    "kind": "analysis",
                    "name": "Vang SJC",
                    "symbol": "SJC",
                    "analysis": output,
                    "buy_price": result.buy_price if hasattr(result, 'buy_price') else 0,
                    "sell_price": result.sell_price if hasattr(result, 'sell_price') else 0,
                    "current_price": result.sell_price if hasattr(result, 'sell_price') else 0,
                    "change_percent": result.change_percent if hasattr(result, 'change_percent') else 0,
                    "trend": result.trend if hasattr(result, 'trend') else "NEUTRAL",
                    "technical_status": result.technical_status if hasattr(result, 'technical_status') else "NEUTRAL",
                    "master_score": result.master_score if hasattr(result, 'master_score') else 50,
                    "rsi": result.rsi if hasattr(result, 'rsi') else 0,
                    "macd": result.macd if hasattr(result, 'macd') else 0,
                    "adx": result.adx if hasattr(result, 'adx') else 0,
                    "sma_20": result.sma_20 if hasattr(result, 'sma_20') else 0,
                    "sma_50": result.sma_50 if hasattr(result, 'sma_50') else 0,
                    "atr": result.atr if hasattr(result, 'atr') else 0,
                    "bollinger_upper": result.bollinger_upper if hasattr(result, 'bollinger_upper') else 0,
                    "bollinger_lower": result.bollinger_lower if hasattr(result, 'bollinger_lower') else 0,
                    "pivot_r1": result.pivot_r1 if hasattr(result, 'pivot_r1') else 0,
                    "pivot_s1": result.pivot_s1 if hasattr(result, 'pivot_s1') else 0,
                    "recommendation": result.recommendation if hasattr(result, 'recommendation') else "WATCH"
                }
            )
    except Exception as exc:
        return _payload("Phan tich vang", kind="json", data={"error": f"{type(exc).__name__}: {exc}"})


# ─── Phase 3: Futures Analysis (Full) ─────────────────────────────────────────

def real_futures_analysis(**params: Any) -> dict[str, Any]:
    """
    Full futures analysis with basis, term structure and technical indicators
    Returns comprehensive analysis like ARCHITECTURE_ROADMAP.md
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            from dashboard.analyzers import FuturesAnalyzer

            analyzer = FuturesAnalyzer(period_ta=30)
            result = analyzer.analyze()

            if result is None:
                return _payload("Phan tich phai sinh", kind="json", data={"error": "Khong the phan tich phai sinh"})

            # Format full output
            output = analyzer.format_output(result)

            return _payload(
                "Phan tich VN30F",
                kind="analysis",
                data={
                    "kind": "analysis",
                    "name": "VN30F Phai sinh",
                    "symbol": "VN30F",
                    "analysis": output,
                    "futures_price": result.current_price if hasattr(result, 'current_price') else 0,
                    "current_price": result.current_price if hasattr(result, 'current_price') else 0,
                    "spot_price": result.spot_price if hasattr(result, 'spot_price') else 0,
                    "basis": result.basis if hasattr(result, 'basis') else 0,
                    "change_percent": result.change_percent if hasattr(result, 'change_percent') else 0,
                    "trend": result.trend if hasattr(result, 'trend') else "NEUTRAL",
                    "technical_status": result.technical_status if hasattr(result, 'technical_status') else "NEUTRAL",
                    "volume": result.volume if hasattr(result, 'volume') else 0,
                    "recommendation": result.recommendation if hasattr(result, 'recommendation') else "WATCH"
                }
            )
    except Exception as exc:
        return _payload("Phan tich phai sinh", kind="json", data={"error": f"{type(exc).__name__}: {exc}"})


# ─── Phase 4: ETF Analysis (Full) ─────────────────────────────────────────────

def real_etf_analysis(**params: Any) -> dict[str, Any]:
    """
    Full ETF analysis with NAV, premium/discount and technical indicators
    Returns comprehensive analysis like ARCHITECTURE_ROADMAP.md
    """
    symbol = params.get("symbol", "E1VFVN30").upper().strip()

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            from dashboard.analyzers import FundAnalyzer

            analyzer = FundAnalyzer(period_ta=90)
            result = analyzer.analyze(symbol)

            if result is None:
                return _payload(f"Phan tich ETF {symbol}", kind="json", data={"error": f"Khong the phan tich {symbol}"})

            # Format full output
            output = analyzer.format_output(result)

            return _payload(
                f"Phan tich ETF {symbol}",
                kind="analysis",
                data={
                    "kind": "analysis",
                    "symbol": symbol,
                    "name": f"ETF {symbol}",
                    "analysis": output,
                    "current_price": result.nav if hasattr(result, 'nav') else 0,
                    "current_value": result.nav if hasattr(result, 'nav') else 0,
                    "change_percent": result.nav_change_percent if hasattr(result, 'nav_change_percent') else 0,
                    "trend": result.trend if hasattr(result, 'trend') else "NEUTRAL",
                    "technical_status": result.trend if hasattr(result, 'trend') else "NEUTRAL",
                    "recommendation": result.recommendation if hasattr(result, 'recommendation') else "HOLD"
                }
            )
    except Exception as exc:
        return _payload(f"Phan tich ETF {symbol}", kind="json", data={"error": f"{type(exc).__name__}: {exc}"})


# ─── Phase 4: Forex Analysis (Full) ───────────────────────────────────────────

def real_forex_analysis(**params: Any) -> dict[str, Any]:
    """
    Full forex analysis with technical indicators
    Returns comprehensive analysis like ARCHITECTURE_ROADMAP.md
    """
    symbol = params.get("symbol", "USDVND").upper().strip()

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            from dashboard.analyzers import ForexAnalyzer

            analyzer = ForexAnalyzer(period_ta=30)
            result = analyzer.analyze(symbol)

            if result is None:
                return _payload(f"Phan tich forex {symbol}", kind="json", data={"error": f"Khong the phan tich {symbol}"})

            # Format full output
            output = analyzer.format_output(result)

            return _payload(
                f"Phan tich ty gia {symbol}",
                kind="analysis",
                data={
                    "kind": "analysis",
                    "symbol": symbol,
                    "name": f"Ty gia {symbol}",
                    "analysis": output,
                    "current_price": result.current_rate if hasattr(result, 'current_rate') else 0,
                    "current_value": result.current_rate if hasattr(result, 'current_rate') else 0,
                    "change_percent": result.change_percent if hasattr(result, 'change_percent') else 0,
                    "trend": result.trend if hasattr(result, 'trend') else "NEUTRAL",
                    "technical_status": result.trend if hasattr(result, 'trend') else "NEUTRAL",
                    "recommendation": result.recommendation if hasattr(result, 'recommendation') else "NEUTRAL"
                }
            )
    except Exception as exc:
        return _payload(f"Phan tich forex {symbol}", kind="json", data={"error": f"{type(exc).__name__}: {exc}"})


# ─── Phase 4: Crypto Analysis (Full) ──────────────────────────────────────────

def real_crypto_analysis(**params: Any) -> dict[str, Any]:
    """
    Full crypto analysis with technical indicators and AI insights
    Returns comprehensive analysis like ARCHITECTURE_ROADMAP.md
    """
    symbol = params.get("symbol", "BTCUSDT").upper().strip()

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            from dashboard.analyzers import CryptoAnalyzer

            analyzer = CryptoAnalyzer(period_ta=90)
            result = analyzer.analyze(symbol)

            if result is None:
                return _payload(f"Phan tich crypto {symbol}", kind="json", data={"error": f"Khong the phan tich {symbol}"})

            # Format full output
            output = analyzer.format_output(result)

            return _payload(
                f"Phan tich {symbol}",
                kind="analysis",
                data={
                    "kind": "analysis",
                    "symbol": symbol,
                    "name": f"Crypto {symbol}",
                    "analysis": output,
                    "current_price": result.current_price if hasattr(result, 'current_price') else 0,
                    "current_value": result.current_price if hasattr(result, 'current_price') else 0,
                    "change_percent": result.change_percent_24h if hasattr(result, 'change_percent_24h') else 0,
                    "trend": result.trend if hasattr(result, 'trend') else "NEUTRAL",
                    "technical_status": result.trend if hasattr(result, 'trend') else "NEUTRAL",
                    "recommendation": result.recommendation if hasattr(result, 'recommendation') else "HOLD"
                }
            )
    except Exception as exc:
        return _payload(f"Phan tich crypto {symbol}", kind="json", data={"error": f"{type(exc).__name__}: {exc}"})


# ─── Phase 4: CW/ Covered Warrant Analysis (Full) ─────────────────────────────

def real_cw_analysis(**params: Any) -> dict[str, Any]:
    """
    Full covered warrant analysis with Greeks and technical indicators
    Returns comprehensive analysis like ARCHITECTURE_ROADMAP.md
    """
    symbol = params.get("symbol", "CACB2511").upper().strip()

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            from dashboard.analyzers import CWAnalyzer

            analyzer = CWAnalyzer(period_ta=30)
            result = analyzer.analyze(symbol)

            if result is None:
                return _payload(f"Phan tich CW {symbol}", kind="json", data={"error": f"Khong the phan tich {symbol}"})

            # Format full output
            output = analyzer.format_output(result)

            return _payload(
                f"Phan tich chung quyen {symbol}",
                kind="analysis",
                data={
                    "kind": "analysis",
                    "symbol": symbol,
                    "name": f"CW {symbol}",
                    "analysis": output,
                    "underlying": result.underlying if hasattr(result, 'underlying') else "",
                    "warrant_type": result.warrant_type if hasattr(result, 'warrant_type') else "",
                    "current_price": result.current_price if hasattr(result, 'current_price') else 0,
                    "current_value": result.current_price if hasattr(result, 'current_price') else 0,
                    "change_percent": result.change_percent if hasattr(result, 'change_percent') else 0,
                    "strike_price": result.strike_price if hasattr(result, 'strike_price') else 0,
                    "maturity_date": result.maturity_date if hasattr(result, 'maturity_date') else "",
                    "exercise_ratio": result.exercise_ratio if hasattr(result, 'exercise_ratio') else 1,
                    "status": result.status if hasattr(result, 'status') else "UNKNOWN",
                    "trend": result.trend if hasattr(result, 'trend') else "NEUTRAL",
                    "technical_status": result.technical_status if hasattr(result, 'technical_status') else "NEUTRAL"
                }
            )
    except Exception as exc:
        return _payload(f"Phan tich CW {symbol}", kind="json", data={"error": f"{type(exc).__name__}: {exc}"})


# ─── Phase 5: Bond Analysis (Full) ───────────────────────────────────────────

def real_bond_analysis(**params: Any) -> dict[str, Any]:
    """
    Full bond analysis with yield curve and technical indicators
    Returns comprehensive analysis like ARCHITECTURE_ROADMAP.md
    """
    bond_type = params.get("bond_type", "GOVT")
    
    # Map bond_type to display name
    bond_names = {
        "GOVT": "Trái phiếu Chính phủ",
        "5Y": "Trái phiếu 5 năm",
        "10Y": "Trái phiếu 10 năm",
        "15Y": "Trái phiếu 15 năm",
        "CORP": "Trái phiếu Doanh nghiệp",
    }
    bond_name = bond_names.get(bond_type, "Trái phiếu Chính phủ")
    
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            from dashboard.analyzers import GovBondIndexAnalyzer

            analyzer = GovBondIndexAnalyzer()
            result = analyzer.analyze(symbol=bond_type)

            if result is None:
                return _payload(f"Phan tich {bond_name}", kind="json", data={"error": f"Khong the phan tich {bond_name}"})

            # Format full output
            output = analyzer.format_output(result)

            return _payload(
                f"Phan tich {bond_name}",
                kind="analysis",
                data={
                    "kind": "analysis",
                    "symbol": bond_type,
                    "name": bond_name,
                    "analysis": output,
                    "current_price": result.avg_yield_10y if hasattr(result, 'avg_yield_10y') else 0,
                    "current_value": result.avg_yield_10y if hasattr(result, 'avg_yield_10y') else 0,
                    "change_percent": result.yield_curve_slope if hasattr(result, 'yield_curve_slope') else 0,
                    "trend": result.trend if hasattr(result, 'trend') else "NEUTRAL",
                    "technical_status": result.trend if hasattr(result, 'trend') else "NEUTRAL",
                    "recommendation": result.recommendation if hasattr(result, 'recommendation') else "NEUTRAL",
                    "avg_yield_10y": result.avg_yield_10y if hasattr(result, 'avg_yield_10y') else 0,
                    "avg_yield_5y": result.avg_yield_5y if hasattr(result, 'avg_yield_5y') else 0
                }
            )
    except Exception as exc:
        return _payload(f"Phan tich {bond_name}", kind="json", data={"error": f"{type(exc).__name__}: {exc}"})


# ─── Legacy runners (raw data) - kept for compatibility ──────────────────────

def real_listing_all_symbols(**params: Any) -> dict[str, Any]:
    try:
        from vnstock_data import Reference
        ref = Reference()
        df = ref.equity.list()
        return _df_to_payload("Danh sach ma niem yet", "table", df)
    except Exception as exc:
        return _payload("Danh sach ma niem yet", kind="table", data={"error": str(exc)})


def real_listing_by_exchange(**params: Any) -> dict[str, Any]:
    try:
        from vnstock_data import Reference
        ref = Reference()
        df = ref.equity.list_by_exchange()
        return _df_to_payload("Danh sach ma theo san", "table", df)
    except Exception as exc:
        return _payload("Danh sach ma theo san", kind="table", data={"error": str(exc)})


def real_listing_by_group(**params: Any) -> dict[str, Any]:
    try:
        from vnstock_data import Reference
        ref = Reference()
        group = params.get("group", "VN30")
        df = ref.equity.list_by_group(group=group)
        return _df_to_payload(f"Danh sach nhom {group}", "table", df)
    except Exception as exc:
        return _payload(f"Danh sach nhom {group}", kind="table", data={"error": str(exc)})


def real_listing_all_indices(**params: Any) -> dict[str, Any]:
    try:
        from vnstock_data import Reference
        ref = Reference()
        df = ref.equity.list_indices()
        return _df_to_payload("Danh sach chi so", "table", df)
    except Exception as exc:
        return _payload("Danh sach chi so", kind="table", data={"error": str(exc)})


def real_price_board(**params: Any) -> dict[str, Any]:
    symbols_str = params.get("symbols", "ACB,VNM,HPG,FPT")
    source = params.get("source", "kbs")
    symbols = [s.strip() for s in symbols_str.split(",") if s.strip()]
    if not symbols:
        return _payload("Bang gia", kind="table", data={"error": "Vui long nhap it nhat mot ma"})

    try:
        from vnstock.explorer.kbs.trading import Trading
        trading = Trading(show_log=False)
        df = trading.price_board(symbols_list=symbols, get_all=False)
        return _df_to_payload(f"Bang gia - {', '.join(symbols)}", "table", df)
    except Exception as exc:
        return _payload("Bang gia", kind="table", data={"error": str(exc)})


def real_stock_quote_realtime(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "ACB").upper().strip()
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.quote import Quote
        q = Quote(symbol=symbol, show_log=False)
        df = q.realtime()
        if df is not None and len(df) > 0:
            return _df_to_payload(f"Gia realtime {symbol}", "table", df)
        return _payload(f"Gia realtime {symbol}", kind="table", data={"error": "Khong co du lieu"})
    except Exception as exc:
        return _payload(f"Gia realtime {symbol}", kind="json", data={"error": str(exc)})


def real_stock_intraday(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "ACB").upper().strip()
    page_size = int(params.get("page_size", 100))
    try:
        from vnstock.explorer.vci.quote import Quote
        q = Quote(symbol=symbol, show_log=False)
        df = q.intraday(page_size=page_size)
        return _df_to_payload(f"Intraday {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Intraday {symbol}", kind="table", data={"error": str(exc)})


def real_stock_historical(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "ACB").upper().strip()
    start_date, end_date = _parse_date_range(params)
    resolution = params.get("resolution", "daily")
    interval_map = {"daily": "1D", "weekly": "1W", "monthly": "1M"}
    interval = interval_map.get(resolution.lower(), "1D")
    try:
        from vnstock.explorer.vci.quote import Quote
        q = Quote(symbol=symbol, show_log=False)
        df = q.history(start=start_date, end=end_date, interval=interval)
        return _df_to_payload(f"Lich su gia {symbol} ({resolution})", "table", df)
    except Exception as exc:
        return _payload(f"Lich su gia {symbol}", kind="table", data={"error": str(exc)})


def real_stock_financial_reports(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT").upper().strip()
    report_type = params.get("report_type", "balance_sheet")
    period = params.get("period", "quarter")
    lang = params.get("lang", "vi")
    try:
        from vnstock.explorer.vci.financial import Financial
        fin = Financial(symbol=symbol, show_log=False)
        if report_type == "income_statement":
            df = fin.income_statement(period=period, lang=lang)
        elif report_type == "cash_flow":
            df = fin.cash_flow(period=period, lang=lang)
        else:
            df = fin.balance_sheet(period=period, lang=lang)
        return _df_to_payload(f"Bao cao {report_type} {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Bao cao {symbol}", kind="table", data={"error": str(exc)})


def real_stock_financial_ratios(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT").upper().strip()
    period = params.get("period", "quarter")
    try:
        from vnstock.explorer.vci.financial import Financial
        fin = Financial(symbol=symbol, show_log=False)
        df = fin.ratio(period=period)
        return _df_to_payload(f"Chi so tai chinh {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Chi so tai chinh {symbol}", kind="table", data={"error": str(exc)})


def real_company_profile(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT").upper().strip()
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.company import Company
        company = Company(symbol=symbol, show_log=False)
        df = company.overview()
        if df is not None and hasattr(df, 'to_dict'):
            return _payload(f"Thong tin {symbol}", kind="json", data=df.to_dict())
        return _payload(f"Thong tin {symbol}", kind="json", data={"error": "Khong co du lieu"})
    except Exception as exc:
        return _payload(f"Thong tin {symbol}", kind="json", data={"error": str(exc)})


def real_stock_news(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT").upper().strip()
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.news import News
        news = News(show_log=False)
        df = news.latest(symbol=symbol, page_size=20)
        return _df_to_payload(f"Tin tuc {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Tin tuc {symbol}", kind="table", data={"error": str(exc)})


def real_index_history(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "VNINDEX")
    start_date, end_date = _parse_date_range(params)
    resolution = params.get("resolution", "daily")
    interval_map = {"daily": "1D", "weekly": "1W", "monthly": "1M"}
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
        return _df_to_payload(f"Chi so quoc te {symbol_id}", "table", df)
    except Exception as exc:
        return _payload(f"Chi so quoc te {symbol_id}", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


def real_cw_listing(**params: Any) -> dict[str, Any]:
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.listing import Listing
        listing = Listing(show_log=False)
        df = listing.all_covered_warrant()
        if hasattr(df, "to_frame"):
            df = df.to_frame(name="symbol")
        return _df_to_payload("Danh sach chung quyen", "table", df)
    except Exception as exc:
        return _payload("Danh sach chung quyen", kind="table", data={"error": str(exc)})


def real_cw_price(**params: Any) -> dict[str, Any]:
    symbols_str = params.get("symbols", "")
    source = params.get("source", "kbs")
    symbols_list = [s.strip() for s in symbols_str.split(",") if s.strip()]
    if not symbols_list:
        return _payload("Gia chung quyen", kind="table", data={"error": "Vui long nhap it nhat mot ma chung quyen."})
    try:
        from vnstock.explorer.kbs.trading import Trading
        trading = Trading(show_log=False)
        df = trading.price_board(symbols_list=symbols_list, get_all=False)
        return _df_to_payload(f"Gia chung quyen - {', '.join(symbols_list)}", "table", df)
    except Exception as exc:
        return _payload("Gia chung quyen", kind="table", data={"error": str(exc)})


def real_cw_expiry_list(**params: Any) -> dict[str, Any]:
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.listing import Listing
        listing = Listing(show_log=False)
        df = listing.all_covered_warrant()
        if hasattr(df, "to_frame"):
            df = df.to_frame(name="symbol")
        return _df_to_payload("Danh sach chung quyen", "table", df)
    except Exception as exc:
        return _payload("Danh sach chung quyen", kind="table", data={"error": str(exc)})


def real_gold_domestic(**params: Any) -> dict[str, Any]:
    try:
        from vnstock.explorer.misc.gold_price import btmc_goldprice
        df = btmc_goldprice()
        return _df_to_payload("Gia vang trong nuoc (BTMC)", "table", df)
    except Exception as exc:
        return _payload("Gia vang trong nuoc", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


def real_gold_global(**params: Any) -> dict[str, Any]:
    try:
        from vnstock.explorer.misc.gold_price import btmc_goldprice
        df = btmc_goldprice()
        sjc = df[df['name'].str.contains('VANG MIENG SJC', case=False, na=False)].copy()
        if sjc.empty:
            return _payload("Gia vang the gioi", kind="table", data={"status": "no_data"})
        return _df_to_payload("Gia vang SJC", "table", sjc)
    except Exception as exc:
        return _payload("Gia vang the gioi", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


def real_vn30f_history(**params: Any) -> dict[str, Any]:
    start_date, end_date = _parse_date_range(params)
    resolution = params.get("resolution", "daily")
    interval_map = {"daily": "1D", "weekly": "1W"}
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
        return _df_to_payload("Danh sach hop dong phai sinh", "table", df)
    except Exception as exc:
        return _payload("Danh sach hop dong phai sinh", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


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
        return _df_to_payload("Danh sach quy mo", "table", df)
    except Exception as exc:
        return _payload("Danh sach quy mo", kind="table", data={"error": str(exc)})


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


def real_forex_vcb(**params: Any) -> dict[str, Any]:
    date_val = params.get("date", "")
    try:
        from vnstock.explorer.misc.exchange_rate import vcb_exchange_rate
        if not date_val:
            import datetime as dt
            date_val = dt.date.today().strftime("%Y-%m-%d")
        df = vcb_exchange_rate(date=date_val)
        return _df_to_payload("Ty gia VCB", "table", df)
    except Exception as exc:
        return _payload("Ty gia VCB", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


def real_gov_bonds_listing(**params: Any) -> dict[str, Any]:
    source = params.get("source", "vci")
    try:
        from vnstock.explorer.vci.listing import Listing
        listing = Listing(show_log=False)
        df = listing.all_government_bonds()
        if hasattr(df, "to_frame"):
            df = df.to_frame(name="symbol")
        return _df_to_payload("Danh sach trai phieu chinh phu", "table", df)
    except Exception as exc:
        return _payload("Danh sach trai phieu chinh phu", kind="table", data={"error": str(exc)})


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

    symbol_map = {
        "BTC": "BTC-USD", "ETH": "ETH-USD", "BNB": "BNB-USD",
        "XRP": "XRP-USD", "SOL": "SOL-USD", "ADA": "ADA-USD",
        "DOGE": "DOGE-USD", "DOT": "DOT-USD",
    }
    yf_symbol = symbol_map.get(symbol_id, symbol_id if "-" in symbol_id else f"{symbol_id}-USD")

    try:
        import time as _sleep
        _sleep.sleep(1)
        start_ts = int(pd.Timestamp(start_str).timestamp())
        end_ts = int(pd.Timestamp(end_str).timestamp())
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, params={"period1": start_ts, "period2": end_ts, "interval": "1d"}, headers=headers, timeout=15)
        if resp.status_code == 429:
            return _payload(f"Crypto {symbol_id}", kind="table", data={"error": "Rate limit. Choi vai giay roi thu lai."})
        if resp.status_code != 200:
            return _payload(f"Crypto {symbol_id}", kind="table", data={"error": f"HTTP {resp.status_code}"})
        json_data = resp.json()
        result = json_data.get("chart", {}).get("result", [])
        if not result:
            return _payload(f"Crypto {symbol_id}", kind="table", data={"error": "Khong co du lieu"})
        timestamps = result[0]["timestamp"]
        ohlc = result[0]["indicators"]["quote"][0]
        df = pd.DataFrame({"time": pd.to_datetime(timestamps, unit="s"), "open": ohlc["open"], "high": ohlc["high"], "low": ohlc["low"], "close": ohlc["close"], "volume": ohlc["volume"]})
        df = df.dropna()
        return _df_to_payload(f"Crypto {yf_symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Crypto {symbol_id}", kind="table", data={"error": f"{type(exc).__name__}: {exc}"})


def real_market_events(**params: Any) -> dict[str, Any]:
    try:
        from vnstock.core.utils.market_events import MARKET_EVENTS
        year_filter = params.get("year", "")
        rows = []
        for date, info in MARKET_EVENTS.items():
            if year_filter and not date.startswith(str(year_filter)):
                continue
            rows.append({"date": date, "event": info.get("event", ""), "type": info.get("type", "")})
        if not rows:
            return _payload("Su kien thi truong", kind="table", data={"status": "no_data"})
        df = pd.DataFrame(rows)
        return _df_to_payload(f"Su kien thi truong {year_filter if year_filter else '(2000-2026)'}", "table", df)
    except Exception as exc:
        return _payload("Su kien thi truong", kind="table", data={"error": str(exc)})


def placeholder_disabled_feature(**_: Any) -> dict[str, Any]:
    return _payload("Bo loc co phieu", kind="json", data={"status": "disabled", "message": "Tinh nang tam thoi khong hoat dong."})


def real_financial_news(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "FPT")
    try:
        from vnstock_news import EnhancedNewsCrawler
        import asyncio
        crawler = EnhancedNewsCrawler(cache_enabled=False)
        sources = ['https://cafef.vn/latest-news-sitemap.xml', 'https://vietnamnet.vn/rss/kinh-doanh.rss']
        df = asyncio.run(crawler.fetch_articles_async(sources=sources, max_articles=10))
        return _df_to_payload(f"Tin tai chinh", "table", df)
    except Exception as exc:
        return _payload(f"Tin tuc - {symbol}", kind="table", data={"error": str(exc)})


def real_corporate_disclosure(**params: Any) -> dict[str, Any]:
    symbol = params.get("symbol", "ACB")
    try:
        from vnstock.explorer.vci.disclosure import Disclosure
        disc = Disclosure(show_log=False)
        df = disc.latest(symbol=symbol)
        return _df_to_payload(f"Cong bo {symbol}", "table", df)
    except Exception as exc:
        return _payload(f"Cong bo - {symbol}", kind="table", data={"error": str(exc)})
