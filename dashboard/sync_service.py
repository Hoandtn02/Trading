"""
Sync Engine v7 - Database-First Architecture
Tốc độ: < 20s cho 100 mã với ThreadPoolExecutor
"""
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd

from django.utils import timezone
from dashboard.models import StockData, StockAnalysis, SyncStatus


# ============== CONSTANTS ==============
MAX_WORKERS = 10  # Số luồng song song
UNIVERSE_SIZE = 100  # Số mã quét
MIN_LIQUIDITY_BILLION = 15  # Thanh khoản tối thiểu (tỷ VND)
MIN_PRICE = 10000  # Giá tối thiểu


def get_market_rsi() -> float:
    """Lấy RSI của VNIndex"""
    try:
        from vnstock import Quote
        q = Quote(symbol="VNINDEX", source="vci")
        df = q.history(
            start=(datetime.now().replace(hour=0, minute=0, second=0) - pd.Timedelta(days=60)).strftime("%Y-%m-%d"),
            end=datetime.now().strftime("%Y-%m-%d"),
            interval="1D"
        )
        if df is not None and len(df) >= 15:
            close = df['close']
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1])
    except:
        pass
    return 50.0


def get_top_symbols_by_liquidity() -> List[str]:
    """Lấy Top 100 mã thanh khoản cao nhất"""
    warnings.filterwarnings('ignore')

    try:
        from vnstock import Quote, Listing

        # Lấy danh sách mã từ HOSE
        candidates = [
            "VNM", "VCB", "VHM", "VIC", "VPB", "BID", "TCB", "CTG", "MBB", "ACB",
            "STB", "HPG", "FPT", "MWG", "PNJ", "TPB", "SHB", "SSI", "MSN", "GAS",
            "PLX", "VRE", "VIB", "VJC", "SAB", "HDB", "LPB", "SSB", "GVR", "DGC",
            "KDH", "GMD", "SBT", "DGW", "CMG", "IMP", "VHC", "REE", "NT2", "BCM",
            "POW", "HAG", "NVL", "DIG", "ASM", "DRC", "HCM", "PVI", "BSR", "PVD",
            "VND", "OCB", "EIB", "KBS", "SHS", "VDS", "BVS", "TVS", "VIG", "VFM",
            "BCM", "MSB", "NAB", "EIB", "STB", "HCM", "CTS", "VCI", "SHS", "VND",
            "TPB", "MBB", "ACB", "VPB", "CTG", "TCB", "BID", "VCB", "SHB", "LPB",
            "SSB", "OCB", "HDB", "VIB", "MSB", "STB", "PGB", "KLB", "BAB", "BID",
            "NVL", "DPG", "DXG", "KDH", "HDG", "IDJ", "SJS", "FPT", "CMG", "ELC",
        ]

        # Tính thanh khoản cho từng mã
        liquidity_data = []
        for symbol in candidates:
            try:
                q = Quote(symbol=symbol)
                df = q.history(
                    start=(datetime.now() - pd.Timedelta(days=30)).strftime("%Y-%m-%d"),
                    end=datetime.now().strftime("%Y-%m-%d"),
                    interval="1D"
                )
                if df is not None and len(df) >= 10:
                    avg_volume = df['volume'].tail(20).mean()
                    avg_price = df['close'].tail(5).mean()
                    avg_value = avg_volume * avg_price

                    if avg_price > MIN_PRICE and avg_value > MIN_LIQUIDITY_BILLION * 1e9:
                        liquidity_data.append((symbol, avg_value))
            except:
                continue

        # Sort và lấy top 100
        liquidity_data.sort(key=lambda x: x[1], reverse=True)
        top_symbols = [s[0] for s in liquidity_data[:UNIVERSE_SIZE]]

        # Fallback nếu không đủ mã
        if len(top_symbols) < 5:
            print(f"[Sync] Fallback: Chỉ có {len(top_symbols)} mã đủ thanh khoản")
            # Dùng tất cả candidates đã định nghĩa
            top_symbols = candidates[:UNIVERSE_SIZE]

        return top_symbols

    except Exception as e:
        print(f"[Sync] Error getting symbols: {e}")
        return [
            "VNM", "VCB", "VHM", "VIC", "VPB", "BID", "TCB", "CTG", "MBB", "ACB",
            "STB", "HPG", "FPT", "MWG", "PNJ", "TPB", "SHB", "SSI", "MSN", "GAS",
        ][:20]


def calculate_technical_indicators(df: pd.DataFrame) -> Dict[str, float]:
    """Tính toán các chỉ báo kỹ thuật từ OHLCV data"""
    result = {
        "rsi": 50.0,
        "adx": 25.0,
        "plus_di": 0.0,
        "minus_di": 0.0,
        "cmf": 0.0,
        "atr": 0.0,
        "sma_10": 0.0,
        "sma_20": 0.0,
        "sma_50": 0.0,
        "bb_upper": 0.0,
        "bb_middle": 0.0,
        "bb_lower": 0.0,
        "bb_percent": 50.0,
        "macd": 0.0,
        "macd_signal": 0.0,
        "volume_ratio": 1.0,
    }

    if df is None or len(df) < 20:
        return result

    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']

    try:
        # Current values
        result["price"] = float(close.iloc[-1])
        if len(close) > 1:
            prev = float(close.iloc[-2])
            if prev > 0:
                result["change_percent"] = round((result["price"] - prev) / prev * 100, 2)

        # Volume Ratio
        avg_vol = volume.tail(20).mean()
        if avg_vol > 0:
            result["volume_ratio"] = round(float(volume.iloc[-1]) / avg_vol, 2)

        # ATR & ADX
        if len(df) >= 15:
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_series = tr.rolling(14).mean()
            result["atr"] = round(float(atr_series.iloc[-1]), 2)
            if result["atr"] <= 0:
                result["atr"] = round(result["price"] * 0.02, 2)  # Fallback 2%

            high_diff = high.diff()
            low_diff = -low.diff()
            plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
            minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

            plus_di = 100 * (plus_dm.rolling(14).mean() / atr_series)
            minus_di = 100 * (minus_dm.rolling(14).mean() / atr_series)
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx_values = dx.rolling(14).mean()

            result["adx"] = round(float(adx_values.iloc[-1]), 1)
            result["plus_di"] = round(float(plus_di.iloc[-1]), 1)
            result["minus_di"] = round(float(minus_di.iloc[-1]), 1)

        # RSI
        if len(close) >= 14:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            result["rsi"] = round(float(rsi.iloc[-1]), 1)

        # MACD
        if len(close) >= 26:
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            result["macd"] = round(float(macd_line.iloc[-1]), 2)
            result["macd_signal"] = round(float(signal_line.iloc[-1]), 2)

        # Bollinger Bands
        if len(close) >= 20:
            bb_middle = close.rolling(20).mean()
            bb_std = close.rolling(20).std()
            result["bb_upper"] = round(float((bb_middle + 2 * bb_std).iloc[-1]), 2)
            result["bb_middle"] = round(float(bb_middle.iloc[-1]), 2)
            result["bb_lower"] = round(float((bb_middle - 2 * bb_std).iloc[-1]), 2)
            if result["bb_upper"] > result["bb_lower"]:
                result["bb_percent"] = round(
                    (result["price"] - result["bb_lower"]) / (result["bb_upper"] - result["bb_lower"]) * 100, 1
                )

        # SMAs
        if len(close) >= 10:
            result["sma_10"] = round(float(close.rolling(10).mean().iloc[-1]), 2)
        if len(close) >= 20:
            result["sma_20"] = round(float(close.rolling(20).mean().iloc[-1]), 2)
        if len(close) >= 50:
            result["sma_50"] = round(float(close.rolling(50).mean().iloc[-1]), 2)

        # CMF
        if len(df) >= 20:
            mf_multiplier = ((close - low) - (high - close)) / (high - low)
            mf_multiplier = mf_multiplier.fillna(0)
            mf_volume = mf_multiplier * volume
            total_mf = mf_volume.rolling(20).sum().iloc[-1]
            total_vol = volume.rolling(20).sum().iloc[-1]
            result["cmf"] = round(total_mf / total_vol, 3) if total_vol > 0 else 0

    except Exception as e:
        print(f"[Sync] Error calculating indicators: {e}")

    return result


def analyze_stock(symbol: str, market_rsi: float = 50.0) -> Optional[Dict[str, Any]]:
    """Phân tích một mã cổ phiếu - trả về dict kết quả"""
    try:
        import warnings as w
        w.filterwarnings('ignore')

        # Lấy dữ liệu giá
        df = None
        try:
            from vnstock_data import Market
            mkt = Market()
            df = mkt.equity(symbol).ohlcv(
                start=(datetime.now() - pd.Timedelta(days=100)).strftime("%Y-%m-%d"),
                end=datetime.now().strftime("%Y-%m-%d")
            )
        except:
            pass

        if df is None:
            try:
                from vnstock import Quote
                q = Quote(symbol=symbol, source="vci")
                df = q.history(
                    start=(datetime.now() - pd.Timedelta(days=100)).strftime("%Y-%m-%d"),
                    end=datetime.now().strftime("%Y-%m-%d"),
                    interval="1D"
                )
            except:
                return None

        if df is None or len(df) < 20:
            return None

        # Calculate indicators
        tech = calculate_technical_indicators(df)

        # Trading Levels - FIX INVERTED SL
        entry = tech["price"]
        min_distance = entry * 0.03  # 3% minimum

        # Find support
        supports = [s for s in [tech["bb_lower"], tech["sma_20"], entry - (tech["atr"] * 2)] if s > 0]
        raw_sl = max(supports) if supports else entry * 0.95

        # Ensure SL < Entry and >= 3% distance
        if entry - raw_sl < min_distance:
            raw_sl = entry - min_distance
        if raw_sl >= entry:
            raw_sl = entry * 0.95
            has_inverted_sl = True
        else:
            has_inverted_sl = False

        stop_loss = round(raw_sl, 2)
        take_profit = round(max(tech["bb_upper"], entry * 1.10), 2)

        # R:R
        risk = entry - stop_loss
        reward = take_profit - entry
        if risk >= min_distance:
            rr_ratio = round(reward / risk, 2)
        else:
            rr_ratio = 0

        # Est Days
        if tech["atr"] > 0:
            price_diff = take_profit - entry
            est_days = max(price_diff / tech["atr"], 1)
            if market_rsi > 80:
                est_days += 3
        else:
            est_days = 5

        # VETO CHECK
        is_vetoed = False
        veto_reason = ""
        if tech["cmf"] < 0:
            is_vetoed = True
            veto_reason = "CMF Negative"
        elif rr_ratio == 0:
            is_vetoed = True
            veto_reason = "R:R = 0"
        elif tech["atr"] <= 0:
            is_vetoed = True
            veto_reason = "ATR = 0"

        # CRITERIA
        criteria = []
        if not is_vetoed:
            if 50 <= tech["rsi"] <= 65:
                criteria.append("RSI Sweet Spot")
            if tech["adx"] > 20:
                criteria.append("ADX Strong")
            if tech["plus_di"] > tech["minus_di"]:
                criteria.append("DI Bullish")
            if tech["cmf"] > 0:
                criteria.append("CMF Positive")
            if tech["volume_ratio"] > 1.0:
                criteria.append("Volume Active")
            if tech["sma_20"] > 0 and tech["price"] > tech["sma_20"]:
                criteria.append("Above SMA20")
            if tech["macd"] > tech["macd_signal"]:
                criteria.append("MACD Bullish")
            if rr_ratio >= 2.0:
                criteria.append("R:R >= 2.0")
            elif rr_ratio >= 1.5:
                criteria.append("R:R >= 1.5")
            if est_days <= 10:
                criteria.append("Fast Holding")

        criteria_met = len(criteria)

        # SCORES
        tech_score = 50
        if not is_vetoed:
            # RSI
            if 50 <= tech["rsi"] <= 65:
                tech_score += 12 if 55 <= tech["rsi"] <= 62 else 8
            elif tech["rsi"] > 70:
                tech_score -= 15
            elif tech["rsi"] > 65:
                tech_score -= 8

            # ADX
            if tech["adx"] > 25:
                tech_score += 12
            elif tech["adx"] > 20:
                tech_score += 8

            # CMF
            if tech["cmf"] > 0.1:
                tech_score += 12
            elif tech["cmf"] > 0:
                tech_score += 8
            else:
                tech_score -= 15

            # Volume
            if tech["volume_ratio"] > 1.5:
                tech_score += 8
            elif tech["volume_ratio"] > 1.0:
                tech_score += 5

            # R:R
            if rr_ratio >= 2.0:
                tech_score += 10
            elif rr_ratio >= 1.5:
                tech_score += 6
            elif rr_ratio < 1.0:
                tech_score -= 10

            # Inverted SL
            if has_inverted_sl:
                tech_score -= 10

            # FAST
            if tech["adx"] > 18 and tech["volume_ratio"] > 0.8:
                is_fast_pick = True
            else:
                is_fast_pick = False
        else:
            tech_score = 35
            is_fast_pick = False

        tech_score = max(0, min(100, tech_score))
        fund_score = 50  # Simplified

        # SIGNAL
        is_sell_zone = market_rsi > 70

        if is_vetoed:
            signal = "WAIT"
        elif criteria_met >= 9:
            if is_sell_zone:
                signal = "STRONG_BUY" if (tech["adx"] > 25 and tech["volume_ratio"] > 1.0) else "WATCH"
            else:
                signal = "STRONG_BUY"
        elif tech_score >= 75:
            signal = "STRONG_BUY" if not is_sell_zone else "BUY"
        elif tech_score >= 65:
            signal = "BUY" if not is_sell_zone else "ACCUMULATE"
        elif tech_score >= 55:
            signal = "ACCUMULATE"
        else:
            signal = "WAIT"

        # Trend
        if tech["sma_20"] > 0 and tech["sma_50"] > 0:
            if tech["price"] > tech["sma_20"] > tech["sma_50"]:
                trend = "UPTREND"
            elif tech["price"] < tech["sma_20"] < tech["sma_50"]:
                trend = "DOWNTREND"
            else:
                trend = "SIDEWAYS"
        else:
            trend = "SIDEWAYS"

        return {
            "symbol": symbol,
            "price": tech["price"],
            "change_percent": tech["change_percent"],
            "rsi": tech["rsi"],
            "adx": tech["adx"],
            "plus_di": tech["plus_di"],
            "minus_di": tech["minus_di"],
            "cmf": tech["cmf"],
            "atr": tech["atr"],
            "sma_10": tech["sma_10"],
            "sma_20": tech["sma_20"],
            "sma_50": tech["sma_50"],
            "bb_upper": tech["bb_upper"],
            "bb_middle": tech["bb_middle"],
            "bb_lower": tech["bb_lower"],
            "bb_percent": tech["bb_percent"],
            "macd": tech["macd"],
            "macd_signal": tech["macd_signal"],
            "volume_ratio": tech["volume_ratio"],
            "volume": int(df['volume'].iloc[-1]) if 'volume' in df.columns else 0,
            "avg_volume_value": round(tech["volume_ratio"] * tech["price"] * df['volume'].tail(20).mean() / 1e9, 1) if 'volume' in df.columns else 0,
            "entry_price": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": rr_ratio,
            "estimated_days_to_target": round(est_days, 1),
            "master_score": int(tech_score * 0.7 + fund_score * 0.3),
            "technical_score": tech_score,
            "fundamental_score": fund_score,
            "signal": signal,
            "is_vetoed": is_vetoed,
            "veto_reason": veto_reason,
            "is_fast_pick": is_fast_pick,
            "is_short_term_qualified": not is_vetoed and criteria_met >= 9,
            "is_slow_mode": est_days > 10,
            "is_high_risk": False,
            "has_inverted_sl": has_inverted_sl,
            "criteria_met": criteria_met,
            "criteria_list": criteria,
            "trend": trend,
            "breakout_status": "🚨 BREAKOUT" if is_fast_pick and not is_vetoed else ("🛑 VETO" if is_vetoed else "⏳ WAIT"),
            "market_rsi": market_rsi,
        }

    except Exception as e:
        print(f"[Sync] Error analyzing {symbol}: {e}")
        return None


def sync_stock_batch(symbols: List[str], market_rsi: float = 50.0) -> Dict[str, Any]:
    """Đồng bộ một batch mã cổ phiếu với ThreadPoolExecutor"""
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(analyze_stock, symbol, market_rsi): symbol for symbol in symbols}

        for future in as_completed(futures):
            symbol = futures[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                print(f"[Sync] Error processing {symbol}: {e}")

    return {"results": results, "count": len(results)}


def sync_market_data(force: bool = False) -> Dict[str, Any]:
    """
    Đồng bộ toàn bộ dữ liệu thị trường
    - Lấy Top 100 mã theo thanh khoản
    - Tính indicators cho từng mã song song
    - Lưu vào Database
    """
    start_time = datetime.now()

    # Tạo hoặc cập nhật sync status
    sync_record, created = SyncStatus.objects.get_or_create(
        id=1,
        defaults={
            "status": "running",
            "total_symbols": UNIVERSE_SIZE,
            "processed_symbols": 0,
            "started_at": timezone.now()
        }
    )
    sync_record.status = "running"
    sync_record.started_at = timezone.now()
    sync_record.save()

    try:
        # Bước 1: Lấy danh sách Top 100
        print(f"[Sync] Getting top {UNIVERSE_SIZE} symbols by liquidity...")
        symbols = get_top_symbols_by_liquidity()
        sync_record.total_symbols = len(symbols)
        sync_record.save()

        # Bước 2: Lấy Market RSI
        market_rsi = get_market_rsi()
        print(f"[Sync] Market RSI: {market_rsi}")

        # Bước 3: Đồng bộ song song
        print(f"[Sync] Syncing {len(symbols)} symbols with {MAX_WORKERS} workers...")
        batch_result = sync_stock_batch(symbols, market_rsi)
        results = batch_result["results"]

        # Bước 4: Lưu vào Database
        print(f"[Sync] Saving {len(results)} results to database...")

        StockData.objects.all().delete()  # Xóa cũ
        StockAnalysis.objects.all().delete()  # Xóa cũ

        for data in results:
            symbol = data["symbol"]

            # Create StockData
            stock, _ = StockData.objects.update_or_create(
                symbol=symbol,
                defaults={
                    "price": data["price"],
                    "change_percent": data["change_percent"],
                    "volume": data["volume"],
                    "avg_volume_value": data["avg_volume_value"],
                    "rsi": data["rsi"],
                    "adx": data["adx"],
                    "plus_di": data["plus_di"],
                    "minus_di": data["minus_di"],
                    "cmf": data["cmf"],
                    "atr": data["atr"],
                    "sma_10": data["sma_10"],
                    "sma_20": data["sma_20"],
                    "sma_50": data["sma_50"],
                    "bb_upper": data["bb_upper"],
                    "bb_middle": data["bb_middle"],
                    "bb_lower": data["bb_lower"],
                    "bb_percent": data["bb_percent"],
                    "macd": data["macd"],
                    "macd_signal": data["macd_signal"],
                    "volume_ratio": data["volume_ratio"],
                }
            )

            # Create StockAnalysis
            StockAnalysis.objects.update_or_create(
                symbol=stock,
                defaults={
                    "master_score": data["master_score"],
                    "technical_score": data["technical_score"],
                    "fundamental_score": data["fundamental_score"],
                    "signal": data["signal"],
                    "entry_price": data["entry_price"],
                    "stop_loss": data["stop_loss"],
                    "take_profit": data["take_profit"],
                    "risk_reward_ratio": data["risk_reward_ratio"],
                    "is_vetoed": data["is_vetoed"],
                    "veto_reason": data["veto_reason"],
                    "is_fast_pick": data["is_fast_pick"],
                    "is_short_term_qualified": data["is_short_term_qualified"],
                    "is_slow_mode": data["is_slow_mode"],
                    "is_high_risk": data["is_high_risk"],
                    "has_inverted_sl": data["has_inverted_sl"],
                    "estimated_days_to_target": data["estimated_days_to_target"],
                    "criteria_met": data["criteria_met"],
                    "criteria_list": data["criteria_list"],
                    "trend": data["trend"],
                    "breakout_status": data["breakout_status"],
                    "market_rsi": data["market_rsi"],
                }
            )

            sync_record.processed_symbols += 1
            sync_record.save()

        # Update sync status
        sync_record.status = "completed"
        sync_record.completed_at = timezone.now()
        sync_record.save()

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"[Sync] Completed in {elapsed:.1f}s")

        return {
            "status": "success",
            "total": len(results),
            "vetoed": sum(1 for r in results if r["is_vetoed"]),
            "fast_picks": sum(1 for r in results if r["is_fast_pick"] and not r["is_vetoed"]),
            "elapsed_seconds": elapsed,
            "market_rsi": market_rsi,
        }

    except Exception as e:
        sync_record.status = "failed"
        sync_record.error_message = str(e)
        sync_record.completed_at = timezone.now()
        sync_record.save()
        print(f"[Sync] Failed: {e}")
        return {"status": "error", "message": str(e)}


def get_top_picks_from_db(limit: int = 10) -> List[Dict]:
    """Lấy Top Picks từ Database - cực nhanh"""
    analyses = StockAnalysis.objects.select_related('symbol').filter(
        is_vetoed=False
    ).order_by('-risk_reward_ratio', '-master_score')[:limit]

    results = []
    for a in analyses:
        results.append({
            "symbol": a.symbol.symbol,
            "company_name": a.symbol.company_name,
            "current_price": a.symbol.price,
            "price": a.symbol.price,
            "change_percent": a.symbol.change_percent,
            "rsi": a.symbol.rsi,
            "adx": a.symbol.adx,
            "plus_di": a.symbol.plus_di,
            "minus_di": a.symbol.minus_di,
            "cmf": a.symbol.cmf,
            "atr": a.symbol.atr,
            "sma_20": a.symbol.sma_20,
            "macd": a.symbol.macd,
            "macd_signal": a.symbol.macd_signal,
            "volume_ratio": a.symbol.volume_ratio,
            "entry_price": a.entry_price,
            "stop_loss": a.stop_loss,
            "take_profit": a.take_profit,
            "risk_reward_ratio": a.risk_reward_ratio,
            "estimated_days_to_target": a.estimated_days_to_target,
            "master_score": a.master_score,
            "technical_score": a.technical_score,
            "fundamental_score": a.fundamental_score,
            "signal": a.signal,
            "is_fast_pick": a.is_fast_pick,
            "is_vetoed": a.is_vetoed,
            "veto_reason": a.veto_reason,
            "is_high_risk": a.is_high_risk,
            "is_slow_mode": a.is_slow_mode,
            "criteria_met": a.criteria_met,
            "criteria_list": a.criteria_list or [],
            "trend": a.trend,
            "breakout_status": a.breakout_status,
            "market_rsi": a.market_rsi,
        })

    return results


def get_sync_status() -> Optional[Dict]:
    """Lấy trạng thái sync cuối cùng"""
    try:
        sync = SyncStatus.objects.get(id=1)
        return {
            "status": sync.status,
            "total_symbols": sync.total_symbols,
            "processed_symbols": sync.processed_symbols,
            "progress_percent": sync.progress_percent,
            "is_running": sync.is_running,
            "started_at": sync.started_at.isoformat() if sync.started_at else None,
            "completed_at": sync.completed_at.isoformat() if sync.completed_at else None,
            "error_message": sync.error_message,
        }
    except:
        return None
