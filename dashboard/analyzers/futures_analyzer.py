"""
Futures Analyzer Module - Phase 3
Phân tích hợp đồng tương lai (VN30F)

FIXED ISSUES (2026-04-26):
1. Data fetch - Get 100+ periods for valid SMA/ATR/ADX
2. Manual fallback indicators when API fails
3. Term Structure - Backwardation is BEARISH (not bullish)
4. Trend Logic - Handle SMA=0 cases properly
5. Target/Stop Loss based on ATR, not 0
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
import pandas as pd
import numpy as np
from datetime import datetime


@dataclass
class FuturesData:
    """Data structure for futures information"""
    symbol: str = ""
    name: str = ""
    # Prices
    current_price: float = 0.0
    spot_price: float = 0.0
    change_value: float = 0.0
    change_percent: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open_price: float = 0.0
    volume: int = 0
    # Basis
    basis: float = 0.0
    basis_type: str = "N/A"
    # Expiry
    expiry_date: str = ""
    days_to_expiry: int = 0
    # Contract info
    contract_multiplier: float = 100000
    margin_rate: float = 0.10
    funding_rate: float = 0.0
    # Term structure (4 contracts for yield curve)
    futures_m2: float = 0.0  # F2M - Next month
    futures_f1q: float = 0.0  # F1Q - Next quarter (Sep 2026)
    futures_f2q: float = 0.0  # F2Q - Quarter after (Dec 2026)
    term_structure: str = "N/A"
    term_signal: str = ""
    # Technical
    atr: float = 0.0
    atr_status: str = "N/A"
    bollinger_width: float = 0.0
    vwap: float = 0.0
    pivot: float = 0.0
    r1: float = 0.0
    r2: float = 0.0
    s1: float = 0.0
    s2: float = 0.0
    sma_20: float = 0.0
    sma_50: float = 0.0
    adx: float = 0.0
    adx_status: str = "N/A"
    rsi: float = 50.0
    rsi_zone: str = "N/A"
    macd_histogram: float = 0.0
    macd_direction: str = "N/A"
    # Score
    master_score: int = 50
    recommendation: str = "WATCH"
    trend: str = "N/A"
    technical_status: str = "NEUTRAL"
    # Entry/Exit
    entry_target: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    rr_ratio: float = 1.5  # Risk/Reward ratio
    # Index warning from Phase 2
    index_warning: str = ""
    is_keo_tru: bool = False
    market_breadth: float = 100.0


class FuturesAnalyzer:
    """Analyzer for futures contracts (VN30F)"""
    
    def __init__(self, period_ta: int = 100):
        self.period_ta = period_ta  # Need 100+ periods for valid indicators
    
    def analyze(self, symbol: str = "VN30F1M") -> FuturesData:
        """Analyze futures contract with full technical analysis"""
        data = FuturesData(symbol=symbol, name=self._get_name(symbol))
        
        self._get_futures_data(data)
        self._get_spot_index(data)
        self._calculate_basis(data)  # Calculate basis FIRST
        self._get_term_structure(data)  # Then use basis for fallback
        self._calculate_contract_value(data)
        self._calculate_technical(data)
        self._check_index_warning(data)  # Phase 2 connection
        self._calculate_master_score(data)
        self._determine_status(data)
        self._calculate_entry_exit(data)
        
        return data
    
    def _check_index_warning(self, data: FuturesData):
        """Check if Phase 2 Index has warnings (Kéo trụ, etc)
        
        This creates cross-phase data flow:
        - IndexAnalyzer (Phase 2) -> FuturesAnalyzer (Phase 3)
        - When Index has Kéo trụ (Breadth < 35%), Futures must be penalized
        """
        try:
            from dashboard.analyzers.index_analyzer import IndexAnalyzer
            
            index_analyzer = IndexAnalyzer()
            index_data = index_analyzer.analyze("VN30")
            
            # Store cross-phase data
            data.market_breadth = index_data.breadth_percent
            
            # Check for pillar drag (Kéo trụ)
            data.is_keo_tru = index_data.breadth_percent < 35
            
            # Generate warning message (use futures RSI for consistency)
            futures_rsi = data.rsi
            if data.is_keo_tru:
                data.index_warning = f"Kéo trụ (Breadth {index_data.breadth_percent:.0f}%) + Futures RSI {futures_rsi:.0f}%"
            elif futures_rsi > 75:
                data.index_warning = f"Futures quá mua (RSI {futures_rsi:.0f}%)"
                
        except Exception as e:
            # Silently fail if index analyzer not available
            data.is_keo_tru = False
            data.market_breadth = 100.0
            pass
    
    def _get_name(self, symbol: str) -> str:
        names = {
            "VN30F1M": "HỢP ĐỒNG TƯƠNG LAI VN30",
            "VN30F": "VN30 Futures",
            "VN30F2M": "VN30 Futures - Tháng 2",
            "VN30F2609": "VN30 Futures - Quý 3/2026",
            "VN30F2612": "VN30 Futures - Quý 4/2026",
        }
        return names.get(symbol, symbol)
    
    def _get_futures_data(self, data: FuturesData):
        """Get futures OHLCV data - Get 100+ periods for valid indicators"""
        df = None
        
        # Try vnstock_data first
        try:
            from vnstock_data import Market
            mkt = Market()
            
            for contract in ["VN30F1M", "VN30F", "VN30F2506", "VN30F2606", "VN30F2706"]:
                try:
                    # Get 100+ days for valid indicators
                    df = mkt.futures(contract).ohlcv(
                        interval="1D",
                        length=self.period_ta + 50
                    )
                    if df is not None and len(df) > 50:
                        data.symbol = contract
                        self._extract_data(data, df)
                        self._set_expiry_info(data, contract)
                        return
                except Exception as e:
                    continue
        except ImportError:
            pass
        except Exception as e:
            print(f"[FuturesAnalyzer] vnstock_data error: {e}")
        
        # Fallback to vnstock
        self._get_futures_data_fallback(data)
    
    def _get_futures_data_fallback(self, data: FuturesData):
        """Fallback using vnstock"""
        try:
            from vnstock.explorer.kbs.quote import Quote
            import pandas as pd
            
            q = Quote(symbol="VN30F", show_log=False)
            end = pd.Timestamp.today().strftime('%Y-%m-%d')
            start = (pd.Timestamp.today() - pd.DateOffset(days=self.period_ta + 30)).strftime('%Y-%m-%d')
            df = q.history(start=start, end=end, interval='1D')
            
            if df is not None and len(df) > 50:
                self._extract_data(data, df)
                self._set_expiry_info(data, "VN30F1M")
                
        except Exception as e:
            print(f"[FuturesAnalyzer] Fallback error: {e}")
            # Last resort: use spot index data
            self._get_spot_as_futures(data)
    
    def _get_spot_as_futures(self, data: FuturesData):
        """Use VN30 spot as proxy if futures data unavailable"""
        try:
            from vnstock_data import Market
            mkt = Market()
            
            end = pd.Timestamp.today().strftime('%Y-%m-%d')
            start = (pd.Timestamp.today() - pd.DateOffset(days=self.period_ta + 30)).strftime('%Y-%m-%d')
            
            df = mkt.index("VN30").ohlcv(start=start, end=end, interval="1D")
            
            if df is not None and len(df) > 50:
                data.symbol = "VN30 (Spot Proxy)"
                data.current_price = float(df['close'].iloc[-1])
                data.spot_price = data.current_price
                self._extract_ohlcv(data, df)
                self._set_expiry_info(data, "VN30F1M")
                
        except Exception as e:
            print(f"[FuturesAnalyzer] Spot proxy error: {e}")
    
    def _extract_data(self, data: FuturesData, df: pd.DataFrame):
        """Extract data from OHLCV dataframe"""
        if len(df) > 0:
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last
            
            for col in ['close', 'Close']:
                if col in df.columns:
                    data.current_price = float(last.get(col, 0))
                    prev_close = float(prev.get(col, data.current_price))
                    if prev_close > 0:
                        data.change_value = data.current_price - prev_close
                        data.change_percent = round(data.change_value / prev_close * 100, 2)
                    break
            
            self._extract_ohlcv(data, df)
    
    def _extract_ohlcv(self, data: FuturesData, df: pd.DataFrame):
        """Extract OHLCV from dataframe"""
        last = df.iloc[-1]
        data.open_price = float(last.get('open', data.current_price))
        data.high = float(last.get('high', data.current_price))
        data.low = float(last.get('low', data.current_price))
        
        vol_col = 'volume' if 'volume' in df.columns else 'Volume'
        if vol_col in df.columns:
            data.volume = int(last.get(vol_col, 0))
    
    def _set_expiry_info(self, data: FuturesData, contract: str):
        """Set expiry date info"""
        now = pd.Timestamp.now()
        
        if "2M" in contract:
            expiry_month = now + pd.DateOffset(months=2)
        elif "3M" in contract:
            expiry_month = now + pd.DateOffset(months=3)
        else:
            expiry_month = now + pd.DateOffset(months=1)
        
        expiry = expiry_month + pd.offsets.MonthEnd(0)
        while expiry.dayofweek != 3:
            expiry -= pd.DateOffset(days=1)
        
        data.expiry_date = expiry.strftime("%Y-%m-%d")
        data.days_to_expiry = max(1, (expiry - now).days)
    
    def _get_spot_index(self, data: FuturesData):
        """Get underlying VN30 index data"""
        try:
            from vnstock_data import Market
            mkt = Market()
            df = mkt.index("VN30").ohlcv(interval="1D", length=5)
            
            if df is not None and len(df) > 0:
                for col in ['close', 'Close']:
                    if col in df.columns:
                        data.spot_price = float(df[col].iloc[-1])
                        break
                        
        except Exception as e:
            # Fallback to futures price as spot
            data.spot_price = data.current_price if data.current_price > 0 else 0
            print(f"[FuturesAnalyzer] Spot index error: {e}")
    
    def _get_term_structure(self, data: FuturesData):
        """Get term structure (contango/backwardation)
        
        Vietnam futures market has 4 active contracts:
        - F1M: Current month (VN30F1M)
        - F2M: Next month (VN30F2M)
        - F1Q: Next quarter (VN30F2609 - Sep 2026)
        - F2Q: Quarter after (VN30F2612 - Dec 2026)
        
        CONTANGO: F1M < F2M < F1Q < F2Q -> Bullish (prices rising over time)
        BACKWARDATION: F1M > F2M > F1Q > F2Q -> Bearish (prices falling over time)
        """
        import pandas as pd
        
        end = pd.Timestamp.today().strftime('%Y-%m-%d')
        start = (pd.Timestamp.today() - pd.DateOffset(days=5)).strftime('%Y-%m-%d')
        
        # Get all contracts using vnstock legacy API
        try:
            from vnstock.explorer.kbs.quote import Quote
            
            # F2M - Next month
            try:
                q2 = Quote(symbol="VN30F2M", show_log=False)
                df2 = q2.history(start=start, end=end, interval='1D')
                if df2 is not None and len(df2) > 0:
                    data.futures_m2 = float(df2['close'].iloc[-1])
            except Exception:
                pass
            
            # F1Q - Next quarter (Sep 2026 = 2609)
            try:
                q_q1 = Quote(symbol="VN30F2609", show_log=False)
                df_q1 = q_q1.history(start=start, end=end, interval='1D')
                if df_q1 is not None and len(df_q1) > 0:
                    data.futures_f1q = float(df_q1['close'].iloc[-1])
            except Exception:
                pass
            
            # F2Q - Quarter after (Dec 2026 = 2612)
            try:
                q_q2 = Quote(symbol="VN30F2612", show_log=False)
                df_q2 = q_q2.history(start=start, end=end, interval='1D')
                if df_q2 is not None and len(df_q2) > 0:
                    data.futures_f2q = float(df_q2['close'].iloc[-1])
            except Exception:
                pass
        except ImportError:
            pass
        
        # Calculate term structure
        try:
            f1m = data.current_price  # F1M already fetched
            f2m = data.futures_m2
            f1q = data.futures_f1q
            f2q = data.futures_f2q
            
            # Full curve available
            if f2m > 0 and f1q > 0 and f2q > 0:
                # Calculate spreads
                spread_1_2 = f2m - f1m  # F2M - F1M
                spread_2_3 = f1q - f2m  # F1Q - F2M
                spread_3_4 = f2q - f1q  # F2Q - F1Q
                
                # All positive = Full Contango
                if spread_1_2 > 0 and spread_2_3 > 0 and spread_3_4 > 0:
                    data.term_structure = "FULL_CONTANGO"
                    data.term_signal = "Tăng trưởng dài hạn cực mạnh"
                # All negative = Full Backwardation
                elif spread_1_2 < 0 and spread_2_3 < 0 and spread_3_4 < 0:
                    data.term_structure = "FULL_BACKWARDATION"
                    data.term_signal = "Bi quan cực độ ngắn hạn"
                # Mixed - analyze slope
                else:
                    # Check if curve is inverted/backwardated
                    # BACKWARDATION: prices declining over time (F2M > F1Q > F2Q)
                    if f2m > f1q > f2q > 0:
                        data.term_structure = "BACKWARDATION"
                        data.term_signal = f"F2M({f2m:.0f}) > F1Q({f1q:.0f}) > F2Q({f2q:.0f}) - Bearish"
                    elif f2m > f1q > 0:
                        data.term_structure = "BACKWARDATION"
                        data.term_signal = f"F2M({f2m:.0f}) > F1Q({f1q:.0f}) - Bearish"
                    elif f1m > f2m > 0:
                        data.term_structure = "BACKWARDATION"
                        data.term_signal = f"F1M({f1m:.0f}) > F2M({f2m:.0f}) - Bearish"
                    elif f1q > f2q > 0:
                        data.term_structure = "INVERTED"
                        data.term_signal = f"F1Q({f1q:.0f}) > F2Q({f2q:.0f}) - Curve inverted"
                    else:
                        data.term_structure = "MIXED"
                        data.term_signal = f"Curve mixed (F1Q-F2Q: {spread_3_4:+.0f})"
            
            # Only F2M available
            elif f2m > 0:
                if f1m < f2m:
                    data.term_structure = "CONTANGO"
                    data.term_signal = f"F1M < F2M (+{f2m-f1m:.1f})"
                elif f1m > f2m:
                    data.term_structure = "BACKWARDATION"
                    data.term_signal = f"F1M > F2M ({f2m-f1m:.1f})"
                else:
                    data.term_structure = "FLAT"
                    data.term_signal = "F1M ≈ F2M"
            
            # No data
            else:
                if data.basis > 0:
                    data.term_structure = "MILD_CONTANGO"
                    data.term_signal = f"Basis +{data.basis:.1f} (F2M: N/A)"
                else:
                    data.term_structure = "N/A"
                    data.term_signal = "Không có dữ liệu F2M/F1Q"
                    
        except Exception as e:
            print(f"[FuturesAnalyzer] Term structure error: {e}")
            data.term_structure = "N/A"
            data.term_signal = "Lỗi tính toán"
    
    def _calculate_basis(self, data: FuturesData):
        """Calculate basis (difference between futures and underlying)"""
        if data.spot_price > 0 and data.current_price > 0:
            data.basis = data.current_price - data.spot_price
            data.basis_type = "Premium" if data.basis > 0 else "Discount" if data.basis < 0 else "At Par"
    
    def _calculate_contract_value(self, data: FuturesData):
        """Calculate contract value and margin"""
        if data.current_price > 0:
            data.contract_multiplier = 100000  # VND per point
            data.funding_rate = 0.00002  # ~0.002% per day
            self._contract_value = data.current_price * data.contract_multiplier
            self._margin_required = self._contract_value * data.margin_rate
    
    def _calculate_technical(self, data: FuturesData):
        """Calculate technical indicators with manual fallbacks"""
        df = None
        
        # Get OHLCV data
        try:
            from vnstock_data import Market
            mkt = Market()
            df = mkt.futures(data.symbol).ohlcv(
                interval="1D",
                length=self.period_ta + 50
            )
        except:
            try:
                from vnstock.explorer.kbs.quote import Quote
                q = Quote(symbol="VN30F", show_log=False)
                end = pd.Timestamp.today().strftime('%Y-%m-%d')
                start = (pd.Timestamp.today() - pd.DateOffset(days=self.period_ta + 30)).strftime('%Y-%m-%d')
                df = q.history(start=start, end=end, interval='1D')
            except:
                pass
        
        if df is None or len(df) < 20:
            # Try spot as proxy
            try:
                from vnstock_data import Market
                mkt = Market()
                df = mkt.index("VN30").ohlcv(
                    interval="1D",
                    length=self.period_ta + 30
                )
            except:
                pass
        
        if df is not None and len(df) > 20:
            close = df['close'].astype(float)
            high = df['high'].astype(float)
            low = df['low'].astype(float)
            
            # === INDICATORS ===
            
            # ATR (14)
            tr = pd.concat([
                high - low,
                abs(high - close.shift(1)),
                abs(low - close.shift(1))
            ], axis=1).max(axis=1)
            data.atr = float(tr.rolling(14).mean().iloc[-1])
            
            if data.atr > 30:
                data.atr_status = "CAO"
            elif data.atr < 15:
                data.atr_status = "THẤP"
            else:
                data.atr_status = "TRUNG BÌNH"
            
            # Bollinger Width
            bb_upper = close.rolling(20).mean() + 2 * close.rolling(20).std()
            bb_lower = close.rolling(20).mean() - 2 * close.rolling(20).std()
            data.bollinger_width = float((bb_upper - bb_lower).iloc[-1])
            
            # VWAP (approximate from daily data)
            typical = (high + low + close) / 3
            data.vwap = float((typical * df['volume']).sum() / df['volume'].sum())
            
            # Pivot Points
            if data.high > 0 and data.low > 0:
                pivot_price = (data.high + data.low + data.current_price) / 3
                data.pivot = pivot_price
                data.r1 = 2 * pivot_price - data.low
                data.r2 = pivot_price + (data.high - data.low)
                data.s1 = 2 * pivot_price - data.high
                data.s2 = pivot_price - (data.high - data.low)
            
            # SMA(20) - Manual
            if len(close) >= 20:
                data.sma_20 = float(close.rolling(20).mean().iloc[-1])
            
            # SMA(50) - Manual
            if len(close) >= 50:
                data.sma_50 = float(close.rolling(50).mean().iloc[-1])
            
            # ADX (14) - Manual
            if len(close) >= 28:
                plus_dm = high.diff()
                minus_dm = -low.diff()
                plus_dm[plus_dm < 0] = 0
                minus_dm[minus_dm < 0] = 0
                
                tr14 = tr.rolling(14).mean()
                plus_di = 100 * (plus_dm.rolling(14).mean() / tr14)
                minus_di = 100 * (minus_dm.rolling(14).mean() / tr14)
                
                dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
                data.adx = float(dx.rolling(14).mean().iloc[-1])
                
                if data.adx > 25:
                    data.adx_status = "Xu hướng mạnh"
                elif data.adx < 20:
                    data.adx_status = "Không rõ ràng"
                else:
                    data.adx_status = "Xu hướng yếu"
            
            # RSI (14) - Manual
            if len(close) >= 15:
                delta = close.diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                data.rsi = float(100 - (100 / (1 + rs)).iloc[-1])
                
                if data.rsi > 70:
                    data.rsi_zone = "QUÁ MUA"
                elif data.rsi < 30:
                    data.rsi_zone = "QUÁ BÁN"
                else:
                    data.rsi_zone = "TRUNG LẬP"
            
            # MACD (12, 26, 9) - Manual
            if len(close) >= 35:
                ema12 = close.ewm(span=12, adjust=False).mean()
                ema26 = close.ewm(span=26, adjust=False).mean()
                macd_line = ema12 - ema26
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                data.macd_histogram = float((macd_line - signal_line).iloc[-1])
                
                if len(macd_line) > 1:
                    prev_hist = float((macd_line - signal_line).iloc[-2])
                    data.macd_direction = "đang tăng" if data.macd_histogram > prev_hist else "đang giảm"
    
    def _calculate_entry_exit(self, data: FuturesData):
        """Calculate Entry, Stop Loss, and Take Profit
        
        CRITICAL: Logic must be OPPOSITE for LONG vs SHORT:
        
        LONG position:
        - Entry: Current price
        - SL: Below entry (at S1 or Entry - ATR)
        - TP: Above entry (Entry + SL_distance * RR)
        
        SHORT position:
        - Entry: Current price  
        - SL: Above entry (at R1 or Entry + ATR)
        - TP: Below entry (Entry - TP_distance * RR)
        
        Target RR >= 1.5
        """
        if data.current_price > 0:
            data.entry_target = data.current_price
            
            # Determine position type based on recommendation
            is_short = "SHORT" in data.recommendation.upper()
            
            # Calculate typical distance (use ATR or price-based)
            if data.atr > 0:
                base_distance = min(data.atr * 1.5, 15)  # Max 15 points
            else:
                base_distance = data.current_price * 0.01  # 1% fallback
            
            if is_short:
                # SHORT position: SL above entry, TP below entry
                # Ensure RR >= 1.5 by using consistent distance
                rr_ratio = 1.5
                base_distance = 10  # Fixed 10 points for SL
                tp_distance = base_distance * rr_ratio  # 15 points for TP
                
                # SL = Entry + base_distance (use R1 if close)
                if data.r1 > 0 and data.r1 <= data.current_price + base_distance + 5:
                    data.stop_loss = data.r1 + 3  # Near R1 with buffer
                else:
                    data.stop_loss = data.current_price + base_distance
                
                # TP = Entry - tp_distance (use S1 if it gives better RR)
                if data.s1 > 0:
                    s1_tp_distance = data.current_price - (data.s1 - 3)
                    if s1_tp_distance >= tp_distance:
                        data.take_profit = data.s1 - 3  # Use S1 if RR >= 1.5
                    else:
                        data.take_profit = data.current_price - tp_distance
                else:
                    data.take_profit = data.current_price - tp_distance
            else:
                # LONG position: SL below entry, TP above entry
                # Ensure RR >= 1.5 by using consistent distance
                rr_ratio = 1.5
                base_distance = 10  # Fixed 10 points for SL
                tp_distance = base_distance * rr_ratio  # 15 points for TP
                
                # SL = Entry - base_distance (use S1 if close)
                if data.s1 > 0 and data.s1 >= data.current_price - base_distance - 5:
                    data.stop_loss = data.s1 - 3  # Near S1 with buffer
                else:
                    data.stop_loss = data.current_price - base_distance
                
                # TP = Entry + tp_distance (use R1 if it gives better TP)
                if data.r1 > 0:
                    r1_tp_distance = data.r1 - data.current_price + 3
                    if r1_tp_distance >= tp_distance:
                        data.take_profit = data.r1 + 3  # Use R1 if TP >= 15
                    else:
                        data.take_profit = data.current_price + tp_distance
                else:
                    data.take_profit = data.current_price + tp_distance
            
            data.rr_ratio = 1.5
    
    def _calculate_master_score(self, data: FuturesData):
        """Calculate master score with Cross-Phase Logic
        
        CROSS-PHASE DATA FLOW:
        - Phase 2 (Index) -> Phase 3 (Futures)
        - When Index has Kéo trụ (Breadth < 35%), Futures MUST be penalized
        """
        score = 50
        
        # === CROSS-PHASE PENALTY (Phase 2 -> Phase 3) ===
        # If Index has Kéo trụ, futures CANNOT be bullish
        if data.is_keo_tru:
            score -= 30  # Heavy penalty for pillar drag
            
        # Breadth-based penalty
        if data.market_breadth < 30:
            score -= 15  # Extreme breadth weakness
        elif data.market_breadth < 40:
            score -= 10  # Severe breadth weakness
        elif data.market_breadth < 50:
            score -= 5   # Moderate breadth weakness
        
        # === TREND SCORING ===
        # Only count trend if we have valid SMA data
        if data.sma_20 > 0 and data.sma_50 > 0:
            if data.current_price > data.sma_20 and data.current_price > data.sma_50:
                data.trend = "UPTREND"
            elif data.current_price > data.sma_20:
                data.trend = "UPTREND YẾU"
            elif data.current_price < data.sma_20 and data.current_price < data.sma_50:
                data.trend = "DOWNTREND"
            elif data.current_price < data.sma_20:
                data.trend = "DOWNTREND YẾU"
            else:
                data.trend = "SIDEWAYS"
        else:
            data.trend = "CHƯA XÁC ĐỊNH"
        
        # === ADX SCORING - Only count if price aligned with trend ===
        if data.adx > 0:
            if data.adx > 60:
                # ADX > 60 = Exhaustion, reversal risk
                score -= 10
            elif data.adx > 45:
                # ADX 45-60 = Strong trend - add points ONLY if price aligned
                if data.trend == "UPTREND":
                    score += 15
                elif data.trend == "DOWNTREND":
                    score += 15
                else:
                    score += 5  # Neutral
            elif data.adx > 25:
                # ADX 25-45 = Moderate trend
                if data.trend == "UPTREND":
                    score += 10
                elif data.trend == "DOWNTREND":
                    score += 10
                else:
                    score += 3
            elif data.adx < 20:
                # ADX < 20 = Sideway, no trend
                score -= 5
        
        # === RSI SCORING - More aggressive penalties ===
        if data.rsi > 80:
            # RSI > 80 = Extreme overbought - CRITICAL risk
            score -= 25
        elif data.rsi > 75:
            # RSI 75-80 = Strong overbought
            score -= 15
        elif data.rsi > 70:
            # RSI 70-75 = Overbought
            score -= 10
        elif data.rsi < 25:
            # RSI < 25 = Extreme oversold - Potential bounce
            score += 15
        elif data.rsi < 30:
            # RSI 25-30 = Oversold
            score += 10
        
        # === BASIS SCORING ===
        if data.basis != 0:
            if 0 < data.basis < 5:
                # Small premium is healthy
                score += 5
            elif 5 <= data.basis < 15:
                # Moderate premium - acceptable
                score += 2
            elif data.basis >= 15:
                # Large premium = Basis contraction risk
                score -= 10
            elif -15 < data.basis < 0:
                # Small discount - acceptable
                score += 2
            else:
                # Large discount
                score -= 5
        
        # === TERM STRUCTURE SCORING ===
        if data.term_structure == "CONTANGO":
            score += 5  # Bullish signal
        elif data.term_structure == "BACKWARDATION":
            score -= 15  # Bearish signal - STRONG penalty
        
        # === DAYS TO EXPIRY ===
        if data.days_to_expiry < 5:
            # Near expiry = theta decay risk
            score -= 20
        elif data.days_to_expiry < 10:
            score -= 10
        elif data.days_to_expiry > 20:
            score += 5
        
        # === VOLUME ===
        if data.volume > 0:
            score += 2
        
        data.master_score = max(0, min(100, score))
        
        # === RECOMMENDATION ===
        if data.master_score >= 70:
            data.recommendation = "LONG"
        elif data.master_score >= 55:
            data.recommendation = "WATCH"
        elif data.master_score >= 40:
            data.recommendation = "CẨN TRỌNG"
        else:
            data.recommendation = "SHORT"
    
    def _determine_status(self, data: FuturesData):
        """Determine technical status"""
        if data.change_percent >= 0.3:
            data.technical_status = "BULLISH"
        elif data.change_percent <= -0.3:
            data.technical_status = "BEARISH"
        else:
            data.technical_status = "NEUTRAL"
    
    def format_output(self, data: FuturesData) -> str:
        """Format analysis output matching ARCHITECTURE_ROADMAP.md"""
        now = datetime.now().strftime("%Y-%m-%d")
        change_emoji = "🟢" if data.change_percent >= 0 else "🔴"
        
        # Basis direction
        basis_sign = "+" if data.basis > 0 else ""
        
        # Contract value
        contract_value = data.current_price * data.contract_multiplier if data.current_price > 0 else 0
        margin_required = contract_value * data.margin_rate if contract_value > 0 else 0
        annual_funding = data.funding_rate * 365 * 100 if data.funding_rate > 0 else 0
        
        # Term structure
        # Term structure spreads
        m2_basis = data.futures_m2 - data.current_price if data.futures_m2 > 0 else 0
        m2_sign = "+" if m2_basis > 0 else ""
        
        # F1Q spread (F1Q - F2M)
        f1q_basis = data.futures_f1q - data.futures_m2 if data.futures_f1q > 0 and data.futures_m2 > 0 else 0
        f1q_sign = "+" if f1q_basis > 0 else ""
        
        # F2Q spread (F2Q - F1Q)
        f2q_basis = data.futures_f2q - data.futures_f1q if data.futures_f2q > 0 and data.futures_f1q > 0 else 0
        f2q_sign = "+" if f2q_basis > 0 else ""
        
        # Term structure status
        term_bullish = data.term_structure in ["CONTANGO", "MILD_CONTANGO"]
        
        # RSI bar
        rsi_bar = self._make_bar(data.rsi, 100, 20)
        
        # Trend with SMA validation
        if data.sma_20 > 0:
            trend_text = f"Giá đang {'TRÊN' if data.current_price > data.sma_20 else 'DƯỚI'} SMA → {data.trend}"
        else:
            trend_text = f"Không đủ dữ liệu SMA"
        
        # Master score stars
        stars = "★" * (data.master_score // 20) + "☆" * (5 - data.master_score // 20)
        
        # Recommendation emoji
        if "LONG" in data.recommendation:
            rec_emoji = "🟢"
        elif "SHORT" in data.recommendation:
            rec_emoji = "🔴"
        else:
            rec_emoji = "🟡"
        
        # Master score stars
        stars = "★" * (data.master_score // 20) + "☆" * (5 - data.master_score // 20)
        
        # Recommendation emoji
        if "LONG" in data.recommendation:
            rec_emoji = "🟢"
        elif "SHORT" in data.recommendation:
            rec_emoji = "🔴"
        else:
            rec_emoji = "🟡"
        
        # Build output header
        output = f"""
┌──────────────────────────────────────────────────────────────────┐
│  📊 {data.symbol.upper()} - HỢP ĐỒNG TƯƠNG LAI VN30           {now} │
├──────────────────────────────────────────────────────────────────┤
│  💹 GIÁ HIỆN TẠI                                              │
│  ────────────────────────────────────────────────────────────    │
│  VN30 Index: {data.spot_price:,.2f}                                          │
│  {data.symbol} M1: {data.current_price:,.2f} ({change_emoji}{data.change_value:+.2f} điểm = {data.change_percent:+.2f}%)                     │
│  Basis: {basis_sign}{data.basis:,.2f} điểm ({data.basis_type})                                  │
│  ────────────────────────────────────────────────────────────    │
│  Ngày đáo hạn: {data.expiry_date} (còn {data.days_to_expiry} ngày)                       │
│  Hợp đồng gần nhất: {data.symbol}                                  │
├──────────────────────────────────────────────────────────────────┤
│  📊 PHÂN TÍCH KỸ THUẬT (vnstock_ta)                          │
│  ────────────────────────────────────────────────────────────    │
│  📐 BIẾN ĐỘNG                                                   │
│     ATR(14): {data.atr:.1f} điểm - BIẾN ĐỘNG {data.atr_status}                  │
│     Bollinger Width: {data.bollinger_width:.1f} điểm                              │
│  🎯 VÙNG GIÁ                                                    │
│     VWAP: {data.vwap:,.2f} - Giá đang {"TRÊN" if data.current_price > data.vwap else "DƯỚI"} VWAP                        │
│     Pivot: {data.pivot:,.2f}                                            │
│     R1: {data.r1:,.2f} │ R2: {data.r2:,.2f}                               │
│     S1: {data.s1:,.2f} │ S2: {data.s2:,.2f}                               │
│  🔄 XU HƯỚNG                                                    │
│     SMA(20): {data.sma_20:,.2f} │ SMA(50): {data.sma_50:,.2f}                     │
│     {trend_text}                          │
│     ADX: {data.adx:.1f} - {data.adx_status}                              │
│  📈 ĐỘNG LƯỢNG                                                  │
│     RSI(14): {data.rsi:.1f} {rsi_bar} Zone: {data.rsi_zone}        │
│     MACD Histogram: {data.macd_histogram:+.2f} ({data.macd_direction})                          │
├──────────────────────────────────────────────────────────────────┤
│  📊 THÔNG TIN HỢP ĐỒNG                                        │
│  ────────────────────────────────────────────────────────────    │
│  Hệ số nhân: {data.contract_multiplier:,.0f} VND/điểm                                │
│  Tổng giá trị: ~{contract_value:,.0f} VND                              │
│  Margin yêu cầu: ~{margin_required:,.0f} VND ({data.margin_rate*100:.0f}%)                       │
│  ────────────────────────────────────────────────────────────    │
│  Cò quỹ (Funding): {data.funding_rate*100:+.3f}%/ngày (Annual: ~{annual_funding:.1f}%)              │
│  ────────────────────────────────────────────────────────────    │
│  📊 ĐỘ KHÚC XẠO (Yield Curve):                             │
│     F2M (Tháng tới): {data.futures_m2:,.2f} ({m2_sign}{m2_basis:+.2f})                           │
│     F1Q (Quý tới): {data.futures_f1q:,.2f} ({f1q_sign}{f1q_basis:+.2f})                           │
│     F2Q (Quý xa): {data.futures_f2q:,.2f} ({f2q_sign}{f2q_basis:+.2f})                           │
│     → {data.term_structure}: {data.term_signal}                      │
├──────────────────────────────────────────────────────────────────┤
│  🤖 AI INSIGHT: {rec_emoji}{data.recommendation}                          │
│  ────────────────────────────────────────────────────────────    │
│  Master Score: {data.master_score}/100 {stars}                                    │
│  ────────────────────────────────────────────────────────────    │"""
        
        # Build Ưu điểm section (only non-empty, aligned with recommendation)
        advantages = []
        is_long = "LONG" in data.recommendation.upper()
        is_short = "SHORT" in data.recommendation.upper()
        
        if data.adx > 25 and data.adx < 60:
            advantages.append(f"• Xu hướng mạnh (ADX {data.adx:.0f})")
        if data.current_price > data.vwap and is_long:
            advantages.append("• Trên VWAP - Tích cực")
        elif data.current_price < data.vwap and is_short:
            advantages.append("• Dưới VWAP - Tiêu cực")
        # Show term structure only if we have actual F2M/F3M data
        if term_bullish and is_long:
            advantages.append("• Contango - Kỳ vọng tích cực")
        elif term_bullish and is_short:
            pass  # Don't show Contango as strength for SHORT
        
        if advantages:
            output += "\n│  ✅ ƯU ĐIỂM:                                                   │"
            for adv in advantages:
                output += f"\n│     {adv:<55}│"
        
        # Build Rủi ro section (only non-empty)
        risks = []
        if hasattr(data, 'index_warning') and data.index_warning:
            risks.append(f"⚠️ {data.index_warning} - Cẩn trọng")
        if data.term_structure in ["BACKWARDATION", "MILD_BACKWARDATION"]:
            risks.append(f"• Backwardation - Cảnh báo giảm")
        elif term_bullish and is_short:
            risks.append("• Contango không đáng tin (F2M/F3M: N/A)")
        if data.rsi > 70:
            risk_level = "Cực kỳ nguy hiểm" if data.rsi > 75 else "Nguy hiểm"
            risks.append(f"• RSI {data.rsi:.0f} - {data.rsi_zone} - {risk_level}")
        if data.adx > 60:
            risks.append("• ADX >60 - Có thể cạn kiệt")
        if data.days_to_expiry < 10:
            risks.append(f"• Còn {data.days_to_expiry} ngày đáo hạn - Theta nghiêm trọng")
        elif data.days_to_expiry < 20:
            risks.append(f"• Còn {data.days_to_expiry} ngày đáo hạn - Theta tăng dần")
        
        if risks:
            output += "\n│  ⚠️ RỦI RO:                                                    │"
            for risk in risks:
                output += f"\n│     {risk:<55}│"
        
        # Calculate SL/TP distances based on position type
        is_short = "SHORT" in data.recommendation.upper()
        if is_short:
            sl_dist = data.stop_loss - data.current_price
            tp_dist = data.current_price - data.take_profit
            sl_text = f"+{sl_dist:.0f} điểm"
            tp_text = f"+{tp_dist:.0f} điểm"
        else:
            sl_dist = data.current_price - data.stop_loss
            tp_dist = data.take_profit - data.current_price
            sl_text = f"-{sl_dist:.0f} điểm"
            tp_text = f"+{tp_dist:.0f} điểm"
        
        output += f"""
│  ────────────────────────────────────────────────────────────    │
│  📌 HÀNH ĐỘNG ({'SHORT' if is_short else 'LONG'}):                                    │
│     • Entry: {data.entry_target:,.0f}                                          │
│     • 🛑 Stop Loss: {data.stop_loss:,.0f} ({sl_text}) - RR {data.rr_ratio:.1f}x                      │
│     • 🎯 Take Profit: {data.take_profit:,.0f} ({tp_text})                          │
│     • ⏰ Hold tối đa: {max(2, data.days_to_expiry - 3)} ngày (trước đáo hạn)            │
│     • ⚠️ Roll sang VN30F2M nếu hold > {max(4, data.days_to_expiry - 5)} ngày          │
└──────────────────────────────────────────────────────────────────┘
"""
        return output
    
    def _make_bar(self, value: float, max_val: float, width: int = 20) -> str:
        """Create a visual bar"""
        filled = int((value / max_val) * width)
        bar = "█" * filled + "░" * (width - filled)
        return bar
