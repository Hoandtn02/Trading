"""
CW (Covered Warrant) Analyzer Module - Phase 4
Phân tích chứng quyền có bảo đảm
"""
from dataclasses import dataclass
from typing import Optional
import pandas as pd
from datetime import datetime


@dataclass
class CWData:
    """Data structure for covered warrant information"""
    symbol: str = ""
    name: str = ""
    underlying: str = ""  # Cổ phiếu cơ sở
    current_price: float = 0.0
    change_value: float = 0.0
    change_percent: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open_price: float = 0.0
    volume: int = 0
    # Warrant specific
    strike_price: float = 0.0
    maturity_date: str = ""
    exercise_ratio: float = 1.0
    warrant_type: str = "CALL"  # or PUT
    leverage: float = 0.0
    delta: float = 0.0
    status: str = "ITM"  # ITM, ATM, OTM
    trend: str = "NEUTRAL"
    technical_status: str = "NEUTRAL"


class CWAnalyzer:
    """Analyzer for covered warrants"""
    
    def __init__(self, period_ta: int = 30):
        self.period_ta = period_ta
    
    def analyze(self, symbol: str = "CACB2511") -> CWData:
        """
        Analyze covered warrant
        
        Args:
            symbol: Warrant symbol - "CACB2511", "CHPG2512", etc.
        """
        data = CWData(symbol=symbol)
        
        # Parse warrant symbol
        self._parse_warrant_symbol(data)
        
        # Get warrant price data
        self._get_warrant_data(data)
        
        # Get underlying info
        self._get_underlying_data(data)
        
        self._determine_status(data)
        
        return data
    
    def _parse_warrant_symbol(self, data: CWData):
        """Parse warrant symbol to extract info"""
        # Format: XYYYZNNN
        # X = loại: C (Call), P (Put)
        # YYY = mã cổ phiếu cơ sở
        # Z = năm: 5=2025, 6=2026
        # NN = tháng hết hạn
        
        if len(data.symbol) >= 5:
            data.warrant_type = "CALL" if data.symbol[0] == 'C' else "PUT"
            
            # Extract underlying (2nd char to before last 2 digits)
            year_code = data.symbol[-3]
            month_code = data.symbol[-2:]
            
            # Find underlying symbol
            underlying_end = len(data.symbol) - 3  # Remove year+month
            data.underlying = data.symbol[1:underlying_end]
            
            # Calculate maturity year
            year = 2020 + int(year_code)
            month = int(month_code) if month_code.isdigit() else 12
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
                
                # Prices (scaled)
                data.current_price = float(last.get('close', 0)) * 1000
                data.open_price = float(last.get('open', 0)) * 1000
                data.high = float(last.get('high', 0)) * 1000
                data.low = float(last.get('low', 0)) * 1000
                data.volume = int(last.get('volume', 0)) if pd.notna(last.get('volume')) else 0
                
                # Change
                prev_close = float(prev.get('close', 0)) * 1000
                if prev_close > 0:
                    data.change_value = data.current_price - prev_close
                    data.change_percent = round(data.change_value / prev_close * 100, 2)
                    
        except Exception as e:
            print(f"[CWAnalyzer] Error: {e}")
    
    def _get_underlying_data(self, data: CWData):
        """Get underlying stock info for reference"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            summary = mkt.warrant(data.symbol).summary()
            
            if summary is not None and len(summary) > 0:
                row = summary.iloc[-1] if isinstance(summary, pd.DataFrame) else summary
                
                # Extract strike price
                for col in row.index:
                    col_lower = str(col).lower()
                    if 'strike' in col_lower:
                        data.strike_price = float(row[col]) * 1000
                    elif 'exercise' in col_lower:
                        data.exercise_ratio = float(row[col])
                    elif 'ratio' in col_lower:
                        data.exercise_ratio = float(row[col])
                        
        except Exception as e:
            print(f"[CWAnalyzer] Underlying error: {e}")
            
            # Try to get from equity
            try:
                from vnstock_data import Market
                mkt = Market()
                quote = mkt.equity(data.underlying).quote()
                
                if quote is not None and len(quote) > 0:
                    row = quote.iloc[-1] if isinstance(quote, pd.DataFrame) else quote
                    for col in row.index:
                        if 'close' in str(col).lower():
                            underlying_price = float(row[col]) * 1000
                            if data.strike_price > 0:
                                data.delta = min(1, max(0, (underlying_price - data.strike_price) / underlying_price * 10))
                            break
                            
            except:
                pass
    
    def _calculate_leverage(self, data: CWData):
        """Calculate effective leverage"""
        if data.strike_price > 0 and data.current_price > 0:
            # Simplified leverage calculation
            data.leverage = data.strike_price / data.current_price / 10
    
    def _determine_status(self, data: CWData):
        """Determine warrant status and trend"""
        # ITM/ATM/OTM
        try:
            from vnstock_data import Market
            mkt = Market()
            quote = mkt.equity(data.underlying).quote()
            
            if quote is not None and len(quote) > 0:
                row = quote.iloc[-1]
                underlying_price = 0
                for col in row.index:
                    if 'close' in str(col).lower():
                        underlying_price = float(row[col]) * 1000
                        break
                
                if underlying_price > 0 and data.strike_price > 0:
                    if data.warrant_type == "CALL":
                        if underlying_price > data.strike_price * 1.05:
                            data.status = "ITM"
                        elif underlying_price < data.strike_price * 0.95:
                            data.status = "OTM"
                        else:
                            data.status = "ATM"
                    else:  # PUT
                        if underlying_price < data.strike_price * 0.95:
                            data.status = "ITM"
                        elif underlying_price > data.strike_price * 1.05:
                            data.status = "OTM"
                        else:
                            data.status = "ATM"
                            
        except:
            pass
        
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
        """Format analysis output"""
        change_emoji = "🟢" if data.change_percent >= 0 else "🔴"
        
        output = f"""
╔══════════════════════════════════════════════════════════════╗
║  📊 CW ANALYSIS: {data.symbol}
║  Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M')}
╠══════════════════════════════════════════════════════════════╣
║  🏦 Cơ sở: {data.underlying} | Loại: {data.warrant_type}
║  💰 GIÁ: {data.current_price:,.0f} VND
║  {change_emoji} Thay đổi: {data.change_value:+,.0f} ({data.change_percent:+.2f}%)
║  Cao/Thấp: {data.high:,.0f} / {data.low:,.0f}
╠══════════════════════════════════════════════════════════════╣
║  📋 CHỨNG QUYỀN:
║     Strike: {data.strike_price:,.0f} VND
║     Tỷ lệ: {data.exercise_ratio:.0f}:1
║     Hạn: {data.maturity_date}
║     Status: {data.status}
╠══════════════════════════════════════════════════════════════╣
║  📈 XU HƯỚNG: {data.trend}
║  📊 TÌNH TRẠNG: {data.technical_status}
╠══════════════════════════════════════════════════════════════╣
║  🤖 ĐÁNH GIÁ: {self._get_recommendation(data)}
╚══════════════════════════════════════════════════════════════╝
"""
        return output
    
    def _get_recommendation(self, data: CWData) -> str:
        """Get trading recommendation"""
        score = 50
        
        # Status scoring
        if data.status == "ITM":
            score += 15
        elif data.status == "ATM":
            score += 5
        else:  # OTM
            score -= 10
        
        # Trend
        if data.trend.startswith("STRONG"):
            score += 10 if "UP" in data.trend else -10
        elif data.trend.startswith("UP"):
            score += 5
        elif data.trend.startswith("DOWN"):
            score -= 5
        
        # Time value (maturity approaching)
        try:
            maturity = pd.to_datetime(data.maturity_date)
            days_to_maturity = (maturity - pd.Timestamp.now()).days
            if days_to_maturity < 30:
                score -= 10  # Time decay
            elif days_to_maturity > 180:
                score += 5  # More time value
        except:
            pass
        
        if score >= 65:
            return "TÍCH CỰC - Có thể mua"
        elif score >= 45:
            return "TRUNG LẬP - Chờ xác nhận"
        else:
            return "THẬN TRỌNG - Có thể bán"
