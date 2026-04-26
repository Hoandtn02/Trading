"""
Futures Analyzer Module - Phase 3
Phân tích hợp đồng tương lai (VN30F)
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
import pandas as pd
from datetime import datetime


@dataclass
class FuturesData:
    """Data structure for futures information"""
    symbol: str = ""
    name: str = ""
    # Prices
    current_price: float = 0.0  # Futures price
    spot_price: float = 0.0  # VN30 index price
    change_value: float = 0.0
    change_percent: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open_price: float = 0.0
    volume: int = 0
    # Basis
    basis: float = 0.0
    basis_type: str = "Premium"  # Premium/Discount
    # Expiry
    expiry_date: str = ""
    days_to_expiry: int = 0
    # Contract info
    contract_multiplier: float = 100000  # VND/điểm
    margin_rate: float = 0.10  # 10%
    funding_rate: float = 0.0  # Daily funding rate
    # Term structure
    futures_m2: float = 0.0
    futures_m3: float = 0.0
    term_structure: str = "CONTANGO"  # CONTANGO/BACKWARDATION
    # Technical
    atr: float = 0.0
    atr_status: str = "TRUNG BÌNH"
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
    adx_status: str = "Xu hướng yếu"
    rsi: float = 50.0
    rsi_zone: str = "TRUNG LẬP"
    macd_histogram: float = 0.0
    macd_direction: str = "đang tăng"
    # Score
    master_score: int = 50
    recommendation: str = "WATCH"
    trend: str = "SIDEWAYS"
    technical_status: str = "NEUTRAL"


class FuturesAnalyzer:
    """Analyzer for futures contracts (VN30F)"""
    
    def __init__(self, period_ta: int = 30):
        self.period_ta = period_ta
    
    def analyze(self, symbol: str = "VN30F1M") -> FuturesData:
        """
        Analyze futures contract with full technical analysis
        """
        data = FuturesData(symbol=symbol, name=self._get_name(symbol))
        
        self._get_futures_data(data)
        self._get_spot_index(data)
        self._get_term_structure(data)
        self._calculate_basis(data)
        self._calculate_contract_value(data)
        self._calculate_technical(data)
        self._calculate_master_score(data)
        self._determine_status(data)
        
        return data
    
    def _get_name(self, symbol: str) -> str:
        names = {
            "VN30F1M": "HỢP ĐỒNG TƯƠNG LAI VN30",
            "VN30F": "VN30 Futures",
            "VN30F2M": "VN30 Futures - Tháng 2",
            "VN30F3M": "VN30 Futures - Tháng 3",
        }
        return names.get(symbol, symbol)
    
    def _get_futures_data(self, data: FuturesData):
        """Get futures OHLCV data"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            
            # Try common contract codes
            for contract in ["VN30F1M", "VN30F", "VN30F2506", "VN30F2606"]:
                try:
                    df = mkt.futures(contract).ohlcv(
                        interval="1D",
                        length=self.period_ta + 1
                    )
                    if df is not None and len(df) > 0:
                        data.symbol = contract
                        self._extract_data(data, df)
                        self._set_expiry_info(data, contract)
                        return
                except:
                    continue
            
        except ImportError:
            self._get_futures_data_fallback(data)
        except Exception as e:
            print(f"[FuturesAnalyzer] Error: {e}")
            self._get_futures_data_fallback(data)
    
    def _get_futures_data_fallback(self, data: FuturesData):
        """Fallback using vnstock"""
        try:
            from vnstock.explorer.kbs.quote import Quote
            import pandas as pd
            
            q = Quote(symbol="VN30F", show_log=False)
            end = pd.Timestamp.today().strftime('%Y-%m-%d')
            start = (pd.Timestamp.today() - pd.DateOffset(days=self.period_ta)).strftime('%Y-%m-%d')
            df = q.history(start=start, end=end, interval='1D')
            
            if df is not None and len(df) > 0:
                self._extract_data(data, df)
                self._set_expiry_info(data, "VN30F1M")
                
        except Exception as e:
            print(f"[FuturesAnalyzer] Fallback error: {e}")
    
    def _extract_data(self, data: FuturesData, df: pd.DataFrame):
        """Extract data from OHLCV dataframe"""
        if len(df) > 0:
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last
            
            # Prices
            for col in ['close', 'Close']:
                if col in df.columns:
                    data.current_price = float(last.get(col, 0))
                    prev_close = float(prev.get(col, data.current_price))
                    if prev_close > 0:
                        data.change_value = data.current_price - prev_close
                        data.change_percent = round(data.change_value / prev_close * 100, 2)
                    break
            
            data.open_price = float(last.get('open', data.current_price))
            data.high = float(last.get('high', data.current_price))
            data.low = float(last.get('low', data.current_price))
            
            # Volume
            vol_col = 'volume' if 'volume' in df.columns else 'Volume'
            if vol_col in df.columns:
                data.volume = int(last.get(vol_col, 0))
    
    def _set_expiry_info(self, data: FuturesData, contract: str):
        """Set expiry date info"""
        # VN30F expiry is typically the last Thursday of the month
        now = pd.Timestamp.now()
        # Estimate: add months based on contract suffix
        if "2M" in contract:
            expiry_month = now + pd.DateOffset(months=2)
        elif "3M" in contract:
            expiry_month = now + pd.DateOffset(months=3)
        else:
            expiry_month = now + pd.DateOffset(months=1)
        
        # Find last Thursday
        expiry = expiry_month + pd.offsets.MonthEnd(0)
        while expiry.dayofweek != 3:  # Thursday
            expiry -= pd.DateOffset(days=1)
        
        data.expiry_date = expiry.strftime("%Y-%m-%d")
        data.days_to_expiry = (expiry - now).days
    
    def _get_spot_index(self, data: FuturesData):
        """Get underlying VN30 index data"""
        try:
            from vnstock_data import Market
            mkt = Market()
            df = mkt.index("VN30").ohlcv(interval="1D", length=2)
            
            if df is not None and len(df) > 0:
                for col in ['close', 'Close']:
                    if col in df.columns:
                        data.spot_price = float(df.iloc[-1].get(col, 0))
                        break
                        
        except ImportError:
            try:
                from vnstock.explorer.vci.quote import Quote
                import pandas as pd
                
                q = Quote(symbol="VNINDEX", show_log=False)
                end = pd.Timestamp.today().strftime('%Y-%m-%d')
                start = (pd.Timestamp.today() - pd.DateOffset(days=5)).strftime('%Y-%m-%d')
                df = q.history(start=start, end=end, interval='1D')
                
                if df is not None and len(df) > 0:
                    data.spot_price = float(df.iloc[-1].get('close', 0))
            except:
                pass
        except Exception as e:
            print(f"[FuturesAnalyzer] Spot index error: {e}")
    
    def _get_term_structure(self, data: FuturesData):
        """Get term structure (contango/backwardation)"""
        try:
            from vnstock_data import Market
            mkt = Market()
            
            # Get M2 contract
            try:
                df2 = mkt.futures("VN30F2M").ohlcv(interval="1D", length=1)
                if df2 is not None and len(df2) > 0:
                    for col in ['close', 'Close']:
                        if col in df2.columns:
                            data.futures_m2 = float(df2.iloc[-1].get(col, 0))
                            break
            except:
                pass
            
            # Get M3 contract
            try:
                df3 = mkt.futures("VN30F3M").ohlcv(interval="1D", length=1)
                if df3 is not None and len(df3) > 0:
                    for col in ['close', 'Close']:
                        if col in df3.columns:
                            data.futures_m3 = float(df3.iloc[-1].get(col, 0))
                            break
            except:
                pass
            
            # Determine term structure
            if data.futures_m2 > data.current_price:
                data.term_structure = "CONTANGO"
            elif data.futures_m2 < data.current_price:
                data.term_structure = "BACKWARDATION"
                
        except Exception as e:
            print(f"[FuturesAnalyzer] Term structure error: {e}")
    
    def _calculate_basis(self, data: FuturesData):
        """Calculate basis (difference between futures and underlying)"""
        if data.spot_price > 0 and data.current_price > 0:
            data.basis = data.current_price - data.spot_price
            data.basis_type = "Premium" if data.basis > 0 else "Discount"
    
    def _calculate_contract_value(self, data: FuturesData):
        """Calculate contract value and margin"""
        if data.current_price > 0:
            data.contract_multiplier = 100000  # VND per point
            data.funding_rate = 0.00002  # ~0.002% per day, ~7.3% annual
            # Total contract value
            self._contract_value = data.current_price * data.contract_multiplier
            # Required margin
            self._margin_required = self._contract_value * data.margin_rate
    
    def _calculate_technical(self, data: FuturesData):
        """Calculate technical indicators"""
        try:
            from vnstock_ta import Indicator
            
            # Try to get OHLCV data
            try:
                from vnstock_data import Market
                mkt = Market()
                df = mkt.futures(data.symbol).ohlcv(interval="1D", length=self.period_ta + 30)
            except:
                from vnstock.explorer.kbs.quote import Quote
                import pandas as pd
                q = Quote(symbol="VN30F", show_log=False)
                end = pd.Timestamp.today().strftime('%Y-%m-%d')
                start = (pd.Timestamp.today() - pd.DateOffset(days=self.period_ta + 30)).strftime('%Y-%m-%d')
                df = q.history(start=start, end=end, interval='1D')
            
            if df is not None and len(df) > 20:
                indicator = Indicator(close=df['close'])
                
                # ATR
                atr = indicator.atr(period=14)
                if hasattr(atr, 'iloc'):
                    data.atr = float(atr.iloc[-1])
                    if data.atr > 30:
                        data.atr_status = "CAO"
                    elif data.atr < 15:
                        data.atr_status = "THẤP"
                    else:
                        data.atr_status = "TRUNG BÌNH"
                
                # Bollinger Width
                bb = indicator.bollinger_bands()
                if bb is not None:
                    upper = float(bb['upper'].iloc[-1])
                    lower = float(bb['lower'].iloc[-1])
                    data.bollinger_width = upper - lower
                
                # VWAP (simplified)
                typical = (df['high'] + df['low'] + df['close']) / 3
                data.vwap = float((typical * df['volume']).sum() / df['volume'].sum())
                
                # Pivot points
                pivot_price = (data.high + data.low + data.current_price) / 3
                data.pivot = pivot_price
                data.r1 = 2 * pivot_price - data.low
                data.r2 = pivot_price + (data.high - data.low)
                data.s1 = 2 * pivot_price - data.high
                data.s2 = pivot_price - (data.high - data.low)
                
                # SMA
                sma20 = indicator.sma(period=20)
                if sma20 is not None and hasattr(sma20, 'iloc'):
                    data.sma_20 = float(sma20.iloc[-1])
                
                sma50 = indicator.sma(period=50)
                if sma50 is not None and hasattr(sma50, 'iloc'):
                    data.sma_50 = float(sma50.iloc[-1])
                
                # ADX
                adx = indicator.adx(period=14)
                if adx is not None and hasattr(adx, 'iloc'):
                    data.adx = float(adx.iloc[-1])
                    if data.adx > 25:
                        data.adx_status = "Xu hướng mạnh"
                    elif data.adx < 20:
                        data.adx_status = "Xu hướng yếu"
                    else:
                        data.adx_status = "Xu hướng trung bình"
                
                # RSI
                rsi = indicator.rsi(period=14)
                if hasattr(rsi, 'iloc'):
                    data.rsi = float(rsi.iloc[-1])
                    if data.rsi > 70:
                        data.rsi_zone = "QUÁ MUA"
                    elif data.rsi < 30:
                        data.rsi_zone = "QUÁ BÁN"
                    else:
                        data.rsi_zone = "TRUNG LẬP"
                
                # MACD
                macd = indicator.macd()
                if macd is not None and hasattr(macd, 'iloc'):
                    data.macd_histogram = float(macd.iloc[-1])
                    if len(macd) > 1:
                        prev_macd = float(macd.iloc[-2])
                        data.macd_direction = "đang tăng" if data.macd_histogram > prev_macd else "đang giảm"
                            
        except Exception as e:
            print(f"[FuturesAnalyzer] Technical error: {e}")
    
    def _calculate_master_score(self, data: FuturesData):
        """Calculate master score"""
        score = 50
        
        # Trend scoring
        if data.current_price > data.sma_20 and data.current_price > data.sma_50:
            score += 15
        elif data.current_price > data.sma_20:
            score += 7
        
        # ADX
        if data.adx > 25:
            score += 10
        elif data.adx > 20:
            score += 5
        
        # Basis
        if 0 < data.basis < 10:
            score += 5  # Small premium is healthy
        elif data.basis > 20:
            score -= 10  # Large premium is risky
        
        # Days to expiry
        if data.days_to_expiry < 7:
            score -= 10  # Near expiry = theta decay risk
        elif data.days_to_expiry > 20:
            score += 5  # Plenty of time
        
        data.master_score = max(0, min(100, score))
        
        if data.master_score >= 65:
            data.recommendation = "LONG NHẸNHAN"
        elif data.master_score >= 45:
            data.recommendation = "WATCH"
        else:
            data.recommendation = "SHORT NHẸNHAN"
    
    def _determine_status(self, data: FuturesData):
        """Determine technical status"""
        # Trend
        if data.current_price > data.sma_20 and data.current_price > data.sma_50:
            data.trend = "UPTREND"
        elif data.current_price < data.sma_20 and data.current_price < data.sma_50:
            data.trend = "DOWNTREND"
        else:
            data.trend = "SIDEWAYS"
        
        # Status
        if data.change_percent >= 0.5:
            data.technical_status = "BULLISH"
        elif data.change_percent <= -0.5:
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
        
        # M2 basis
        m2_basis = data.futures_m2 - data.current_price if data.futures_m2 > 0 else 0
        m2_sign = "+" if m2_basis > 0 else ""
        
        # M3 basis
        m3_basis = data.futures_m3 - data.futures_m2 if data.futures_m3 > 0 and data.futures_m2 > 0 else 0
        m3_sign = "+" if m3_basis > 0 else ""
        
        # RSI bar
        rsi_bar = self._make_bar(data.rsi, 100, 20)
        
        # Trend direction
        trend_direction = "TRÊN" if data.current_price > data.sma_20 else "DƯỚI"
        
        # Master score stars
        stars = "★" * (data.master_score // 20) + "☆" * (5 - data.master_score // 20)
        
        # Recommendation emoji
        if data.recommendation == "LONG NHẸNHAN":
            rec_emoji = "🟢"
        elif data.recommendation == "SHORT NHẸNHAN":
            rec_emoji = "🔴"
        else:
            rec_emoji = "🟡"
        
        output = f"""
┌──────────────────────────────────────────────────────────────────┐
│  📊 {data.symbol.upper()} - HỢP ĐỒNG TƯƠNG LAI VN30               {now} │
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
│     ATR(14): {data.atr:.0f} điểm - BIẾN ĐỘNG {data.atr_status}                  │
│     Bollinger Width: {data.bollinger_width:.0f} điểm (Biên độ bình thường)            │
│  🎯 VÙNG GIÁ                                                    │
│     VWAP: {data.vwap:,.2f} - Giá đang {"TRÊN" if data.current_price > data.vwap else "DƯỚI"} VWAP                        │
│     Pivot: {data.pivot:,.2f}                                            │
│     R1: {data.r1:,.2f} │ R2: {data.r2:,.2f}                               │
│     S1: {data.s1:,.2f} │ S2: {data.s2:,.2f}                               │
│  🔄 XU HƯỚNG                                                    │
│     SMA(20): {data.sma_20:,.2f} │ SMA(50): {data.sma_50:,.2f}                     │
│     Giá đang {"TRÊN" if data.current_price > data.sma_20 else "DƯỚI"} cả 2 SMA → {data.trend}                          │
│     ADX: {data.adx:.0f} - {data.adx_status}                              │
│  📈 ĐỘNG LƯỢNG                                                  │
│     RSI(14): {data.rsi:.0f} {rsi_bar} Zone: {data.rsi_zone}        │
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
│  📊 ĐỘ KHÚC XẠO (Contango/Backwardation):                    │
│     VN30F2M: {data.futures_m2:,.2f} ({m2_sign}{m2_basis:+.2f})                           │
│     VN30F3M: {data.futures_m3:,.2f} ({m3_sign}{m3_basis:+.2f})                           │
│     → Thị trường {data.term_structure} ({'Bullish' if data.term_structure == 'CONTANGO' else 'Bearish'})                      │
├──────────────────────────────────────────────────────────────────┤
│  🤖 AI INSIGHT: {rec_emoji}{data.recommendation}                          │
│  ────────────────────────────────────────────────────────────    │
│  Master Score: {data.master_score}/100 {stars}                                    │
│  ────────────────────────────────────────────────────────────    │
│  ✅ ƯU ĐIỂM:                                                   │
│     • Basis {basis_sign}{data.basis:.1f} - {data.basis_type} nhẹ                          │
│     • Giá đang {"trên" if data.current_price > data.vwap else "dưới"} VWAP                                      │
│     • {data.term_structure} nhẹ - {'Bullish signal' if data.term_structure == 'CONTANGO' else 'Bearish signal'}                           │
│  ⚠️ RỦI RO:                                                    │
│     • ADX {data.adx:.0f} - {data.adx_status.lower()}                   │
│     • Còn {data.days_to_expiry} ngày đáo hạn - Theta decay sắp tăng              │
│     • Basis có thể thu hẹp nhanh gần đáo hạn                 │
│  ────────────────────────────────────────────────────────────    │
│  📌 HÀNH ĐỘNG:                                                  │
│     • LONG: Mở quanh {data.s1:,.0f}-{data.sma_20:,.0f} với SL {data.s2:,.0f}               │
│     • 🛑 Stop Loss: {data.s2:,.0f} ({data.s1 - data.s2:+.0f} điểm)                           │
│     • 🎯 Mục tiêu: {data.r1:,.0f} ({data.r1 - data.current_price:+.0f} điểm)                           │
│     • ⏰ Thời gian hold: {max(2, min(data.days_to_expiry - 3, 5))}-3 ngày (trước đáo hạn)            │
│     • ⚠️ Chú ý: Roll sang VN30F2M nếu hold > 4 ngày          │
└──────────────────────────────────────────────────────────────────┘
"""
        return output
    
    def _make_bar(self, value: float, max_val: float, width: int = 20) -> str:
        """Create a visual bar"""
        filled = int((value / max_val) * width)
        bar = "█" * filled + "░" * (width - filled)
        return bar
