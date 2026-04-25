"""
Forex Analyzer Module - Phase 4
Phân tích tỷ giá ngoại hối (EUR/USD, USD/JPY, etc.)
"""
from dataclasses import dataclass
from typing import Optional
import pandas as pd
from datetime import datetime


@dataclass
class ForexData:
    """Data structure for forex information"""
    symbol: str = ""
    name: str = ""
    current_rate: float = 0.0
    change_value: float = 0.0
    change_percent: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open_price: float = 0.0
    unit: str = ""
    trend: str = "NEUTRAL"
    technical_status: str = "NEUTRAL"


class ForexAnalyzer:
    """Analyzer for forex pairs"""
    
    def __init__(self, period_ta: int = 30):
        self.period_ta = period_ta
    
    def analyze(self, symbol: str = "EURUSD") -> ForexData:
        """
        Analyze forex pair
        
        Args:
            symbol: Forex pair - "EURUSD", "USDJPY", "GBPUSD", etc.
        """
        data = ForexData(symbol=symbol, name=self._get_name(symbol))
        
        self._get_forex_data(data)
        self._determine_status(data)
        
        return data
    
    def _get_name(self, symbol: str) -> str:
        names = {
            "EURUSD": "Euro / US Dollar",
            "USDJPY": "US Dollar / Japanese Yen",
            "GBPUSD": "British Pound / US Dollar",
            "USDVND": "US Dollar / Vietnamese Dong",
            "EURVND": "Euro / Vietnamese Dong",
            "JPYVND": "Japanese Yen / Vietnamese Dong",
        }
        return names.get(symbol, symbol)
    
    def _get_forex_data(self, data: ForexData):
        """Get forex OHLCV data"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            
            # For USDVND, use specialized handling
            if data.symbol == "USDVND":
                data.unit = "VND/USD"
                # Try to get from reference data or estimate
                try:
                    # Get USD/VND from commodity or forex
                    df = mkt.forex("USDVND").ohlcv(interval="1D", length=self.period_ta)
                except:
                    df = None
                
                if df is None or len(df) == 0:
                    # Use static estimate for now
                    data.current_rate = 25600  # Approximate rate
                    data.open_price = data.current_rate
                    data.high = data.current_rate
                    data.low = data.current_rate
                    return
            else:
                df = mkt.forex(data.symbol).ohlcv(interval="1D", length=self.period_ta)
            
            if df is not None and len(df) > 0:
                last = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
                
                # Debug: print columns
                # print(f"Forex columns: {list(df.columns)}")
                # print(f"Last row: {last.to_dict()}")
                
                # Extract OHLC - forex data might have different column structure
                # Common patterns: ['time', 'open', 'high', 'low', 'close'] or ['close']
                close_col = None
                for col in ['close', 'Close', 'ClosePrice', 'price']:
                    if col in df.columns:
                        close_col = col
                        break
                
                if close_col is None and len(df.columns) > 0:
                    # Try last column as close
                    close_col = df.columns[-1]
                
                if close_col:
                    data.current_rate = float(last.get(close_col, 0))
                    data.open_price = float(last.get('open', last.get('Open', data.current_rate)))
                    data.high = float(last.get('high', last.get('High', data.current_rate)))
                    data.low = float(last.get('low', last.get('Low', data.current_rate)))
                    
                    # Calculate change
                    prev_close = float(prev.get(close_col, data.current_rate))
                    if prev_close > 0 and prev_close != data.current_rate:
                        data.change_value = data.current_rate - prev_close
                        data.change_percent = round(data.change_value / prev_close * 100, 4)
                
                # Set unit
                base = data.symbol[:3]
                quote = data.symbol[3:] if len(data.symbol) > 3 else ""
                data.unit = f"{quote}/{base}" if quote else ""
                        
        except Exception as e:
            print(f"[ForexAnalyzer] Error: {e}")
            # Use reasonable defaults
            data.current_rate = 1.0
            data.open_price = 1.0
            data.high = 1.0
            data.low = 1.0
    
    def _determine_status(self, data: ForexData):
        """Determine technical status"""
        # For most forex pairs, small changes are normal
        if data.change_percent >= 0.1:
            data.trend = "UPTREND"
        elif data.change_percent <= -0.1:
            data.trend = "DOWNTREND"
        else:
            data.trend = "SIDEWAYS"
        
        if data.change_percent >= 0.3:
            data.technical_status = "STRONG BULLISH"
        elif data.change_percent <= -0.3:
            data.technical_status = "STRONG BEARISH"
        elif data.change_percent >= 0.1:
            data.technical_status = "BULLISH"
        elif data.change_percent <= -0.1:
            data.technical_status = "BEARISH"
        else:
            data.technical_status = "NEUTRAL"
    
    def format_output(self, data: ForexData) -> str:
        """Format analysis output"""
        change_emoji = "🟢" if data.change_percent >= 0 else "🔴"
        
        output = f"""
╔══════════════════════════════════════════════════════════════╗
║  💱 FOREX ANALYSIS: {data.symbol} ({data.name})
║  Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M')}
╠══════════════════════════════════════════════════════════════╣
║  💹 TỶ GIÁ: {data.current_rate:,.5f} {data.unit}
║  {change_emoji} Thay đổi: {data.change_value:+,.5f} ({data.change_percent:+.4f}%)
║  Cao/Thấp: {data.high:,.5f} / {data.low:,.5f}
║  Open: {data.open_price:,.5f}
╠══════════════════════════════════════════════════════════════╣
║  📈 XU HƯỚNG: {data.trend}
║  📊 TÌNH TRẠNG: {data.technical_status}
╠══════════════════════════════════════════════════════════════╣
║  🤖 ĐÁNH GIÁ: {self._get_recommendation(data)}
╚══════════════════════════════════════════════════════════════╝
"""
        return output
    
    def _get_recommendation(self, data: ForexData) -> str:
        """Get trading recommendation"""
        score = 50
        
        if data.trend == "UPTREND":
            score += 10
        elif data.trend == "DOWNTREND":
            score -= 10
        
        # Volatility check
        if data.high > 0 and data.low > 0:
            daily_range = (data.high - data.low) / data.current_rate * 100
            if daily_range > 1:
                score -= 10  # High volatility
        
        if score >= 60:
            return "TÍCH CỰC - Có thể mua"
        elif score >= 40:
            return "TRUNG LẬP - Chờ xác nhận"
        else:
            return "THẬN TRỌNG - Có thể bán"
