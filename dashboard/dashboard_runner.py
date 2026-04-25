"""
Unified Dashboard Runner - Phase 5
Kết hợp tất cả analyzers (Phase 1-4) với caching và batch processing
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
import pandas as pd

# Cache directory
CACHE_DIR = Path.home() / ".trading_dashboard" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class CacheManager:
    """Simple file-based cache for API responses"""
    
    def __init__(self, cache_dir: Path = CACHE_DIR, ttl_seconds: int = 300):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_seconds
    
    def _get_cache_key(self, prefix: str, params: dict) -> str:
        """Generate cache key from prefix and params"""
        params_str = json.dumps(params, sort_keys=True, default=str)
        hash_str = hashlib.md5(params_str.encode()).hexdigest()[:16]
        return f"{prefix}_{hash_str}"
    
    def _get_cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"
    
    def get(self, prefix: str, params: dict) -> Optional[dict]:
        """Get cached data if exists and not expired"""
        key = self._get_cache_key(prefix, params)
        path = self._get_cache_path(key)
        
        if not path.exists():
            return None
        
        # Check TTL
        mtime = path.stat().st_mtime
        age = time.time() - mtime
        
        if age > self.ttl:
            # Expired
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except:
            return None
    
    def set(self, prefix: str, params: dict, data: dict) -> None:
        """Cache data with timestamp"""
        key = self._get_cache_key(prefix, params)
        path = self._get_cache_path(key)
        
        cache_entry = {
            "timestamp": time.time(),
            "params": params,
            "data": data
        }
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"[CacheManager] Cache write error: {e}")
    
    def clear(self, prefix: str = None) -> int:
        """Clear cache files. If prefix is None, clear all."""
        count = 0
        pattern = f"{prefix}_*" if prefix else "*"
        
        for path in self.cache_dir.glob(pattern):
            try:
                path.unlink()
                count += 1
            except:
                pass
        
        return count
    
    def clear_expired(self) -> int:
        """Clear expired cache files"""
        count = 0
        now = time.time()
        
        for path in self.cache_dir.glob("*.json"):
            try:
                mtime = path.stat().st_mtime
                if now - mtime > self.ttl:
                    path.unlink()
                    count += 1
            except:
                pass
        
        return count


# Global cache instance
cache = CacheManager()


def _json_serial(v: Any) -> Any:
    """JSON serialization helper"""
    from datetime import date, datetime
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
        except:
            pass
    return v


def _df_to_payload(title: str, kind: str, df: Any) -> dict:
    """Convert DataFrame to dashboard payload"""
    if df is None:
        return {"kind": kind, "title": title, "data": {"status": "no_data", "message": "Không có dữ liệu"}}
    
    if isinstance(df, pd.Series):
        if df.empty:
            return {"kind": kind, "title": title, "data": {"status": "no_data"}}
        return {
            "kind": kind,
            "title": title,
            "data": {"status": "series", "values": _json_serial(df)},
            "columns": [str(df.name or "value")],
            "rows": [{"index": str(idx), "value": _json_serial(val)} for idx, val in df.items()]
        }
    
    if not hasattr(df, "to_dict") or df.empty:
        return {"kind": kind, "title": title, "data": {"status": "no_data"}}
    
    rows = []
    for row in df.to_dict(orient="records"):
        rows.append({k: _json_serial(v) for k, v in row.items()})
    
    cols = [str(c) for c in list(df.columns)] if hasattr(df, "columns") else []
    
    return {
        "kind": kind,
        "title": title,
        "summary": f"{len(rows)} dòng, {len(cols)} cột",
        "rows": rows,
        "columns": cols,
    }


def _payload(title: str, kind: str = "json", data: Any = None) -> dict:
    return {"kind": kind, "title": title, "summary": "", "data": data if data else {}}


# ─── Stock Analysis Runner ───────────────────────────────────────────────────

def run_stock_analysis(symbol: str, use_cache: bool = True) -> dict:
    """Run comprehensive stock analysis (Phase 1)"""
    cache_prefix = f"stock_{symbol}"
    params = {"symbol": symbol}
    
    if use_cache:
        cached = cache.get(cache_prefix, params)
        if cached:
            cached["cached"] = True
            return cached
    
    try:
        from dashboard.analyzers import StockAnalyzer
        
        analyzer = StockAnalyzer(period_ta=90)
        result = analyzer.analyze(symbol)
        
        # Get output text - StockAnalyzer uses to_string, others use format_output
        if hasattr(analyzer, 'to_string'):
            output = analyzer.to_string(result)
        elif hasattr(analyzer, 'format_output'):
            output = analyzer.format_output(result)
        else:
            output = str(result)
        
        payload = {
            "status": "success",
            "symbol": result.symbol,
            "name": result.name,
            "exchange": result.exchange,
            "timestamp": datetime.now().isoformat(),
            "price": {
                "current": result.technical.current_price,
                "change_percent": result.technical.change_percent,
                "volume": result.technical.volume,
            },
            "technical": {
                "rsi": result.technical.rsi,
                "macd": result.technical.macd,
                "adx": result.technical.adx,
                "sma_20": result.technical.sma_20,
                "sma_50": result.technical.sma_50,
            },
            "fundamental": {
                "f_score": result.fundamental.f_score,
                "pe": result.fundamental.pe,
                "pb": result.fundamental.pb,
                "roe": result.fundamental.roe,
            },
            "recommendation": {
                "action": result.recommendation.action,
                "master_score": result.recommendation.master_score,
            },
            "output_text": output
        }
        
        if use_cache:
            cache.set(cache_prefix, params, payload)
        
        return payload
        
    except Exception as e:
        return {"status": "error", "symbol": symbol, "error": str(e)}


# ─── Index Analysis Runner ──────────────────────────────────────────────────

def run_index_analysis(symbol: str = "VNINDEX", use_cache: bool = True) -> dict:
    """Run index analysis with market breadth (Phase 2)"""
    cache_prefix = f"index_{symbol}"
    params = {"symbol": symbol}
    
    if use_cache:
        cached = cache.get(cache_prefix, params)
        if cached:
            cached["cached"] = True
            return cached
    
    try:
        from dashboard.analyzers import IndexAnalyzer
        
        analyzer = IndexAnalyzer(period_ta=60)
        result = analyzer.analyze(symbol)
        
        # Get output text - StockAnalyzer uses to_string, others use format_output
        if hasattr(analyzer, 'to_string'):
            output = analyzer.to_string(result)
        elif hasattr(analyzer, 'format_output'):
            output = analyzer.format_output(result)
        else:
            output = str(result)
        
        payload = {
            "status": "success",
            "symbol": result.symbol,
            "name": result.name,
            "current_value": result.current_value,
            "change_percent": result.change_percent,
            "high": result.high,
            "low": result.low,
            "volume": result.volume,
            "trend": result.trend,
            "technical_status": result.technical_status,
            "market_breadth": result.market_breadth,
            "breadth_percent": result.breadth_percent,
            "output_text": output
        }
        
        if use_cache:
            cache.set(cache_prefix, params, payload)
        
        return payload
        
    except Exception as e:
        return {"status": "error", "symbol": symbol, "error": str(e)}


# ─── Gold & Futures Analysis Runner ─────────────────────────────────────────

def run_gold_analysis(gold_type: str = "gold_vn", use_cache: bool = True) -> dict:
    """Run gold analysis (Phase 3)"""
    cache_prefix = f"gold_{gold_type}"
    params = {"type": gold_type}
    
    if use_cache:
        cached = cache.get(cache_prefix, params)
        if cached:
            cached["cached"] = True
            return cached
    
    try:
        from dashboard.analyzers import GoldAnalyzer
        
        analyzer = GoldAnalyzer(period_ta=30)
        result = analyzer.analyze(gold_type)
        
        # Get output text - StockAnalyzer uses to_string, others use format_output
        if hasattr(analyzer, 'to_string'):
            output = analyzer.to_string(result)
        elif hasattr(analyzer, 'format_output'):
            output = analyzer.format_output(result)
        else:
            output = str(result)
        
        payload = {
            "status": "success",
            "symbol": result.symbol,
            "name": result.name,
            "current_price": result.current_price,
            "buy_price": result.buy_price,
            "sell_price": result.sell_price,
            "change_percent": result.change_percent,
            "high": result.high,
            "low": result.low,
            "unit": result.unit,
            "trend": result.trend,
            "technical_status": result.technical_status,
            "output_text": output
        }
        
        if use_cache:
            cache.set(cache_prefix, params, payload)
        
        return payload
        
    except Exception as e:
        return {"status": "error", "type": gold_type, "error": str(e)}


def run_futures_analysis(symbol: str = "VN30F", use_cache: bool = True) -> dict:
    """Run futures analysis (Phase 3)"""
    cache_prefix = f"futures_{symbol}"
    params = {"symbol": symbol}
    
    if use_cache:
        cached = cache.get(cache_prefix, params)
        if cached:
            cached["cached"] = True
            return cached
    
    try:
        from dashboard.analyzers import FuturesAnalyzer
        
        analyzer = FuturesAnalyzer(period_ta=30)
        result = analyzer.analyze(symbol)
        
        # Get output text - StockAnalyzer uses to_string, others use format_output
        if hasattr(analyzer, 'to_string'):
            output = analyzer.to_string(result)
        elif hasattr(analyzer, 'format_output'):
            output = analyzer.format_output(result)
        else:
            output = str(result)
        
        payload = {
            "status": "success",
            "symbol": result.symbol,
            "name": result.name,
            "current_price": result.current_price,
            "change_percent": result.change_percent,
            "high": result.high,
            "low": result.low,
            "volume": result.volume,
            "basis": result.basis,
            "trend": result.trend,
            "technical_status": result.technical_status,
            "output_text": output
        }
        
        if use_cache:
            cache.set(cache_prefix, params, payload)
        
        return payload
        
    except Exception as e:
        return {"status": "error", "symbol": symbol, "error": str(e)}


# ─── ETF, Forex, Crypto, CW Analysis Runner ────────────────────────────────

def run_etf_analysis(symbol: str = "E1VFVN30", use_cache: bool = True) -> dict:
    """Run ETF analysis (Phase 4)"""
    cache_prefix = f"etf_{symbol}"
    params = {"symbol": symbol}
    
    if use_cache:
        cached = cache.get(cache_prefix, params)
        if cached:
            cached["cached"] = True
            return cached
    
    try:
        from dashboard.analyzers import FundAnalyzer
        
        analyzer = FundAnalyzer(period_ta=30)
        result = analyzer.analyze(symbol)
        
        # Get output text - StockAnalyzer uses to_string, others use format_output
        if hasattr(analyzer, 'to_string'):
            output = analyzer.to_string(result)
        elif hasattr(analyzer, 'format_output'):
            output = analyzer.format_output(result)
        else:
            output = str(result)
        
        payload = {
            "status": "success",
            "symbol": result.symbol,
            "name": result.name,
            "nav": result.nav,
            "change_percent": result.nav_change_percent,
            "high_52w": result.high_52w,
            "low_52w": result.low_52w,
            "volume": result.volume,
            "top_holdings": result.top_holdings,
            "trend": result.trend,
            "technical_status": result.technical_status,
            "output_text": output
        }
        
        if use_cache:
            cache.set(cache_prefix, params, payload)
        
        return payload
        
    except Exception as e:
        return {"status": "error", "symbol": symbol, "error": str(e)}


def run_crypto_analysis(symbol: str = "BTCUSDT", use_cache: bool = True) -> dict:
    """Run crypto analysis (Phase 4)"""
    cache_prefix = f"crypto_{symbol}"
    params = {"symbol": symbol}
    
    if use_cache:
        cached = cache.get(cache_prefix, params)
        if cached:
            cached["cached"] = True
            return cached
    
    try:
        from dashboard.analyzers import CryptoAnalyzer
        
        analyzer = CryptoAnalyzer(period_ta=30)
        result = analyzer.analyze(symbol)
        
        # Get output text - StockAnalyzer uses to_string, others use format_output
        if hasattr(analyzer, 'to_string'):
            output = analyzer.to_string(result)
        elif hasattr(analyzer, 'format_output'):
            output = analyzer.format_output(result)
        else:
            output = str(result)
        
        payload = {
            "status": "success",
            "symbol": result.symbol,
            "name": result.name,
            "current_price": result.current_price,
            "change_percent_24h": result.change_percent_24h,
            "high_24h": result.high_24h,
            "low_24h": result.low_24h,
            "trend": result.trend,
            "technical_status": result.technical_status,
            "output_text": output
        }
        
        if use_cache:
            cache.set(cache_prefix, params, payload)
        
        return payload
        
    except Exception as e:
        return {"status": "error", "symbol": symbol, "error": str(e)}


def run_cw_analysis(symbol: str, use_cache: bool = True) -> dict:
    """Run covered warrant analysis (Phase 4)"""
    cache_prefix = f"cw_{symbol}"
    params = {"symbol": symbol}
    
    if use_cache:
        cached = cache.get(cache_prefix, params)
        if cached:
            cached["cached"] = True
            return cached
    
    try:
        from dashboard.analyzers import CWAnalyzer
        
        analyzer = CWAnalyzer(period_ta=30)
        result = analyzer.analyze(symbol)
        
        # Get output text - StockAnalyzer uses to_string, others use format_output
        if hasattr(analyzer, 'to_string'):
            output = analyzer.to_string(result)
        elif hasattr(analyzer, 'format_output'):
            output = analyzer.format_output(result)
        else:
            output = str(result)
        
        payload = {
            "status": "success",
            "symbol": result.symbol,
            "underlying": result.underlying,
            "warrant_type": result.warrant_type,
            "current_price": result.current_price,
            "change_percent": result.change_percent,
            "strike_price": result.strike_price,
            "maturity_date": result.maturity_date,
            "status": result.status,
            "trend": result.trend,
            "technical_status": result.technical_status,
            "output_text": output
        }
        
        if use_cache:
            cache.set(cache_prefix, params, payload)
        
        return payload
        
    except Exception as e:
        return {"status": "error", "symbol": symbol, "error": str(e)}


# ─── Bond Analysis Runner ─────────────────────────────────────────────────

def run_bond_analysis(symbol: str = "gov_bonds", use_cache: bool = True) -> dict:
    """Run bond analysis (Government or Corporate bonds)"""
    cache_prefix = f"bond_{symbol}"
    params = {"symbol": symbol}
    
    if use_cache:
        cached = cache.get(cache_prefix, params)
        if cached:
            cached["cached"] = True
            return cached
    
    try:
        from dashboard.analyzers import BondAnalyzer
        
        analyzer = BondAnalyzer(period_ta=30)
        result = analyzer.analyze(symbol)
        
        # Get output text
        if hasattr(analyzer, 'format_output'):
            output = analyzer.format_output(result)
        else:
            output = str(result)
        
        payload = {
            "status": "success",
            "symbol": result.symbol,
            "name": result.name,
            "bond_type": result.bond_type,
            "face_value": result.face_value,
            "current_price": result.current_price,
            "coupon_rate": result.coupon_rate,
            "yield_to_maturity": result.yield_to_maturity,
            "maturity_date": result.maturity_date,
            "days_to_maturity": result.days_to_maturity,
            "change_percent": result.change_percent,
            "trend": result.trend,
            "technical_status": result.technical_status,
            "output_text": output
        }
        
        # Add bonds list if available
        if hasattr(result, 'bonds_list') and result.bonds_list is not None:
            payload["bonds_list"] = str(result.bonds_list.head(10)) if hasattr(result.bonds_list, 'head') else str(result.bonds_list)
        
        if use_cache:
            cache.set(cache_prefix, params, payload)
        
        return payload
        
    except Exception as e:
        return {"status": "error", "symbol": symbol, "error": str(e)}


def run_government_bonds_list(use_cache: bool = True) -> dict:
    """Get list of government bonds"""
    cache_prefix = "gov_bonds_list"
    params = {}
    
    if use_cache:
        cached = cache.get(cache_prefix, params)
        if cached:
            cached["cached"] = True
            return cached
    
    try:
        from dashboard.analyzers import BondAnalyzer
        
        analyzer = BondAnalyzer()
        bonds_df = analyzer.get_government_bonds_list()
        
        if bonds_df is not None and len(bonds_df) > 0:
            payload = {
                "status": "success",
                "count": len(bonds_df),
                "bonds": bonds_df.head(20).to_dict(orient="records")
            }
        else:
            payload = {
                "status": "no_data",
                "message": "Không có dữ liệu trái phiếu"
            }
        
        if use_cache:
            cache.set(cache_prefix, params, payload)
        
        return payload
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─── Batch Analysis Runner ──────────────────────────────────────────────────

def run_market_overview() -> dict:
    """Run comprehensive market overview (batch processing)"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "indices": {},
        "gold": {},
        "futures": {},
        "crypto": {},
        "bonds": {},
    }
    
    # Indices
    for idx in ["VNINDEX", "VN30", "HNXIndex"]:
        results["indices"][idx] = run_index_analysis(idx, use_cache=False)
    
    # Gold
    results["gold"]["sjc"] = run_gold_analysis("gold_vn", use_cache=False)
    results["gold"]["global"] = run_gold_analysis("gold_global", use_cache=False)
    
    # Futures
    results["futures"]["vn30f"] = run_futures_analysis("VN30F", use_cache=False)
    
    # Crypto
    results["crypto"]["btc"] = run_crypto_analysis("BTCUSDT", use_cache=False)
    results["crypto"]["eth"] = run_crypto_analysis("ETHUSDT", use_cache=False)
    
    # Bonds
    results["bonds"]["gov"] = run_government_bonds_list(use_cache=False)
    
    return results


def run_watchlist_analysis(symbols: list[str]) -> list[dict]:
    """Run stock analysis on multiple symbols (batch)"""
    results = []
    
    for symbol in symbols:
        result = run_stock_analysis(symbol, use_cache=False)
        results.append(result)
    
    return results


# ─── Cache Management ──────────────────────────────────────────────────────

def clear_all_cache() -> dict:
    """Clear all cached data"""
    count = cache.clear()
    return {"status": "success", "cleared": count}


def clear_expired_cache() -> dict:
    """Clear expired cache entries"""
    count = cache.clear_expired()
    return {"status": "success", "cleared": count}


def get_cache_stats() -> dict:
    """Get cache statistics"""
    cache_files = list(CACHE_DIR.glob("*.json"))
    total_size = sum(f.stat().st_size for f in cache_files)
    
    oldest = min(cache_files, key=lambda f: f.stat().st_mtime) if cache_files else None
    newest = max(cache_files, key=lambda f: f.stat().st_mtime) if cache_files else None
    
    return {
        "count": len(cache_files),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "oldest": oldest.stat().st_mtime if oldest else None,
        "newest": newest.stat().st_mtime if newest else None,
    }
