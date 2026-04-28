"""
Sync Engine v9 - Database-First Architecture (FULL SYNC)
- Uses vnstock_data for Fundamental data (like single-stock analyzer)
- Adds VWAP, Ichimoku, SuperTrend, MFI indicators
- Fixes Change% calculation
- Adds F-Score
- Applies consistent veto rules across all stocks
"""
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd

from django.utils import timezone
from dashboard.models import StockData, StockAnalysis, SyncStatus, VN30_SYMBOLS


# ============== CONSTANTS ==============
MAX_WORKERS = 8
UNIVERSE_SIZE = 100
MIN_LIQUIDITY_BILLION = 15
MIN_PRICE = 10000


def get_market_rsi() -> float:
    """Lấy RSI của VNIndex"""
    try:
        from vnstock import Quote
        q = Quote(symbol="VNINDEX")
        df = q.history(
            start=(datetime.now() - pd.Timedelta(days=60)).strftime("%Y-%m-%d"),
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


def get_company_name(symbol: str) -> str:
    """Lấy tên công ty từ vnstock"""
    try:
        from vnstock import Company
        company = Company(symbol=symbol, source="vci")
        info = company.overview()
        if info is not None and not info.empty:
            if 'company_name' in info.columns:
                return str(info['company_name'].iloc[0])
            elif 'name' in info.columns:
                return str(info['name'].iloc[0])
    except:
        pass
    return symbol


def get_fundamental_data(symbol: str) -> Dict[str, Any]:
    """
    Lấy dữ liệu cơ bản từ vnstock_data (Unified API) hoặc vnstock fallback
    Returns: {roe, pe, pb, f_score, f_score_grade, profit_growth}
    """
    result = {
        "roe": None,
        "pe": None,
        "pb": None,
        "f_score": 0,
        "f_score_grade": "N/A",
        "profit_growth": None,  # NEW: Quý gần nhất vs cùng kỳ năm trước
    }

    def safe_float(val):
        """Convert value to float safely"""
        if val is None or pd.isna(val):
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    # Try vnstock_data first (Silver+)
    try:
        from vnstock_data import Fundamental
        import warnings as w
        w.filterwarnings('ignore')

        fun = Fundamental()

        # Get financial ratios - try year first, then quarter
        ratios = None
        for period in ["year", "quarter"]:
            try:
                ratios = fun.equity(symbol).ratio(period=period)
                if ratios is not None and len(ratios) > 0:
                    break
            except:
                continue

        if ratios is not None and len(ratios) > 0:
            # IMPORTANT: Index 0 = newest data, Index -1 = oldest data
            # Get the latest row (index 0)
            if hasattr(ratios, 'iloc'):
                latest = ratios.iloc[0]  # Use index 0 for newest data
            else:
                latest = ratios

            # Try multiple possible column names for PE
            for col_name in ['pe', 'PE', 'P/E', 'price_to_earnings', 'pe_ratio']:
                if col_name in ratios.columns:
                    val = safe_float(latest.get(col_name))
                    if val is not None and 0 < val < 1000:
                        result['pe'] = val
                        break

            # Try multiple possible column names for PB
            for col_name in ['pb', 'PB', 'P/B', 'price_to_book', 'pb_ratio', 'book_value_per_share']:
                if col_name in ratios.columns:
                    val = safe_float(latest.get(col_name))
                    if val is not None and 0 < val < 100:
                        # book_value_per_share might need different handling
                        if col_name == 'book_value_per_share':
                            continue  # Skip, we'll calculate PB differently
                        result['pb'] = val
                        break

            # Try to find ROE or calculate from available data
            for col_name in ['roe', 'ROE', 'return_on_equity', 'roe_ratio']:
                if col_name in ratios.columns:
                    val = safe_float(latest.get(col_name))
                    if val is not None:
                        # ROE might be in decimal (0.15) or percentage (15)
                        if abs(val) < 1:  # Likely decimal form
                            val *= 100
                        result['roe'] = round(val, 2)
                        break

            # Calculate ROE from PE/PB if not found
            if result['roe'] is None and result['pe'] and result['pb'] and result['pe'] > 0:
                result['roe'] = round((result['pb'] / result['pe']) * 100, 2)

    except Exception as e:
        # print(f"[{symbol}] vnstock_data error: {e}")
        pass

    # Fallback: try vnstock
    if result['pe'] is None or result['pb'] is None or result['roe'] is None:
        try:
            from vnstock import Finance
            fin = Finance(symbol=symbol, source="vci")

            # Try to get ratios
            ratios = fin.ratio(period="quarter")
            if ratios is not None and not ratios.empty:
                # Get first row (newest data)
                for col in ratios.columns:
                    col_lower = str(col).lower()

                    # ROE
                    if ('roe' in col_lower or 'return on equity' in col_lower) and result['roe'] is None:
                        val = ratios[col].iloc[0] if hasattr(ratios[col], 'iloc') else ratios[col]
                        val = safe_float(val)
                        if val is not None:
                            if abs(val) < 1:  # Decimal form
                                val *= 100
                            result['roe'] = round(val, 2)

                    # PE
                    if ('pe' in col_lower or 'p/e' in col_lower) and result['pe'] is None:
                        val = ratios[col].iloc[0] if hasattr(ratios[col], 'iloc') else ratios[col]
                        val = safe_float(val)
                        if val is not None and 0 < val < 1000:
                            result['pe'] = val

                    # PB
                    if ('pb' in col_lower or 'p/b' in col_lower or 'book' in col_lower) and result['pb'] is None:
                        val = ratios[col].iloc[0] if hasattr(ratios[col], 'iloc') else ratios[col]
                        val = safe_float(val)
                        if val is not None and 0 < val < 100:
                            result['pb'] = val

        except Exception as e:
            # print(f"[{symbol}] vnstock fallback error: {e}")
            pass

    # Calculate ROE from PE/PB if still missing
    if result['roe'] is None and result['pe'] and result['pb'] and result['pe'] > 0:
        result['roe'] = round((result['pb'] / result['pe']) * 100, 2)

    # NEW: Calculate Profit Growth from income statement (latest quarter vs same quarter last year)
    result['profit_growth'] = calculate_profit_growth(symbol)

    # Calculate F-Score
    result['f_score'] = calculate_f_score(symbol, result)
    result['f_score_grade'] = get_f_score_grade(result['f_score'])

    return result


def calculate_profit_growth(symbol: str) -> Optional[float]:
    """
    Calculate profit growth: (LNST quý gần nhất / LNST quý cùng kỳ năm trước) - 1
    Returns growth percentage or None if unavailable
    """
    try:
        from vnstock_data import Fundamental
        import warnings as w
        w.filterwarnings('ignore')

        fun = Fundamental()
        income = fun.equity(symbol).income_statement(limit=8)

        if income is None or len(income) < 4:
            return None

        # Find net profit column
        net_profit_col = None
        for col in income.columns:
            col_lower = str(col).lower()
            if ('net' in col_lower and 'profit' in col_lower) or 'lnst' in col_lower:
                net_profit_col = col
                break

        if net_profit_col is None:
            return None

        # Index 0 = newest, index 1 = prev quarter, index 4 = same quarter last year (roughly)
        # Get quarter index from first row
        latest_date = income.index[0]
        latest_profit = income.loc[latest_date, net_profit_col]

        if latest_profit is None or float(latest_profit) <= 0:
            return None

        # Find same quarter last year - iterate through rows to match quarter
        import pandas as pd
        if isinstance(latest_date, str):
            latest_dt = pd.to_datetime(latest_date)
        else:
            latest_dt = latest_date

        same_quarter_last_year = None
        for i in range(1, min(5, len(income))):
            row_date = income.index[i]
            if isinstance(row_date, str):
                row_dt = pd.to_datetime(row_date)
            else:
                row_dt = row_date

            # Check if same quarter (quarter number should match)
            if (latest_dt.month // 4) == (row_dt.month // 4) and latest_dt.year == row_dt.year + 1:
                same_quarter_last_year = income.loc[row_date, net_profit_col]
                break

        if same_quarter_last_year is None or float(same_quarter_last_year) <= 0:
            return None

        growth = (float(latest_profit) / float(same_quarter_last_year)) - 1
        return round(growth * 100, 2)  # Return as percentage

    except Exception as e:
        pass
    return None


def calculate_f_score(symbol: str, fund_data: dict = None) -> int:
    """
    Calculate Piotroski F-Score (0-9)
    fund_data: Optional dict with ROE, PE, PB to use in score calculation
    """
    score = 0

    try:
        from vnstock_data import Fundamental
        import warnings as w
        w.filterwarnings('ignore')

        fun = Fundamental()

        income = fun.equity(symbol).income_statement(limit=8)
        balance = fun.equity(symbol).balance_sheet(limit=8)
        cf = fun.equity(symbol).cash_flow(limit=8)

        if income is None or len(income.columns) < 2:
            return 0

        # Get latest period
        latest_row = income.index[0]
        prev_row = income.index[1] if len(income.index) > 1 else None

        # Helper
        def get_val(df, row, col):
            try:
                if col in df.columns:
                    return df.loc[row, col]
            except:
                pass
            return None

        # 1. ROA > 0
        ni_col = 'net_profit_after_tax' if 'net_profit_after_tax' in income.columns else None
        ta_col = 'total_assets' if 'total_assets' in balance.columns else None
        if ni_col and ta_col:
            ni = get_val(income, latest_row, ni_col)
            ta = get_val(balance, latest_row, ta_col)
            if ni and ta and float(ta) != 0:
                roa = float(ni) / float(ta)
                if roa > 0:
                    score += 1

        # 2. OCF > 0
        ocf_col = None
        for col in cf.columns:
            if 'operating' in col.lower() and 'cash' in col.lower():
                ocf_col = col
                break
        if ocf_col:
            ocf = get_val(cf, latest_row, ocf_col)
            if ocf and float(ocf) > 0:
                score += 1

        # 3. ROA increase YoY
        # (simplified - skip for speed)

        # 4. CFO > Net Income
        if ocf_col and ni_col:
            ocf_val = get_val(cf, latest_row, ocf_col)
            ni_val = get_val(income, latest_row, ni_col)
            if ocf_val and ni_val and float(ocf_val) > float(ni_val):
                score += 1

        # 5. Leverage decrease
        if ta_col:
            current_assets_col = 'total_current_assets' if 'total_current_assets' in balance.columns else None
            if current_assets_col:
                ca = get_val(balance, latest_row, current_assets_col)
                if ta and ca and float(ta) > 0:
                    de_ratio = float(ta) / float(ca) if float(ca) > 0 else 0
                    if prev_row:
                        ca_prev = get_val(balance, prev_row, current_assets_col)
                        ta_prev = get_val(balance, prev_row, ta_col)
                        if ca_prev and ta_prev and float(ta_prev) > 0:
                            de_ratio_prev = float(ta_prev) / float(ca_prev)
                            if de_ratio < de_ratio_prev:
                                score += 1

        # 6. Current ratio increase
        if current_assets_col and 'total_current_liabilities' in balance.columns:
            cl = get_val(balance, latest_row, 'total_current_liabilities')
            if ca and cl and float(cl) > 0:
                cr = float(ca) / float(cl)
                if prev_row:
                    cl_prev = get_val(balance, prev_row, 'total_current_liabilities')
                    ca_prev = get_val(balance, prev_row, current_assets_col)
                    if ca_prev and cl_prev and float(cl_prev) > 0:
                        cr_prev = float(ca_prev) / float(cl_prev)
                        if cr > cr_prev:
                            score += 1

        # 7-9. Margin/Asset improvements (simplified for speed)
        # Use fund_data if provided
        _roe = fund_data.get('roe', 0) if fund_data else None
        _pe = fund_data.get('pe', 0) if fund_data else None
        _pb = fund_data.get('pb', 0) if fund_data else None
        
        if _roe and _roe > 10:
            score += 1
        if _pe and 5 < _pe < 25:
            score += 1
        if _pb and _pb < 3:
            score += 1

    except:
        pass

    return min(score, 9)


def get_f_score_grade(score: int) -> str:
    """Convert F-Score to grade"""
    if score >= 8:
        return "A"
    elif score >= 6:
        return "B"
    elif score >= 4:
        return "C"
    elif score >= 2:
        return "D"
    else:
        return "F"


def get_top_symbols_by_liquidity() -> List[str]:
    """Lấy Top 100 mã thanh khoản cao nhất"""
    warnings.filterwarnings('ignore')

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

    try:
        from vnstock import Quote
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

        liquidity_data.sort(key=lambda x: x[1], reverse=True)
        top_symbols = [s[0] for s in liquidity_data[:UNIVERSE_SIZE]]

        if len(top_symbols) < 5:
            print(f"[Sync] Fallback: Chỉ có {len(top_symbols)} mã đủ thanh khoản")
            top_symbols = candidates[:UNIVERSE_SIZE]

        return top_symbols

    except Exception as e:
        print(f"[Sync] Error getting symbols: {e}")
        return [
            "VNM", "VCB", "VHM", "VIC", "VPB", "BID", "TCB", "CTG", "MBB", "ACB",
            "STB", "HPG", "FPT", "MWG", "PNJ", "TPB", "SHB", "SSI", "MSN", "GAS",
        ][:20]


def calculate_technical_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate technical indicators using vnstock_ta
    Includes: RSI, MACD, ADX, CMF, Bollinger, SMA, VWAP, Ichimoku, SuperTrend, MFI
    """
    result = {
        "price": 0.0,
        "change_percent": 0.0,
        "volume": 0,
        "rsi": 50.0,
        "mfi": 50.0,
        "adx": 25.0,
        "plus_di": 0.0,
        "minus_di": 0.0,
        "cmf": 0.0,
        "sma_10": 0.0,
        "sma_20": 0.0,
        "sma_50": 0.0,
        "bb_upper": 0.0,
        "bb_middle": 0.0,
        "bb_lower": 0.0,
        "bb_percent": 50.0,
        "macd": 0.0,
        "macd_signal": 0.0,
        "atr": 0.0,
        "vwap": 0.0,
        "vwap_status": "neutral",
        "ichimoku_tenkan": 0.0,
        "ichimoku_kijun": 0.0,
        "ichimoku_status": "neutral",
        "supertrend": 0.0,
        "supertrend_signal": "neutral",
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
        result["volume"] = int(volume.iloc[-1]) if 'volume' in df.columns else 0

        # Change Percent
        if len(close) > 1:
            prev_close = float(close.iloc[-2])
            if prev_close > 0:
                result["change_percent"] = round((result["price"] - prev_close) / prev_close * 100, 2)

        # Volume Ratio
        avg_vol = volume.tail(20).mean()
        if avg_vol > 0:
            result["volume_ratio"] = round(float(volume.iloc[-1]) / avg_vol, 2)

        # Try vnstock_ta
        try:
            from vnstock_ta import Indicator
            ind = Indicator(data=df)

            # RSI
            try:
                rsi_series = ind.rsi(length=14)
                if rsi_series is not None and len(rsi_series) > 0:
                    result["rsi"] = round(float(rsi_series.iloc[-1]), 1)
            except Exception:
                pass

            # ADX
            try:
                adx_df = ind.adx(length=14)
                if adx_df is not None and len(adx_df) > 0 and hasattr(adx_df, 'columns'):
                    for col in adx_df.columns:
                        col_str = str(col).upper()
                        if 'ADX' in col_str and 'DMP' not in col_str and 'DMN' not in col_str:
                            result["adx"] = round(float(adx_df[col].iloc[-1]), 1)
                            break
                    for col in adx_df.columns:
                        col_str = str(col).upper()
                        if 'DMP' in col_str or 'PLUS' in col_str:
                            result["plus_di"] = round(float(adx_df[col].iloc[-1]), 1)
                            break
                    for col in adx_df.columns:
                        col_str = str(col).upper()
                        if 'DMN' in col_str or 'MINUS' in col_str:
                            result["minus_di"] = round(float(adx_df[col].iloc[-1]), 1)
                            break
            except Exception:
                pass

            # MACD
            try:
                macd_df = ind.macd(fast=12, slow=26, signal=9)
                if macd_df is not None and len(macd_df) > 0 and hasattr(macd_df, 'columns'):
                    cols = list(macd_df.columns)
                    if len(cols) >= 1:
                        result["macd"] = round(float(macd_df[cols[0]].iloc[-1]), 2)
                    if len(cols) >= 2:
                        result["macd_signal"] = round(float(macd_df[cols[1]].iloc[-1]), 2)
            except Exception:
                pass

            # SMA
            try:
                sma_20_series = ind.sma(length=20)
                if sma_20_series is not None and len(sma_20_series) > 0:
                    result["sma_20"] = round(float(sma_20_series.iloc[-1]), 2)
            except Exception:
                pass

            try:
                sma_10_series = ind.sma(length=10)
                if sma_10_series is not None and len(sma_10_series) > 0:
                    result["sma_10"] = round(float(sma_10_series.iloc[-1]), 2)
            except Exception:
                pass

            try:
                sma_50_series = ind.sma(length=50)
                if sma_50_series is not None and len(sma_50_series) > 0:
                    result["sma_50"] = round(float(sma_50_series.iloc[-1]), 2)
            except Exception:
                pass

            # Bollinger
            try:
                bb_df = ind.bbands(length=20, std=2)
                if bb_df is not None and len(bb_df) > 0 and hasattr(bb_df, 'columns'):
                    cols = list(bb_df.columns)
                    for col in cols:
                        if 'BBL' in col.upper():
                            result["bb_lower"] = round(float(bb_df[col].iloc[-1]), 2)
                        elif 'BBM' in col.upper():
                            result["bb_middle"] = round(float(bb_df[col].iloc[-1]), 2)
                        elif 'BBU' in col.upper():
                            result["bb_upper"] = round(float(bb_df[col].iloc[-1]), 2)

                    if result["bb_upper"] > result["bb_lower"]:
                        result["bb_percent"] = round((result["price"] - result["bb_lower"]) / (result["bb_upper"] - result["bb_lower"]) * 100, 1)
            except Exception:
                pass

            # CMF
            try:
                cmf_series = ind.cmf(length=20)
                if cmf_series is not None and len(cmf_series) > 0:
                    result["cmf"] = round(float(cmf_series.iloc[-1]), 3)
            except Exception:
                pass

            # ATR
            try:
                atr_series = ind.atr(length=14)
                if atr_series is not None and len(atr_series) > 0:
                    result["atr"] = round(float(atr_series.iloc[-1]), 2)
            except Exception:
                pass

        except ImportError:
            pass

        # Manual ATR fallback
        if result["atr"] <= 0 and len(df) >= 15:
            try:
                tr1 = high - low
                tr2 = abs(high - close.shift(1))
                tr3 = abs(low - close.shift(1))
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr_series = tr.rolling(14).mean()
                result["atr"] = round(float(atr_series.iloc[-1]), 2) if not pd.isna(atr_series.iloc[-1]) else 0
            except Exception:
                pass

        # ATR fallback to percentage
        if result["atr"] <= 0 or result["atr"] is None:
            result["atr"] = round(result["price"] * 0.02, 2) if result["price"] > 0 else 1000

        # Manual RSI fallback
        if result["rsi"] == 50.0:
            try:
                delta = close.diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                result["rsi"] = round(float(rsi.iloc[-1]), 1) if not pd.isna(rsi.iloc[-1]) else 50
            except Exception:
                pass

        # Manual CMF
        if result["cmf"] == 0.0:
            try:
                mfm = ((close - low) - (high - close)) / (high - low)
                mfm = mfm.fillna(0)
                mfv = mfm * volume
                cmf = mfv.rolling(20).sum() / volume.rolling(20).sum()
                result["cmf"] = round(float(cmf.iloc[-1]), 4) if not pd.isna(cmf.iloc[-1]) else 0
            except Exception:
                pass

        # Manual MFI
        if result["mfi"] == 50.0:
            try:
                typical_price = (high + low + close) / 3
                money_flow = typical_price * volume
                positive_flow = money_flow.where(typical_price > typical_price.shift(), 0).rolling(14).sum()
                negative_flow = money_flow.where(typical_price < typical_price.shift(), 0).rolling(14).sum()
                money_ratio = positive_flow / negative_flow.replace(0, 1)
                mfi = 100 - (100 / (1 + money_ratio))
                result["mfi"] = round(float(mfi.iloc[-1]), 1) if not pd.isna(mfi.iloc[-1]) else 50
            except Exception:
                pass

        # VWAP
        try:
            typical_price = (high + low + close) / 3
            cum_vol = volume.cumsum()
            vwap_value = (typical_price * volume).cumsum() / cum_vol
            result["vwap"] = round(float(vwap_value.iloc[-1]), 2)
            result["vwap_status"] = "above" if result["price"] > result["vwap"] else "below"
        except Exception:
            result["vwap"] = result["price"]
            result["vwap_status"] = "neutral"

        # Ichimoku
        if len(df) >= 52:
            try:
                high_9 = high.rolling(9).max()
                low_9 = low.rolling(9).min()
                result["ichimoku_tenkan"] = round((high_9 + low_9).iloc[-1] / 2, 2)

                high_26 = high.rolling(26).max()
                low_26 = low.rolling(26).min()
                result["ichimoku_kijun"] = round((high_26 + low_26).iloc[-1] / 2, 2)

                tenkan = result["ichimoku_tenkan"]
                kijun = result["ichimoku_kijun"]
                price = result["price"]

                if price > tenkan > kijun:
                    result["ichimoku_status"] = "bullish"
                elif price < tenkan < kijun:
                    result["ichimoku_status"] = "bearish"
                else:
                    result["ichimoku_status"] = "neutral"
            except Exception:
                pass

        # SuperTrend
        try:
            if result["atr"] > 0:
                hl2 = (high + low) / 2
                lower_band = hl2 - (result["atr"] * 2)
                result["supertrend"] = round(float(lower_band.iloc[-1]), 2)
                result["supertrend_signal"] = "bullish" if result["price"] > result["supertrend"] else "bearish"
        except Exception:
            pass

    except Exception as e:
        print(f"[Sync] Error calculating indicators: {e}")

    return result


def analyze_stock(symbol: str, market_rsi: float = 50.0) -> Optional[Dict[str, Any]]:
    """Phân tích một mã cổ phiếu - trả về dict kết quả"""
    try:
        import warnings as w
        w.filterwarnings('ignore')

        # Get Company Name
        company_name = get_company_name(symbol)

        # Get Fundamental Data (ROE, P/E, P/B, F-Score)
        fund_data = get_fundamental_data(symbol)

        # Get Price Data - try vnstock_data first
        df = None
        try:
            from vnstock_data import Market
            mkt = Market()
            df = mkt.equity(symbol).ohlcv(
                start=(datetime.now() - pd.Timedelta(days=100)).strftime("%Y-%m-%d"),
                end=datetime.now().strftime("%Y-%m-%d")
            )
            if df is not None and len(df) > 0:
                # Convert to correct price scale
                for col in ['open', 'high', 'low', 'close']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce') * 1000
                if 'time' in df.columns:
                    df.set_index('time', inplace=True)
        except:
            pass

        if df is None:
            try:
                from vnstock import Quote
                q = Quote(symbol=symbol)
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

        # Trading Levels - ATR-based Stop Loss
        entry = tech["price"]
        atr_value = tech["atr"] if tech["atr"] > 0 else entry * 0.02
        min_distance_pct = 0.03
        min_distance = entry * min_distance_pct

        raw_sl = entry - (atr_value * 1.5)
        if raw_sl >= entry:
            raw_sl = entry * (1 - min_distance_pct)
            has_inverted_sl = True
        else:
            has_inverted_sl = False

        stop_loss = round(raw_sl, 2)
        take_profit = round(entry + (atr_value * 3), 2)

        # R:R
        risk = entry - stop_loss
        reward = take_profit - entry
        if risk > 0:
            rr_ratio = round(reward / risk, 2)
        else:
            risk = entry * 0.03
            rr_ratio = 3.0
            stop_loss = round(entry * 0.97, 2)
            take_profit = round(entry * 1.09, 2)

        # ========== NEW: Target Yield & Est. Days với ADX Trend Factor ==========
        # Target Yield %: Lợi nhuận kỳ vọng từ Entry tới Take Profit
        target_yield_pct = round((take_profit - entry) / entry * 100, 2) if entry > 0 else 0
        
        # Trend Factor dựa trên ADX (uy tín của xu hướng)
        adx_val = tech["adx"]
        if adx_val > 25:
            trend_factor = 0.8  # Xu hướng mạnh - giá đạt mục tiêu nhanh
        elif adx_val < 20:
            trend_factor = 0.4  # Sideways - giá đi dắt dẻo
        else:
            trend_factor = 0.6  # Trung gian
        
        # Est. Days với Trend Factor
        price_diff = take_profit - entry
        if atr_value > 0 and atr_value < entry:  # Valid ATR in price units
            est_days = price_diff / (atr_value * trend_factor)
        elif atr_value > 0:
            # ATR might be percentage (value >= entry means it's a ratio)
            atr_pct = atr_value / entry if entry > 0 else 0.02
            est_days = price_diff / (atr_value * trend_factor)  # Still use atr_value as base
        else:
            est_days = price_diff / (entry * 0.02 * trend_factor) if entry > 0 else 10
        
        # Clamp: min 1 day, max 30 days
        est_days = min(max(est_days, 1), 30)
        
        # Timeframe Label dựa trên Est. Days (mới)
        if est_days <= 5:
            timeframe_label = "Fast T+"
            timeframe_color = "emerald"
        elif est_days <= 15:
            timeframe_label = "Swing Pick"
            timeframe_color = "sky"
        else:
            timeframe_label = "Position"
            timeframe_color = "amber"
        
        # Profit/Day = Target Yield % / Est. Days
        profit_per_day = round(target_yield_pct / est_days, 2) if est_days > 0 else 0
        
        # DEBUG: Log values for first few symbols
        if not hasattr(analyze_stock, '_call_count'):
            analyze_stock._call_count = 0
        analyze_stock._call_count += 1
        if analyze_stock._call_count <= 5:
            print(f"[DEBUG {symbol}] Entry={entry}, TP={take_profit}, ATR={atr_value}, ADX={adx_val}, Factor={trend_factor}, TargetYield={target_yield_pct}%, EstDays={est_days}, Profit/Day={profit_per_day}")

        # CRITERIA - Calculate BEFORE veto
        criteria = []
        criteria_names = []

        # RSI Sweet Spot
        if 50 <= tech["rsi"] <= 65:
            criteria.append("RSI Sweet Spot")
            criteria_names.append("RSI")
        # ADX Strong
        if tech["adx"] > 20:
            criteria.append("ADX Strong")
            criteria_names.append("ADX")
        # DI Bullish
        if tech["plus_di"] > tech["minus_di"]:
            criteria.append("DI Bullish")
            criteria_names.append("DI+")
        # CMF Positive
        if tech["cmf"] > 0:
            criteria.append("CMF Positive")
            criteria_names.append("CMF")
        # Volume Active
        if tech["volume_ratio"] > 1.0:
            criteria.append("Volume Active")
            criteria_names.append("Vol")
        # Above SMA20
        if tech["sma_20"] > 0 and tech["price"] > tech["sma_20"]:
            criteria.append("Above SMA20")
            criteria_names.append("SMA20")
        # MACD Bullish
        if tech["macd"] > tech["macd_signal"]:
            criteria.append("MACD Bullish")
            criteria_names.append("MACD")
        # R:R Good
        if rr_ratio >= 2.0:
            criteria.append("R:R >= 2.0")
            criteria_names.append("R:R>=2")
        elif rr_ratio >= 1.5:
            criteria.append("R:R >= 1.5")
            criteria_names.append("R:R>=1.5")
        # Fast Holding
        if est_days <= 10:
            criteria.append("Fast Holding")
            criteria_names.append("Fast")
        # VWAP
        if tech["vwap_status"] == "above":
            criteria.append("Above VWAP")
            criteria_names.append("VWAP")
        # Ichimoku Bullish
        if tech["ichimoku_status"] == "bullish":
            criteria.append("Ichimoku Bullish")
            criteria_names.append("Cloud")
        # SuperTrend Bullish
        if tech["supertrend_signal"] == "bullish":
            criteria.append("SuperTrend Bull")
            criteria_names.append("ST")

        criteria_met = len(criteria)

        # VETO CHECK - AFTER criteria calculation
        is_vetoed = False
        veto_reason = ""

        if tech["cmf"] < 0:
            is_vetoed = True
            veto_reason = "CMF Negative"
        elif tech["atr"] <= 0:
            is_vetoed = True
            veto_reason = "ATR = 0"
        elif entry <= 0:
            is_vetoed = True
            veto_reason = "Invalid Price"
        # VETO if F-Score < 3 (low fundamental quality)
        elif fund_data['f_score'] < 3:
            is_vetoed = True
            veto_reason = f"F-Score: {fund_data['f_score']}/9"
        # VETO if Price < SMA50 (downtrend long-term) - NOT override existing veto
        elif tech["sma_50"] > 0 and tech["price"] < tech["sma_50"]:
            is_vetoed = True
            veto_reason = "Below SMA50"

        # SCORES
        tech_score = 50
        fund_score = 50

        if not is_vetoed:
            # RSI
            if 50 <= tech["rsi"] <= 65:
                tech_score += 12 if 55 <= tech["rsi"] <= 62 else 8
            elif tech["rsi"] > 70:
                tech_score -= 15
            elif tech["rsi"] > 65:
                tech_score -= 8
            elif tech["rsi"] < 40:
                tech_score += 5

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

            # VWAP penalty
            if tech["vwap_status"] == "below":
                tech_score -= 8

            # Inverted SL
            if has_inverted_sl:
                tech_score -= 10

            # FAST PICK - Based on Volume Ratio
            if tech["adx"] > 18 and tech["volume_ratio"] > 0.8:
                is_fast_pick = True
            else:
                is_fast_pick = False
        else:
            tech_score = max(25, tech_score - 30)
            is_fast_pick = False

        tech_score = max(0, min(100, tech_score))

        # Fund Score based on F-Score and ROE
        if fund_data['f_score'] >= 7:
            fund_score = 80
        elif fund_data['f_score'] >= 5:
            fund_score = 65
        elif fund_data['f_score'] >= 3:
            fund_score = 50
        else:
            fund_score = 35

        # Adjust by ROE
        if fund_data['roe'] is not None:
            if fund_data['roe'] > 20:
                fund_score = min(100, fund_score + 15)
            elif fund_data['roe'] > 15:
                fund_score = min(100, fund_score + 10)
            elif fund_data['roe'] < 5:
                fund_score = max(0, fund_score - 15)

        # ========== RISK ASSESSMENT - SEPARATED ==========
        # Market Risk (thị trường chung) - VNIndex RSI
        is_market_high_risk = market_rsi > 80
        
        # Stock Risk (rủi ro riêng mã) - Dựa trên khoảng cách từ giá tới Stop Loss
        # Nếu SL cách xa > 5% so với giá -> High Risk
        sl_distance_pct = ((entry - stop_loss) / entry) * 100 if entry > 0 else 0
        
        if sl_distance_pct > 7:
            stock_risk_level = "High"
            stock_risk_reason = f"SL cách xa {sl_distance_pct:.1f}%"
        elif sl_distance_pct > 5:
            stock_risk_level = "Medium"
            stock_risk_reason = f"SL cách xa {sl_distance_pct:.1f}%"
        elif sl_distance_pct > 3:
            stock_risk_level = "Low"
            stock_risk_reason = f"SL cách xa {sl_distance_pct:.1f}%"
        else:
            stock_risk_level = "Very Low"
            stock_risk_reason = f"SL gần {sl_distance_pct:.1f}%"
        
        # Additional risk check: Price below SMA50 = elevated stock risk
        if tech["sma_50"] > 0 and tech["price"] < tech["sma_50"]:
            stock_risk_level = "High"
            stock_risk_reason = "Giá dưới SMA50 (xu hướng dài hạn giảm)"
        
        # Overall High Risk = Market High Risk OR Stock Risk is High
        is_high_risk = stock_risk_level == "High"

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
            # Basic info
            "symbol": symbol,
            "company_name": company_name,
            "price": tech["price"],
            "change_percent": tech["change_percent"],
            "volume": tech["volume"],
            # Technical
            "rsi": tech["rsi"],
            "mfi": tech["mfi"],
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
            # Advanced TA
            "vwap": tech["vwap"],
            "vwap_status": tech["vwap_status"],
            "ichimoku_tenkan": tech["ichimoku_tenkan"],
            "ichimoku_kijun": tech["ichimoku_kijun"],
            "ichimoku_status": tech["ichimoku_status"],
            "supertrend": tech["supertrend"],
            "supertrend_signal": tech["supertrend_signal"],
            # Avg volume value
            "avg_volume_value": round(tech["volume_ratio"] * tech["price"] * df['volume'].tail(20).mean() / 1e9, 1) if 'volume' in df.columns else 0,
            # Trading levels
            "entry_price": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": rr_ratio,
            # NEW: Target Yield & Est. Days
            "target_yield_pct": target_yield_pct,
            "trend_factor": trend_factor,
            "estimated_days_to_target": round(est_days, 1),
            "timeframe_label": timeframe_label,
            "timeframe_color": timeframe_color,
            # Expected metrics (profit/day)
            "expected_profit_per_day": profit_per_day,
            "upside_per_day": profit_per_day,
            # Scores
            "master_score": int(tech_score * 0.55 + fund_score * 0.45),
            "technical_score": tech_score,
            "fundamental_score": fund_score,
            "signal": signal,
            # Status
            "is_vetoed": is_vetoed,
            "veto_reason": veto_reason,
            "is_fast_pick": is_fast_pick,
            "is_short_term_qualified": not is_vetoed and criteria_met >= 9,
            "is_slow_mode": est_days > 10,
            "is_high_risk": is_high_risk,
            "is_market_high_risk": is_market_high_risk,  # NEW
            "stock_risk_level": stock_risk_level,  # NEW: Very Low/Low/Medium/High
            "stock_risk_reason": stock_risk_reason,  # NEW: Lý do cụ thể
            "has_inverted_sl": has_inverted_sl,
            # Criteria (keep even when vetoed)
            "criteria_met": criteria_met,
            "criteria_list": criteria,
            "criteria_names": criteria_names,
            # Trend
            "trend": trend,
            "breakout_status": "BREAKOUT" if is_fast_pick and not is_vetoed else ("VETO" if is_vetoed else "WAIT"),
            # Market
            "market_rsi": market_rsi,
            # Fundamental
            "roe": fund_data['roe'],
            "pe": fund_data['pe'],
            "pb": fund_data['pb'],
            "f_score": fund_data['f_score'],
            "f_score_grade": fund_data['f_score_grade'],
            "profit_growth": fund_data.get('profit_growth'),  # NEW
        }

    except Exception as e:
        print(f"[Sync] Error analyzing {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None


def sync_stock_batch(symbols: List[str], market_rsi: float = 50.0) -> Dict[str, Any]:
    """Đồng bộ một batch mã cổ phiếu"""
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


def sync_market_data(mode: str = "full") -> Dict[str, Any]:
    """Đồng bộ toàn bộ dữ liệu thị trường"""
    start_time = datetime.now()

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

    print(f"[Sync] Starting sync in '{mode}' mode...")

    # Lấy Market RSI
    market_rsi = get_market_rsi()
    print(f"[Sync] Market RSI: {market_rsi:.2f}")

    if mode == "analyze":
        symbols = list(StockData.objects.values_list('symbol', flat=True))
        print(f"[Sync] Analyze mode: Re-analyzing {len(symbols)} existing symbols")
    else:
        symbols = get_top_symbols_by_liquidity()
        print(f"[Sync] Got {len(symbols)} symbols")

    # Process in batches
    batch_size = 20
    all_results = []

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        print(f"[Sync] Processing batch {i//batch_size + 1}: {batch[:5]}...")

        batch_result = sync_stock_batch(batch, market_rsi)
        all_results.extend(batch_result["results"])

        sync_record.processed_symbols = min(i + batch_size, len(symbols))
        sync_record.save()

    # Save to Database
    print(f"[Sync] Saving {len(all_results)} results to database...")
    saved_count = save_results_to_db(all_results)

    # Validation: Top 5 by F-Score
    if all_results:
        valid_fscore = [r for r in all_results if r.get('f_score', 0) > 0]
        if valid_fscore:
            top_fscore = sorted(valid_fscore, key=lambda x: x.get('f_score') or 0, reverse=True)[:5]
            print(f"[Sync] Top 5 by F-Score:")
            for r in top_fscore:
                print(f"  {r['symbol']}: F={r.get('f_score')}, ROE={r.get('roe')}, PE={r.get('pe')}, PB={r.get('pb')}")

        # Top 5 by Volume Ratio (for FAST picks)
        non_vetoed = [r for r in all_results if not r.get('is_vetoed')]
        if non_vetoed:
            top_vol = sorted(non_vetoed, key=lambda x: x.get('volume_ratio') or 0, reverse=True)[:5]
            print(f"[Sync] Top 5 by Volume Ratio:")
            for r in top_vol:
                print(f"  {r['symbol']}: VolRatio={r.get('volume_ratio')}, Score={r.get('master_score')}")

    elapsed = (datetime.now() - start_time).total_seconds()

    sync_record.status = "completed"
    sync_record.completed_at = timezone.now()
    sync_record.save()

    result = {
        "status": "success",
        "mode": mode,
        "total": len(all_results),
        "saved": saved_count,
        "market_rsi": market_rsi,
        "elapsed_seconds": elapsed,
    }

    print(f"[Sync] Completed in {elapsed:.1f}s. Saved {saved_count}/{len(all_results)} results")
    return result


def save_results_to_db(results: List[Dict[str, Any]]) -> int:
    """Lưu kết quả vào Database"""
    saved = 0

    # Get VN30 list
    try:
        from vnstock_data import Reference
        ref = Reference()
        vn30_list = list(ref.equity.list_by_group(group="VN30")['symbol'].str.upper())
    except:
        vn30_list = list(VN30_SYMBOLS)

    for data in results:
        try:
            symbol = data["symbol"]
            industry = data.get("industry", "")
            market_group = "VN30" if symbol in vn30_list else ("MIDCAP" if data.get("avg_volume_value", 0) >= 5 else "SMALL")

            # Save StockData
            stock, _ = StockData.objects.update_or_create(
                symbol=symbol,
                defaults={
                    "company_name": data.get("company_name", symbol),
                    "industry": industry,
                    "market_group": market_group,
                    "price": data["price"],
                    "change_percent": data["change_percent"],
                    "volume": data["volume"],
                    "avg_volume_value": data.get("avg_volume_value", 0),
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
                    # Advanced TA
                    "mfi": data.get("mfi", 50),
                    "vwap": data.get("vwap", 0),
                    "vwap_status": data.get("vwap_status", "neutral"),
                    "ichimoku_tenkan": data.get("ichimoku_tenkan", 0),
                    "ichimoku_kijun": data.get("ichimoku_kijun", 0),
                    "ichimoku_status": data.get("ichimoku_status", "neutral"),
                    "supertrend": data.get("supertrend", 0),
                    "supertrend_signal": data.get("supertrend_signal", "neutral"),
                    # Fundamental
                    "pe": data.get("pe"),
                    "pb": data.get("pb"),
                    "roe": data.get("roe"),
                    "f_score": data.get("f_score", 0),
                    "profit_growth": data.get("profit_growth"),  # NEW
                }
            )

            # Save StockAnalysis
            StockAnalysis.objects.update_or_create(
                symbol=stock,
                defaults={
                    "master_score": data["master_score"],
                    "base_master_score": data.get("base_master_score", data["master_score"]),
                    "market_weight": data.get("market_weight", 0),
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
                    "is_market_high_risk": data.get("is_market_high_risk", False),  # NEW
                    "stock_risk_level": data.get("stock_risk_level", "Medium"),  # NEW
                    "has_inverted_sl": data["has_inverted_sl"],
                    "estimated_days_to_target": data["estimated_days_to_target"],
                    "timeframe_label": data.get("timeframe_label", ""),
                    "timeframe_color": data.get("timeframe_color", ""),
                    "expected_profit_per_day": data.get("expected_profit_per_day", 0),
                    "upside_per_day": data.get("upside_per_day", 0),
                    "target_yield_pct": data.get("target_yield_pct", 0),
                    "criteria_met": data["criteria_met"],
                    "criteria_list": data["criteria_list"],
                    "trend": data["trend"],
                    "breakout_status": data["breakout_status"],
                    "market_rsi": data["market_rsi"],
                }
            )
            saved += 1

        except Exception as e:
            print(f"[Sync] Error saving {data.get('symbol')}: {e}")

    return saved


def get_top_picks_from_db(limit: int = 5) -> List[Dict[str, Any]]:
    """Lấy top picks từ Database - SORTED by Profit/Day for best efficiency"""
    from django.db.models import F, ExpressionWrapper, FloatField

    # Get non-vetoed stocks, calculate profit_per_day and sort by it
    # Profit/Day = (take_profit - entry_price) / estimated_days_to_target / entry_price * 100
    analyses = StockAnalysis.objects.select_related("symbol").filter(
        is_vetoed=False,
        estimated_days_to_target__gt=0
    ).annotate(
        profit_per_day_calc=ExpressionWrapper(
            F('take_profit') - F('entry_price'),
            output_field=FloatField()
        )
    ).order_by(
        '-profit_per_day_calc',
        '-master_score'
    )[:limit]

    picks = []
    for a in analyses:
        s = a.symbol
        # Use target_yield_pct from DB if available, otherwise calculate
        target_yield_pct = a.target_yield_pct if a.target_yield_pct else round((a.take_profit - (a.entry_price or s.price)) / (a.entry_price or s.price) * 100, 2) if a.take_profit and (a.entry_price or s.price) > 0 else 0
        days = a.estimated_days_to_target or 1
        profit_per_day = round(target_yield_pct / days, 2) if days > 0 else 0
        
        picks.append({
            "symbol": s.symbol,
            "company_name": s.company_name,
            "price": s.price,
            "change_percent": s.change_percent,
            # Target Yield
            "target_yield_pct": target_yield_pct,
            "profit_per_day": profit_per_day,
            # Technical
            "rsi": s.rsi,
            "adx": s.adx,
            "volume_ratio": s.volume_ratio,
            "cmf": s.cmf,
            "atr": s.atr,
            # Scores
            "master_score": a.master_score,
            "technical_score": a.technical_score,
            "fundamental_score": a.fundamental_score,
            "signal": a.signal,
            "risk_reward_ratio": a.risk_reward_ratio,
            "is_fast_pick": a.is_fast_pick,
            "criteria_met": a.criteria_met,
            "criteria_list": a.criteria_list,
            "trend": a.trend,
            "breakout_status": a.breakout_status,
            # Trading Levels
            "entry_price": a.entry_price,
            "stop_loss": a.stop_loss,
            "take_profit": a.take_profit,
            "estimated_days_to_target": a.estimated_days_to_target,
            "timeframe_label": a.timeframe_label,
            "timeframe_color": a.timeframe_color,
            # Risk
            "is_high_risk": a.is_high_risk,
            "is_market_high_risk": getattr(a, 'is_market_high_risk', False),
            "stock_risk_level": getattr(a, 'stock_risk_level', 'Medium'),
            # Meta
            "market_rsi": a.market_rsi,
            "profit_growth": getattr(s, 'profit_growth', None),
            # Extra for criteria check
            "plus_di": s.plus_di,
            "minus_di": s.minus_di,
            "macd": s.macd,
            "macd_signal": s.macd_signal,
            "sma_20": s.sma_20,
        })

    return picks


def get_sync_status() -> Optional[Dict[str, Any]]:
    """Lấy trạng thái sync cuối cùng"""
    try:
        sync = SyncStatus.objects.get(id=1)
        return {
            "status": sync.status,
            "is_running": sync.is_running,
            "progress_percent": sync.progress_percent,
            "total_symbols": sync.total_symbols,
            "processed_symbols": sync.processed_symbols,
            "started_at": str(sync.started_at) if sync.started_at else None,
            "completed_at": str(sync.completed_at) if sync.completed_at else None,
            "error_message": sync.error_message,
        }
    except:
        return None
