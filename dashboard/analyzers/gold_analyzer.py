"""
Gold Analyzer Module - Phase 3
Phân tích vàng (Vàng SJC, vàng thế giới, dầu thô)
"""
from dataclasses import dataclass
from typing import Optional, Dict
import pandas as pd
from datetime import datetime


@dataclass
class GoldData:
    """Data structure for gold information"""
    symbol: str = ""
    name: str = ""
    current_price: float = 0.0
    buy_price: float = 0.0
    sell_price: float = 0.0
    change_value: float = 0.0
    change_percent: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open_price: float = 0.0
    unit: str = "VND/chỉ"  # or USD/oz
    trend: str = "NEUTRAL"
    technical_status: str = "NEUTRAL"


class GoldAnalyzer:
    """Analyzer for gold and precious metals"""
    
    def __init__(self, period_ta: int = 30):
        self.period_ta = period_ta
    
    def analyze(self, symbol: str = "gold_vn") -> GoldData:
        """
        Analyze gold with prices and technical indicators
        
        Args:
            symbol: Type of gold - "gold_vn", "gold_global", "oil_crude"
        """
        data = GoldData(symbol=symbol, name=self._get_name(symbol))
        
        if symbol == "gold_vn":
            self._analyze_gold_vn(data)
        elif symbol == "gold_global":
            self._analyze_gold_global(data)
        elif symbol == "oil_crude":
            self._analyze_oil_crude(data)
        else:
            self._analyze_gold_vn(data)
        
        self._determine_status(data)
        return data
    
    def _get_name(self, symbol: str) -> str:
        names = {
            "gold_vn": "Vàng SJC Việt Nam",
            "gold_global": "Vàng Thế Giới (XAU/USD)",
            "oil_crude": "Dầu Thô WTI",
        }
        return names.get(symbol, symbol)
    
    def _analyze_gold_vn(self, data: GoldData):
        """Analyze Vietnam gold (SJC)"""
        try:
            from vnstock_data import CommodityPrice
            
            commodity = CommodityPrice()
            df = commodity.gold_vn(length=f"{self.period_ta}D")
            
            if df is not None and len(df) > 0:
                last = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else last
                
                # Prices are already in VND
                data.buy_price = float(last.get('buy', 0))
                data.sell_price = float(last.get('sell', 0))
                data.current_price = data.sell_price  # Use sell as current
                
                # Change
                if pd.notna(prev.get('sell')):
                    data.change_value = data.sell_price - float(prev['sell'])
                    if float(prev['sell']) > 0:
                        data.change_percent = round(data.change_value / float(prev['sell']) * 100, 2)
                
                # High/Low
                if 'sell' in df.columns:
                    data.high = float(df['sell'].max())
                    data.low = float(df['sell'].min())
                
                data.unit = "VND/chỉ"
                
        except Exception as e:
            print(f"[GoldAnalyzer] Error analyzing gold VN: {e}")
    
    def _analyze_gold_global(self, data: GoldData):
        """Analyze global gold (XAU/USD)"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            # Gold in USD/oz via Dukascopy
            df = mkt.commodity("XAUUSD").ohlcv(interval="1d", length=self.period_ta)
            
            if df is not None and len(df) > 0:
                last = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else last
                
                data.current_price = float(last.get('close', 0))
                data.open_price = float(last.get('open', 0))
                data.high = float(last.get('high', 0))
                data.low = float(last.get('low', 0))
                
                # Change
                if pd.notna(prev.get('close')):
                    prev_close = float(prev['close'])
                    data.change_value = data.current_price - prev_close
                    if prev_close > 0:
                        data.change_percent = round(data.change_value / prev_close * 100, 2)
                
                data.unit = "USD/oz"
                
        except Exception as e:
            print(f"[GoldAnalyzer] Error analyzing gold global: {e}")
    
    def _analyze_oil_crude(self, data: GoldData):
        """Analyze crude oil"""
        try:
            from vnstock_data import CommodityPrice
            
            commodity = CommodityPrice()
            df = commodity.oil_crude(length=f"{self.period_ta}D")
            
            if df is not None and len(df) > 0:
                last = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else last
                
                data.current_price = float(last.get('close', 0))
                data.open_price = float(last.get('open', 0))
                data.high = float(last.get('high', 0))
                data.low = float(last.get('low', 0))
                
                # Change
                if pd.notna(prev.get('close')):
                    prev_close = float(prev['close'])
                    data.change_value = data.current_price - prev_close
                    if prev_close > 0:
                        data.change_percent = round(data.change_value / prev_close * 100, 2)
                
                data.unit = "USD/barrel"
                
        except Exception as e:
            print(f"[GoldAnalyzer] Error analyzing oil: {e}")
    
    def _determine_status(self, data: GoldData):
        """Determine technical status"""
        # Trend based on change percent
        if data.change_percent >= 0.5:
            data.trend = "UPTREND"
        elif data.change_percent <= -0.5:
            data.trend = "DOWNTREND"
        else:
            data.trend = "SIDEWAYS"
        
        # Overall status
        if data.change_percent >= 1.0:
            data.technical_status = "BULLISH"
        elif data.change_percent <= -1.0:
            data.technical_status = "BEARISH"
        else:
            data.technical_status = "NEUTRAL"
    
    def format_output(self, data: GoldData) -> str:
        """Format analysis output"""
        change_emoji = "🟢" if data.change_percent >= 0 else "🔴"
        
        output = f"""
╔══════════════════════════════════════════════════════════════╗
║  🥇 GOLD ANALYSIS: {data.name}
║  Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M')}
╠══════════════════════════════════════════════════════════════╣
║  💰 GIÁ HIỆN TẠI"""
        
        if data.symbol == "gold_vn":
            output += f"""
║     Giá mua: {data.buy_price:,.0f} {data.unit}
║     Giá bán: {data.sell_price:,.0f} {data.unit}
║     {change_emoji} Thay đổi: {data.change_value:+,.0f} ({data.change_percent:+.2f}%)
║     Cao/Thấp: {data.high:,.0f} / {data.low:,.0f}"""
        else:
            output += f"""
║     Giá: {data.current_price:,.2f} {data.unit}
║     {change_emoji} Thay đổi: {data.change_value:+,.2f} ({data.change_percent:+.2f}%)
║     Cao/Thấp: {data.high:,.2f} / {data.low:,.2f}
║     Open: {data.open_price:,.2f}"""
        
        output += f"""
╠══════════════════════════════════════════════════════════════╣
║  📈 XU HƯỚNG: {data.trend}
║  📊 TÌNH TRẠNG: {data.technical_status}
╠══════════════════════════════════════════════════════════════╣
║  🤖 ĐÁNH GIÁ: {self._get_recommendation(data)}
╚══════════════════════════════════════════════════════════════╝
"""
        return output
    
    def _get_recommendation(self, data: GoldData) -> str:
        """Get investment recommendation"""
        score = 50
        
        # Trend adjustment
        if data.trend == "UPTREND":
            score += 15
        elif data.trend == "DOWNTREND":
            score -= 15
        
        # Volatility (high change = high risk)
        if abs(data.change_percent) > 2:
            score -= 10
        
        if score >= 65:
            return "TÍCH CỰC - Có thể mua"
        elif score >= 45:
            return "TRUNG LẬP - Chờ xác nhận"
        else:
            return "THẬN TRỌNG - Có thể bán"
