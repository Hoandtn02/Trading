"""
CW (Covered Warrant) Analyzer Module - Phase 4
Phân tích chứng quyền có bảo đảm
"""
from dataclasses import dataclass, field
from typing import Optional, List
import pandas as pd
from datetime import datetime


@dataclass
class CWData:
    """Data structure for covered warrant information"""
    symbol: str = ""
    name: str = ""
    underlying: str = ""  # Cổ phiếu cơ sở
    issuer: str = ""  # Tổ chức phát hành
    current_price: float = 0.0
    change_value: float = 0.0
    change_percent: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open_price: float = 0.0
    volume: int = 0
    # Warrant specific
    underlying_price: float = 0.0
    strike_price: float = 0.0
    maturity_date: str = ""
    exercise_ratio: float = 1.0
    warrant_type: str = "CALL"  # or PUT
    # Pricing
    intrinsic_value: float = 0.0
    time_value: float = 0.0
    premium: float = 0.0
    moneyness: str = ""  # ITM/ATM/OTM
    # Greeks
    delta: float = 0.0
    gamma: float = 0.0
    vega: float = 0.0
    theta: float = 0.0
    # Leverage
    effective_leverage: float = 0.0
    break_even: float = 0.0
    # Underlying analysis
    underlying_rsi: float = 50.0
    underlying_adx: float = 0.0
    underlying_trend: str = "NEUTRAL"
    # Score
    master_score: int = 50
    recommendation: str = "WATCH"
    trend: str = "NEUTRAL"
    technical_status: str = "NEUTRAL"


class CWAnalyzer:
    """Analyzer for covered warrants"""
    
    def __init__(self, period_ta: int = 30):
        self.period_ta = period_ta
    
    def analyze(self, symbol: str = "CACB2511") -> CWData:
        """
        Analyze covered warrant with full Greeks analysis
        """
        data = CWData(symbol=symbol)
        
        # Parse warrant symbol
        self._parse_warrant_symbol(data)
        
        # Get warrant price data
        self._get_warrant_data(data)
        
        # Get underlying info
        self._get_underlying_data(data)
        
        # Calculate Greeks
        self._calculate_greeks(data)
        
        # Get underlying technical
        self._get_underlying_technical(data)
        
        self._calculate_master_score(data)
        self._determine_status(data)
        
        return data
    
    def _parse_warrant_symbol(self, data: CWData):
        """Parse warrant symbol to extract info"""
        # Format: X + [UNDERLYING 2-4 chars] + [YYMM]
        # Examples:
        #   CACB2511 -> C(Call) + ACB(Underlying) + 25(Year) + 11(Month)
        #   CVCB2601 -> C(Call) + VCB(Underlying) + 26(Year) + 01(Month)
        
        if len(data.symbol) >= 7:
            data.warrant_type = "CALL" if data.symbol[0] == 'C' else "PUT"
            
            sym = data.symbol[1:]
            
            known_underlyings = ['VNM', 'VCB', 'VPB', 'TCB', 'CTG', 'BID', 'SSI', 'HPG', 'FPT', 
                                  'MWG', 'PNJ', 'VRE', 'VHM', 'KDH', 'STB', 'ACB', 'SHB',
                                  'MBB', 'TPB', 'MSB', 'HDB', 'LPB', 'OCB', 'SSB', 'VIB']
            
            underlying_found = None
            for length in [4, 3, 2]:
                if len(sym) > length:
                    candidate = sym[:length]
                    if candidate in known_underlyings:
                        underlying_found = candidate
                        sym_remaining = sym[length:]
                        break
            
            if underlying_found and sym_remaining:
                data.underlying = underlying_found
                if len(sym_remaining) == 4:
                    year_part = sym_remaining[:2]
                    month_part = sym_remaining[2:]
                    year = 2000 + int(year_part) if int(year_part) < 100 else int(year_part)
                    month = int(month_part)
                    data.maturity_date = f"{year}-{month:02d}"
    
    def _get_warrant_data(self, data: CWData):
        """Get warrant OHLCV data"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            df = mkt.warrant(data.symbol).ohlcv(
                interval="1D",
                length=self.period_ta + 1
            )
            
            if df is not None and len(df) > 1:
                last = df.iloc[-1]
                prev = df.iloc[-2]
                
                data.current_price = float(last.get('close', 0)) * 1000
                data.open_price = float(last.get('open', 0)) * 1000
                data.high = float(last.get('high', 0)) * 1000
                data.low = float(last.get('low', 0)) * 1000
                data.volume = int(last.get('volume', 0)) if pd.notna(last.get('volume')) else 0
                
                prev_close = float(prev.get('close', 0)) * 1000
                if prev_close > 0:
                    data.change_value = data.current_price - prev_close
                    data.change_percent = round(data.change_value / prev_close * 100, 2)
                    
        except ImportError:
            self._get_warrant_data_fallback(data)
        except Exception as e:
            print(f"[CWAnalyzer] Error: {e}")
            self._get_warrant_data_fallback(data)
    
    def _get_warrant_data_fallback(self, data: CWData):
        """Fallback using vnstock"""
        try:
            from vnstock.explorer.kbs.trading import Trading
            trading = Trading(show_log=False)
            df = trading.price_board(symbols_list=[data.symbol], get_all=False)
            
            if df is not None and len(df) > 0:
                row = df.iloc[0]
                data.current_price = float(row.get('close', 0))
                data.change_value = float(row.get('change', 0))
                data.change_percent = float(row.get('pct_change', 0))
                data.high = float(row.get('high', 0))
                data.low = float(row.get('low', 0))
                data.volume = int(row.get('volume', 0))
        except Exception as e:
            print(f"[CWAnalyzer] Fallback error: {e}")
    
    def _get_underlying_data(self, data: CWData):
        """Get underlying stock info"""
        try:
            from vnstock_data import Market
            mkt = Market()
            
            summary = mkt.warrant(data.symbol).summary()
            
            if summary is not None and len(summary) > 0:
                row = summary.iloc[-1] if isinstance(summary, pd.DataFrame) else summary
                
                for col in row.index:
                    col_lower = str(col).lower()
                    if 'strike' in col_lower:
                        data.strike_price = float(row[col]) * 1000
                    elif 'exercise' in col_lower:
                        data.exercise_ratio = float(row[col])
                    elif 'ratio' in col_lower:
                        data.exercise_ratio = float(row[col])
                        
        except ImportError:
            self._get_underlying_data_fallback(data)
        except Exception as e:
            print(f"[CWAnalyzer] Underlying error: {e}")
            self._get_underlying_data_fallback(data)
    
    def _get_underlying_data_fallback(self, data: CWData):
        """Fallback for underlying data"""
        try:
            from vnstock.explorer.vci.quote import Quote
            import pandas as pd
            
            q = Quote(symbol=data.underlying, show_log=False)
            end = pd.Timestamp.today().strftime('%Y-%m-%d')
            start = (pd.Timestamp.today() - pd.DateOffset(days=5)).strftime('%Y-%m-%d')
            df = q.history(start=start, end=end, interval='1D')
            
            if df is not None and len(df) > 0:
                last = df.iloc[-1]
                for col in df.columns:
                    if 'close' in str(col).lower():
                        data.underlying_price = float(last[col]) * 1000
                        break
        except Exception as e:
            print(f"[CWAnalyzer] Underlying fallback error: {e}")
    
    def _calculate_greeks(self, data: CWData):
        """Calculate option Greeks"""
        if data.underlying_price <= 0 or data.strike_price <= 0:
            return
        
        # Intrinsic value
        if data.warrant_type == "CALL":
            data.intrinsic_value = max(0, (data.underlying_price - data.strike_price) / data.exercise_ratio)
            moneyness_pct = (data.underlying_price - data.strike_price) / data.strike_price * 100
        else:
            data.intrinsic_value = max(0, (data.strike_price - data.underlying_price) / data.exercise_ratio)
            moneyness_pct = (data.strike_price - data.underlying_price) / data.strike_price * 100
        
        # Time value
        data.time_value = data.current_price - data.intrinsic_value
        
        # Premium
        if data.intrinsic_value > 0:
            data.premium = (data.current_price - data.intrinsic_value) / data.intrinsic_value * 100
        elif data.current_price > 0:
            data.premium = 0
        
        # Moneyness
        if moneyness_pct > 1:
            data.moneyness = f"ITM (+{moneyness_pct:.1f}% in-the-money)"
        elif moneyness_pct < -1:
            data.moneyness = f"OTM ({moneyness_pct:.1f}%)"
        else:
            data.moneyness = "ATM"
        
        # Delta (simplified)
        if data.warrant_type == "CALL":
            data.delta = min(1, max(0, (data.underlying_price - data.strike_price) / data.underlying_price * 2 + 0.5))
        else:
            data.delta = min(0, max(-1, -(data.strike_price - data.underlying_price) / data.underlying_price * 2 - 0.5))
        
        # Gamma (simplified)
        data.gamma = abs(data.delta) * 0.02
        
        # Vega (simplified)
        data.vega = data.current_price * 0.05
        
        # Theta (approximate daily decay)
        try:
            maturity = pd.to_datetime(data.maturity_date)
            days_to_maturity = max(1, (maturity - pd.Timestamp.now()).days)
            # Theta is typically (option_price / days_to_maturity) * (1/365)
            data.theta = -abs(data.time_value) / days_to_maturity if days_to_maturity > 0 else 0
        except:
            data.theta = -data.current_price * 0.01
        
        # Effective leverage
        if data.current_price > 0 and data.underlying_price > 0:
            data.effective_leverage = (data.underlying_price / data.exercise_ratio) / data.current_price
        
        # Break-even
        if data.warrant_type == "CALL":
            data.break_even = data.strike_price + (data.time_value * data.exercise_ratio)
        else:
            data.break_even = data.strike_price - (data.time_value * data.exercise_ratio)
    
    def _get_underlying_technical(self, data: CWData):
        """Get underlying stock technical analysis"""
        try:
            from vnstock_ta import Indicator
            
            from vnstock.explorer.vci.quote import Quote
            import pandas as pd
            
            q = Quote(symbol=data.underlying, show_log=False)
            end = pd.Timestamp.today().strftime('%Y-%m-%d')
            start = (pd.Timestamp.today() - pd.DateOffset(days=90)).strftime('%Y-%m-%d')
            df = q.history(start=start, end=end, interval='1D')
            
            if df is not None and len(df) > 20:
                indicator = Indicator(close=df['close'])
                
                rsi = indicator.rsi(period=14)
                if hasattr(rsi, 'iloc'):
                    data.underlying_rsi = float(rsi.iloc[-1])
                
                adx = indicator.adx(period=14)
                if hasattr(adx, 'iloc'):
                    data.underlying_adx = float(adx.iloc[-1])
                
                if data.underlying_rsi > 50 and data.underlying_adx > 20:
                    data.underlying_trend = "BULLISH"
                elif data.underlying_rsi < 50 and data.underlying_adx > 20:
                    data.underlying_trend = "BEARISH"
                else:
                    data.underlying_trend = "NEUTRAL"
                            
        except Exception as e:
            print(f"[CWAnalyzer] Technical error: {e}")
    
    def _calculate_master_score(self, data: CWData):
        """Calculate master score"""
        score = 50
        
        # Status scoring
        if "ITM" in data.moneyness:
            score += 10
        elif "ATM" in data.moneyness:
            score += 5
        
        # Days to maturity
        try:
            maturity = pd.to_datetime(data.maturity_date)
            days_to_maturity = (maturity - pd.Timestamp.now()).days
            
            if days_to_maturity < 30:
                score -= 15  # Time decay risk
            elif days_to_maturity > 90:
                score += 10  # Enough time value
            elif days_to_maturity > 180:
                score += 5
        except:
            pass
        
        # Underlying trend
        if data.underlying_trend == "BULLISH":
            score += 10
        elif data.underlying_trend == "BEARISH":
            score -= 10
        
        # Delta
        if 0.3 <= abs(data.delta) <= 0.7:
            score += 10  # Optimal delta range
        
        # Premium
        if data.premium > 50:
            score -= 10  # Too expensive
        elif data.premium < 20:
            score += 5
        
        data.master_score = max(0, min(100, score))
        
        if data.master_score >= 60:
            data.recommendation = "CÓ THỂ MUA"
        elif data.master_score >= 40:
            data.recommendation = "THEO DÕI"
        else:
            data.recommendation = "KHÔNG KHUYẾN KHÍCH"
    
    def _determine_status(self, data: CWData):
        """Determine warrant status and trend"""
        # Trend
        if data.change_percent >= 2:
            data.trend = "STRONG UP"
        elif data.change_percent >= 0.5:
            data.trend = "UPTREND"
        elif data.change_percent <= -2:
            data.trend = "STRONG DOWN"
        elif data.change_percent <= -0.5:
            data.trend = "DOWNTREND"
        else:
            data.trend = "SIDEWAYS"
        
        # Status
        if data.change_percent >= 3:
            data.technical_status = "BULLISH"
        elif data.change_percent <= -3:
            data.technical_status = "BEARISH"
        else:
            data.technical_status = "NEUTRAL"
    
    def format_output(self, data: CWData) -> str:
        """Format analysis output matching ARCHITECTURE_ROADMAP.md"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        change_emoji = "🟢" if data.change_percent >= 0 else "🔴"
        
        # Days to maturity
        days_to_maturity = 0
        try:
            maturity = pd.to_datetime(data.maturity_date)
            days_to_maturity = (maturity - pd.Timestamp.now()).days
        except:
            pass
        
        # Master score stars
        stars = "★" * (data.master_score // 20) + "☆" * (5 - data.master_score // 20)
        
        # Recommendation
        if data.recommendation == "CÓ THỂ MUA":
            rec_emoji = "🟢"
        elif data.recommendation == "KHÔNG KHUYẾN KHÍCH":
            rec_emoji = "🔴"
        else:
            rec_emoji = "🟡"
        
        # Capital comparison
        cw_cost = data.current_price
        stock_cost = data.underlying_price * 100 / data.exercise_ratio if data.exercise_ratio > 0 else data.underlying_price * 100
        capital_saved = (1 - cw_cost / stock_cost) * 100 if stock_cost > 0 else 0
        
        output = f"""
┌──────────────────────────────────────────────────────────────────┐
│  🏦 CHỨNG QUYỀN {data.symbol.upper()}                    THỜI GIAN: {now}   │
├──────────────────────────────────────────────────────────────────┤
│  💰 THÔNG TIN CHỨNG QUYỀN                                     │
│  ────────────────────────────────────────────────────────────    │
│  Mã CW: {data.symbol}                                             │
│  Tổ chức phát hành: {data.issuer if data.issuer else 'N/A'}                      │
│  ────────────────────────────────────────────────────────────    │
│  💵 GIÁ & ĐIỀU KHOẢN                                         │
│  ────────────────────────────────────────────────────────────    │
│  Giá CW: {data.current_price:,.0f} VND                                           │
│  Giá underlying ({data.underlying}): {data.underlying_price:,.0f} VND                            │
│  Strike price: {data.strike_price:,.0f} VND                                    │
│  ────────────────────────────────────────────────────────────    │
│  Moneyness: {data.moneyness}                         │
│  Intrinsic Value: {data.intrinsic_value:,.0f} VND ({data.current_price - data.intrinsic_value:+,.0f})                 │
│  Time Value: {data.time_value:,.0f} VND                               │
│  Premium: {data.premium:+.1f}% ({'Discount' if data.premium < 0 else 'Premium'})                            │
│  ────────────────────────────────────────────────────────────    │
│  📅 THỜI GIAN                                                 │
│  ────────────────────────────────────────────────────────────    │
│  Ngày đáo hạn: {data.maturity_date} ({days_to_maturity} ngày)                      │
│  Theta decay: ~{abs(data.theta):,.0f} VND/ngày                           │
├──────────────────────────────────────────────────────────────────┤
│  📊 CÁC CHỈ SỐ HY ĐỖNG                                       │
│  ────────────────────────────────────────────────────────────    │
│  Delta: {data.delta:.2f} ({data.warrant_type} - Giá CW tăng {abs(data.delta)*100:.0f}% khi {data.underlying} tăng 1%)        │
│  Gamma: {data.gamma:.3f} (Delta thay đổi nhanh gần strike)              │
│  Vega: {data.vega:,.0f} VND/% (Vol tăng 1% → CW tăng {data.vega:,.0f})               │
│  Theta: {data.theta:+,.0f} VND/ngày (Mất {abs(data.theta):,.0f} VND/ngày)       │
│  ────────────────────────────────────────────────────────────    │
│  ĐÒN BẨY (Leverage)                                          │
│  ────────────────────────────────────────────────────────────    │
│  Effective Leverage: {data.effective_leverage:.1f}x ({data.underlying} tăng 1% → CW tăng {data.effective_leverage:.1f}%)         │
│  Break-even: {data.break_even:,.0f} VND ({'Hòa vốn' if data.break_even > data.strike_price else 'Dưới strike'})                   │
│  ────────────────────────────────────────────────────────────    │
│  ⚠️ SO SÁNH VỚI MUA TRỰC TIẾP                               │
│  ────────────────────────────────────────────────────────────    │
│  Mua 1 CW: {cw_cost:,.0f} VND vs Mua 100 {data.underlying}: {stock_cost:,.0f} VND          │
│  Vốn tiết kiệm: {capital_saved:.1f}%                                       │
│  Nhưng rủi ro mất 100% nếu {data.underlying} < {data.break_even:,.0f}         │
├──────────────────────────────────────────────────────────────────┤
│  📊 PHÂN TÍCH {data.underlying} (UNDERLYING)                               │
│  ────────────────────────────────────────────────────────────    │
│  {data.underlying} Technical: RSI {data.underlying_rsi:.0f}, ADX {data.underlying_adx:.0f}, Trend {data.underlying_trend}                 │
│  (Xem chi tiết ở phần Cổ phiếu)                              │
├──────────────────────────────────────────────────────────────────┤
│  🤖 AI INSIGHT: {data.recommendation}              │
│  ────────────────────────────────────────────────────────────    │
│  Master Score: {data.master_score}/100 {stars}                                    │
│  ────────────────────────────────────────────────────────────    │
│  ⚠️ RỦI RO CHÍNH:                                              │
│     • Còn {days_to_maturity} ngày đáo hạn - THETA DECAY {'nhanh' if days_to_maturity < 60 else 'trung bình'}            │
│     • Premium {data.premium:+.1f}% - {'CW đắt' if data.premium > 30 else 'Hợp lý'}                            │
│     • Delta {data.delta:.2f} - {'Tốt' if 0.3 <= abs(data.delta) <= 0.7 else 'Cần điều chỉnh'}                            │
│     • {data.underlying_trend} trend cho {data.underlying}                              │
│  ────────────────────────────────────────────────────────────    │
│  📌 HÀNH ĐỘNG:                                                  │
│     • {data.recommendation}: {'Phù hợp cho người muốn đòn bẩy' if data.recommendation == 'CÓ THỂ MUA' else 'Chờ cơ hội tốt hơn'}                          │
│     • Tìm CW có Delta 0.4-0.6 (Cân bằng đòn bẩy & rủi ro)  │
│     • Luôn đặt stop-loss: -30% giá CW                        │
│     • ⏰ Chỉ trade CW khi hiểu rõ Greeks & Theta             │
└──────────────────────────────────────────────────────────────────┘
"""
        return output
