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
    unit: str = "VND/chi"  # or USD/oz
    trend: str = "NEUTRAL"
    technical_status: str = "NEUTRAL"
    recommendation: str = "WATCH"
    master_score: int = 50
    
    # Technical indicators
    rsi: float = 50.0
    macd: float = 0.0
    macd_signal: float = 0.0
    adx: float = 25.0
    sma_20: float = 0.0
    sma_50: float = 0.0
    atr: float = 0.0
    
    # Bollinger Bands
    bollinger_upper: float = 0.0
    bollinger_lower: float = 0.0
    
    # Pivot Points
    pivot_r1: float = 0.0
    pivot_s1: float = 0.0
    
    # Premium/Discount (for gold_vn)
    premium: float = 0.0
    gold_spot: float = 0.0
    vnd_usd: float = 25500.0


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
        """Determine technical status - Enhanced with indicators"""
        # Calculate technical indicators
        self._calculate_indicators(data)
        
        # Trend based on price vs SMA
        if data.sma_20 > 0 and data.sma_50 > 0:
            if data.current_price > data.sma_20 and data.current_price > data.sma_50:
                data.trend = "UPTREND"
            elif data.current_price < data.sma_20 and data.current_price < data.sma_50:
                data.trend = "DOWNTREND"
            else:
                data.trend = "SIDEWAYS"
        
        # Overall status based on RSI and change
        if data.rsi > 70 or data.change_percent >= 1.0:
            data.technical_status = "BULLISH"
        elif data.rsi < 30 or data.change_percent <= -1.0:
            data.technical_status = "BEARISH"
        else:
            data.technical_status = "NEUTRAL"
    
    def _calculate_indicators(self, data: GoldData):
        """Calculate technical indicators for gold"""
        try:
            # Get price data based on symbol
            if data.symbol == "gold_vn":
                from vnstock_data import CommodityPrice
                commodity = CommodityPrice()
                df = commodity.gold_vn(length=f"{self.period_ta}D")
                price_col = 'sell'
            elif data.symbol == "gold_global":
                from vnstock_data import Market
                mkt = Market()
                df = mkt.commodity("XAUUSD").ohlcv(interval="1d", length=self.period_ta)
                price_col = 'close'
            else:
                return
            
            if df is None or len(df) < 20:
                return
            
            close = df[price_col].dropna()
            
            # SMA
            if len(close) >= 20:
                data.sma_20 = float(close.rolling(20).mean().iloc[-1])
            if len(close) >= 50:
                data.sma_50 = float(close.rolling(50).mean().iloc[-1])
            
            # RSI
            if len(close) >= 14:
                delta = close.diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                data.rsi = float(100 - (100 / (1 + rs)).iloc[-1])
            
            # MACD
            if len(close) >= 26:
                ema12 = close.ewm(span=12, adjust=False).mean()
                ema26 = close.ewm(span=26, adjust=False).mean()
                data.macd = float((ema12 - ema26).iloc[-1])
                data.macd_signal = float((data.macd - data.macd.ewm(span=9, adjust=False).mean().iloc[-1]) if hasattr(data.macd, 'ewm') else 0)
            
            # ATR
            if len(df) >= 14:
                high = df['high'] if 'high' in df.columns else df[price_col]
                low = df['low'] if 'low' in df.columns else df[price_col]
                close_arr = df[price_col]
                tr1 = high - low
                tr2 = abs(high - close_arr.shift(1))
                tr3 = abs(low - close_arr.shift(1))
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                data.atr = float(tr.rolling(14).mean().iloc[-1])
            
            # Bollinger Bands
            if len(close) >= 20:
                sma = close.rolling(20).mean()
                std = close.rolling(20).std()
                data.bollinger_upper = float((sma + 2 * std).iloc[-1])
                data.bollinger_lower = float((sma - 2 * std).iloc[-1])
            
            # Pivot Points
            if len(df) >= 2:
                high_p = float(df['high'].iloc[-1]) if 'high' in df.columns else data.high
                low_p = float(df['low'].iloc[-1]) if 'low' in df.columns else data.low
                close_p = float(df[price_col].iloc[-1])
                pivot = (high_p + low_p + close_p) / 3
                data.pivot_r1 = float(2 * pivot - low_p)
                data.pivot_s1 = float(2 * pivot - high_p)
            
            # Premium for gold_vn
            if data.symbol == "gold_vn" and data.current_price > 0:
                # Approximate: 1 oz = 37.5 chi, VND/USD ~ 25500
                gold_spot_usd = data.gold_spot if data.gold_spot > 0 else 2400  # default
                vnd_usd = data.vnd_usd
                converted = gold_spot_usd * 37.5 * vnd_usd
                data.premium = data.current_price - converted
                data.gold_spot = gold_spot_usd
                
        except Exception as e:
            print(f"[GoldAnalyzer] Error calculating indicators: {e}")
    
    def format_output(self, data: GoldData) -> str:
        """Format analysis output - Full version per spec"""
        change_emoji = "🟢" if data.change_percent >= 0 else "🔴"
        
        # RSI zone
        if data.rsi > 70:
            rsi_zone = "QUÁ MUA"
        elif data.rsi < 30:
            rsi_zone = "QUÁ BÁN"
        else:
            rsi_zone = "TRUNG LẬP"
        
        # RSI bar visualization
        rsi_pct = min(100, max(0, data.rsi * 2))
        rsi_bar = "█" * int(rsi_pct / 5) + "░" * (20 - int(rsi_pct / 5))
        
        # ADX strength
        if data.adx > 40:
            adx_status = "RẤT MẠNH"
        elif data.adx > 25:
            adx_status = "MẠNH"
        elif data.adx > 20:
            adx_status = "YẾU"
        else:
            adx_status = "SIDEWAY"
        
        # Bollinger position
        bollinger_pos = ""
        if data.bollinger_upper > 0 and data.bollinger_lower > 0:
            range_width = data.bollinger_upper - data.bollinger_lower
            if range_width > 0:
                position = (data.current_price - data.bollinger_lower) / range_width * 100
                bollinger_pos = f"vùng {position:.0f}%"
        
        output = f"""
╔══════════════════════════════════════════════════════════════╗
║  🥇 VÀNG SJC                | THỜI GIAN: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ║
╠══════════════════════════════════════════════════════════════╣
║  💰 GIÁ TRONG NƯỚC                                              │
║  ────────────────────────────────────────────────────────────"""
        
        if data.symbol == "gold_vn":
            spread = data.sell_price - data.buy_price
            spread_pct = (spread / data.buy_price * 100) if data.buy_price > 0 else 0
            output += f"""
║  Mua vào: {data.buy_price:,.0f} VND/lượng
║  Bán ra:  {data.sell_price:,.0f} VND/lượng
║  Spread:  {spread:,.0f} VND ({spread_pct:.2f}%)
║  {change_emoji} Thay đổi: {data.change_value:+,.0f} ({data.change_percent:+.2f}%)"""
            
            if data.premium != 0:
                premium_sign = "+" if data.premium > 0 else ""
                output += f"""
║  ────────────────────────────────────────────────────────────
║  Premium SJC vs TT: {premium_sign}{data.premium:,.0f} VND"""
        
        output += f"""
╠══════════════════════════════════════════════════════════════╣
║  📊 PHÂN TÍCH KỸ THUẬT (vnstock_ta)
║  ────────────────────────────────────────────────────────────
║  📈 ĐỘNG LƯỢNG
║     RSI(14): {data.rsi:.1f} {rsi_bar} Zone: {rsi_zone}
║     MACD: {data.macd:+.2f} (Signal: {'Bullish' if data.macd > 0 else 'Bearish'})
║  🎯 VÙNG GIÁ
║     Bollinger Upper: {data.bollinger_upper:,.0f} │ Lower: {data.bollinger_lower:,.0f}
║     Giá đang ở {bollinger_pos if bollinger_pos else 'giữa'}
║     Pivot R1: {data.pivot_r1:,.0f} │ S1: {data.pivot_s1:,.0f}
║  🔄 XU HƯỚNG
║     SMA(20): {data.sma_20:,.0f} │ SMA(50): {data.sma_50:,.0f}"""
        
        # Price vs SMA
        if data.sma_20 > 0 and data.sma_50 > 0:
            if data.current_price > data.sma_20 and data.current_price > data.sma_50:
                output += """
║     Giá đang TRÊN cả 2 SMA → Uptrend"""
            elif data.current_price < data.sma_20 and data.current_price < data.sma_50:
                output += """
║     Giá đang DƯỚI cả 2 SMA → Downtrend"""
            else:
                output += """
║     Giá sideway giữa 2 SMA"""
        
        output += f"""
║     ADX: {data.adx:.1f} - Xu hướng {adx_status}
║  📐 BIẾN ĐỘNG
║     ATR(14): {data.atr:,.0f} VND - BIẾN ĐỘNG {'CAO' if data.atr > data.current_price * 0.01 else 'TRUNG BÌNH'}
╠══════════════════════════════════════════════════════════════╣
║  🤖 AI INSIGHT: {self._get_recommendation(data)}
╠══════════════════════════════════════════════════════════════╣"""
        
        # Generate insights
        insights = self._generate_insights(data)
        for insight in insights:
            output += f"""
║  {insight}"""
        
        output += """
╚══════════════════════════════════════════════════════════════╝
"""
        return output
    
    def _generate_insights(self, data: GoldData) -> list:
        """Generate market insights"""
        insights = []
        
        # RSI insight
        if data.rsi > 70:
            insights.append("⚠️ RSI > 70 → QUÁ MUA, có nguy cơ điều chỉnh")
        elif data.rsi < 30:
            insights.append("✅ RSI < 30 → QUÁ BÁN, có thể rebound")
        else:
            insights.append(f"ℹ️ RSI {data.rsi:.1f} → Trung lập, chờ tín hiệu")
        
        # MACD insight
        if data.macd > 0:
            insights.append("✅ MACD dương → Đà tăng")
        else:
            insights.append("⚠️ MACD âm → Đà giảm")
        
        # Premium insight (for gold_vn)
        if data.symbol == "gold_vn" and data.premium != 0:
            if data.premium > 100000:
                insights.append(f"⚠️ Premium cao +{data.premium:,.0f} VND → SJC đắt hơn TT")
            elif data.premium < -100000:
                insights.append(f"✅ Premium thấp {data.premium:,.0f} VND → SJC rẻ hơn TT")
        
        # Bollinger insight
        if data.bollinger_upper > 0:
            if data.current_price >= data.bollinger_upper * 0.98:
                insights.append("⚠️ Giá gần Upper Band → Có thể quá mua")
            elif data.current_price <= data.bollinger_lower * 1.02:
                insights.append("✅ Giá gần Lower Band → Có thể quá bán")
        
        return insights
    
    def _get_recommendation(self, data: GoldData) -> str:
        """Get investment recommendation"""
        score = 50
        
        # Trend adjustment
        if data.trend == "UPTREND":
            score += 15
        elif data.trend == "DOWNTREND":
            score -= 15
        
        # ADX adjustment
        if data.adx > 25:
            score += 10
        elif data.adx < 20:
            score -= 5
        
        # RSI adjustment
        if data.rsi > 70:
            score -= 15  # Overbought
        elif data.rsi < 30:
            score += 15  # Oversold
        
        # Volatility (high change = high risk)
        if abs(data.change_percent) > 2:
            score -= 10
        
        # Cap score
        score = max(0, min(100, score))
        data.master_score = int(score)
        
        if score >= 70:
            return "TÍCH CỰC - Có thể mua"
        elif score >= 50:
            return "TRUNG LẬP - Chờ xác nhận"
        elif score >= 30:
            return "THẬN TRỌNG - Có thể bán"
        else:
            return "TIÊU CỰC - Không nên mua"
