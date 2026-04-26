"""
Index Analyzer Module - Phase 2
Phân tích chỉ số thị trường (VNIndex, VN30, HNX...)
"""
from dataclasses import dataclass
from typing import Optional, List, Dict
import pandas as pd
from datetime import datetime


@dataclass
class IndexData:
    """Data structure for index information"""
    symbol: str
    name: str
    current_value: float = 0.0
    change_percent: float = 0.0
    change_value: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: int = 0
    market_breadth: Dict[str, int] = None  # {advance: N, decline: M}
    breadth_percent: float = 0.0  # % cổ phiếu tăng
    technical_status: str = "NEUTRAL"  # BULL, BEAR, NEUTRAL
    trend: str = "SIDEWAYS"
    # Technical indicators
    sma_20: float = 0.0
    sma_50: float = 0.0
    adx: float = 0.0
    rsi: float = 0.0
    # Recommendation
    master_score: int = 50
    recommendation: str = "NEUTRAL"


@dataclass
class MarketBreadth:
    """Market breadth data"""
    advance: int = 0  # Số cổ phiếu tăng
    decline: int = 0  # Số cổ phiếu giảm
    unchanged: int = 0  # Số cổ phiếu đứng giá
    total: int = 0
    percent_up: float = 0.0
    a_d_ratio: float = 0.0  # Advance/Decline ratio


class IndexAnalyzer:
    """Analyzer for market indices and breadth"""
    
    def __init__(self, period_ta: int = 60):
        self.period_ta = period_ta
    
    def analyze(self, symbol: str = "VNINDEX") -> IndexData:
        """
        Analyze an index with technical indicators and market breadth
        
        Args:
            symbol: Index symbol (VNINDEX, VN30, HNXIndex, etc.)
        """
        data = IndexData(symbol=symbol, name=self._get_index_name(symbol))
        
        # Get index OHLCV data
        df = self._get_index_ohlcv(symbol)
        if df is not None and len(df) > 0:
            self._extract_index_info(data, df)
            self._calculate_index_indicators(data, df)
        
        # Get market breadth
        breadth = self._get_market_breadth(symbol)
        if breadth:
            data.market_breadth = {
                "advance": breadth.advance,
                "decline": breadth.decline,
                "unchanged": breadth.unchanged
            }
            data.breadth_percent = breadth.percent_up
        
        # Determine technical status
        self._determine_technical_status(data)
        
        return data
    
    def _get_index_name(self, symbol: str) -> str:
        """Get human-readable index name"""
        names = {
            "VNINDEX": "VN-Index",
            "VN30": "VN30",
            "HNXIndex": "HNX Index",
            "HNX30": "HNX30",
            "UPCOM": "UPCOM Index",
            "VNALL": "VN-All",
            "VN100": "VN100",
            "VNMid": "VN-Mid Cap",
            "VNSmall": "VN-Small Cap",
            "VN50": "VN50",
        }
        return names.get(symbol, symbol)
    
    def _get_index_ohlcv(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch index OHLCV data"""
        try:
            from vnstock_data import Market
            mkt = Market()
            
            end = pd.Timestamp.today().strftime("%Y-%m-%d")
            start = (pd.Timestamp.today() - pd.DateOffset(days=self.period_ta)).strftime("%Y-%m-%d")
            
            df = mkt.index(symbol).ohlcv(start=start, end=end)
            
            if df is not None and len(df) > 0:
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Note: Index values are NOT divided by 1000 like stock prices
                # Keep as-is (actual index points)
                
                if 'time' in df.columns:
                    df.set_index('time', inplace=True)
                
                return df
            
            return None
        except Exception as e:
            print(f"[IndexAnalyzer] Error fetching {symbol}: {e}")
            return None
    
    def _extract_index_info(self, data: IndexData, df: pd.DataFrame):
        """Extract current index information"""
        if len(df) > 0:
            last = df.iloc[-1]
            
            # Current values (index points, not prices)
            data.current_value = float(last.get('close', 0))
            data.high = float(last.get('high', 0))
            data.low = float(last.get('low', 0))
            data.volume = int(last.get('volume', 0)) if pd.notna(last.get('volume')) else 0
            
            # Change calculation
            if len(df) > 1:
                prev_close = float(df.iloc[-2].get('close', 0))
                if prev_close > 0:
                    data.change_value = data.current_value - prev_close
                    data.change_percent = round((data.change_value / prev_close) * 100, 2)
    
    def _calculate_index_indicators(self, data: IndexData, df: pd.DataFrame):
        """Calculate technical indicators for index"""
        if df is None or len(df) < 20:
            return
        
        close = df['close'].dropna()
        
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
        
        # ADX (simplified calculation)
        if len(df) >= 14:
            high = df['high'].dropna()
            low = df['low'].dropna()
            if len(high) >= 14 and len(low) >= 14:
                # True Range
                tr1 = high - low
                tr2 = abs(high - close.shift(1))
                tr3 = abs(low - close.shift(1))
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                
                # Directional Movement
                plus_dm = high.diff()
                minus_dm = -low.diff()
                plus_dm[plus_dm < 0] = 0
                minus_dm[minus_dm < 0] = 0
                
                # Smoothed values
                atr = tr.rolling(14).mean()
                plus_di = 100 * (plus_dm.rolling(14).mean() / atr)
                minus_di = 100 * (minus_dm.rolling(14).mean() / atr)
                
                dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
                data.adx = float(dx.rolling(14).mean().iloc[-1])
        
        # Determine trend based on ADX and price position
        if len(close) >= 50:
            if data.current_value > data.sma_50 and data.adx > 20:
                data.trend = "UPTREND"
            elif data.current_value < data.sma_50 and data.adx > 20:
                data.trend = "DOWNTREND"
            else:
                data.trend = "SIDEWAYS"
    
    def _get_market_breadth(self, symbol: str) -> Optional[MarketBreadth]:
        """
        Calculate market breadth for an index
        
        Market breadth shows how many stocks are advancing vs declining
        """
        try:
            from vnstock_data import Market, Listing
            
            breadth = MarketBreadth()
            
            # Get list of stocks in the index
            lst = Listing(source='VCI')
            
            try:
                if symbol == "VNINDEX":
                    # All HOSE stocks
                    stocks = lst.symbols_by_exchange(exchange='HOSE')
                elif symbol == "VN30":
                    stocks = lst.symbols_by_group(group="VN30")
                elif symbol == "HNXIndex":
                    stocks = lst.symbols_by_exchange(exchange='HNX')
                elif symbol == "UPCOM":
                    stocks = lst.symbols_by_exchange(exchange='UPCOM')
                else:
                    # Try to get constituents
                    stocks = lst.symbols_by_group(group=symbol)
            except Exception:
                # Fallback to VNINDEX
                stocks = lst.symbols_by_exchange(exchange='HOSE')
            
            if stocks is None or len(stocks) == 0:
                return breadth
            
            # Get symbols list - handle both Series and DataFrame
            if isinstance(stocks, pd.Series):
                symbols = stocks.tolist()
            elif isinstance(stocks, pd.DataFrame):
                if 'symbol' in stocks.columns:
                    symbols = stocks['symbol'].tolist()
                else:
                    symbols = stocks.iloc[:, 0].tolist()
            else:
                symbols = list(stocks) if stocks else []
            
            # Limit to 100 for performance
            symbols = symbols[:100]
            
            # Get quotes for all symbols (batch call)
            mkt = Market()
            quotes = mkt.quote(symbols)
            
            if quotes is None or len(quotes) == 0:
                return breadth
            
            # Calculate breadth
            for _, row in quotes.iterrows():
                # Try different column names for price
                close = 0
                ref = 0
                
                for close_col in ['close_price', 'close', 'price']:
                    if close_col in row.index:
                        val = row.get(close_col, 0)
                        if pd.notna(val) and val != 0:
                            close = float(val) * 1000  # Scale back
                            break
                
                for ref_col in ['reference_price', 'ref', 'reference']:
                    if ref_col in row.index:
                        val = row.get(ref_col, 0)
                        if pd.notna(val) and val != 0:
                            ref = float(val) * 1000  # Scale back
                            break
                
                if close > ref:
                    breadth.advance += 1
                elif close < ref:
                    breadth.decline += 1
                else:
                    breadth.unchanged += 1
            
            breadth.total = breadth.advance + breadth.decline + breadth.unchanged
            if breadth.total > 0:
                breadth.percent_up = round(breadth.advance / breadth.total * 100, 1)
            if breadth.decline > 0:
                breadth.a_d_ratio = round(breadth.advance / breadth.decline, 2)
            
            return breadth
            
        except Exception as e:
            print(f"[IndexAnalyzer] Error calculating breadth: {e}")
            return None
    
    def _determine_technical_status(self, data: IndexData):
        """Determine overall technical status"""
        # Based on change percent and trend
        if data.change_percent >= 1.0:
            data.technical_status = "BULL"
        elif data.change_percent <= -1.0:
            data.technical_status = "BEAR"
        else:
            data.technical_status = "NEUTRAL"
    
    def get_index_list(self) -> pd.DataFrame:
        """Get list of available indices"""
        try:
            from vnstock_data import Listing
            
            lst = Listing()
            return lst.all_indices()
        except Exception as e:
            print(f"[IndexAnalyzer] Error getting index list: {e}")
            return pd.DataFrame()
    
    def format_output(self, data: IndexData) -> str:
        """Format analysis output as readable string - Full version"""
        change_emoji = "🟢" if data.change_percent >= 0 else "🔴"
        status_emoji = {
            "BULL": "🟢",
            "BEAR": "🔴",
            "NEUTRAL": "🟡"
        }.get(data.technical_status, "🟡")
        
        # RSI zone
        if data.rsi > 70:
            rsi_zone = "QUÁ MUA"
        elif data.rsi < 30:
            rsi_zone = "QUÁ BÁN"
        else:
            rsi_zone = "TRUNG LẬP"
        
        # ADX strength
        if data.adx > 40:
            adx_status = "RẤT MẠNH"
        elif data.adx > 25:
            adx_status = "MẠNH"
        elif data.adx > 20:
            adx_status = "YẾU"
        else:
            adx_status = "SIDEWAY"
        
        # Breadth assessment
        if data.breadth_percent >= 60:
            breadth_status = "TĂNG MẠNH"
        elif data.breadth_percent >= 50:
            breadth_status = "TĂNG NHẸ"
        elif data.breadth_percent >= 40:
            breadth_status = "GIẢM NHẸ"
        else:
            breadth_status = "GIẢM MẠNH"
        
        # Volume formatting
        vol_str = f"{data.volume:,}" if data.volume < 1000000 else f"{data.volume/1000000:.1f}M"
        
        output = f"""
╔══════════════════════════════════════════════════════════════╗
║  📊 CHỈ SỐ THỊ TRƯỜNG            | THỜI GIAN: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ║
╠══════════════════════════════════════════════════════════════╣
║  💹 {data.symbol} - {data.name}
║  ────────────────────────────────────────────────────────────
║  Giá: {data.current_value:,.2f} điểm
║  {change_emoji} Thay đổi: {data.change_percent:+.2f}% ({data.change_value:+,.2f} điểm)
║  Cao/Thấp: {data.high:,.2f} / {data.low:,.2f}
║  Khối lượng: {vol_str}
╠══════════════════════════════════════════════════════════════╣
║  📈 PHÂN TÍCH KỸ THUẬT
║  ────────────────────────────────────────────────────────────
║  📐 XU HƯỚNG
║     SMA(20): {data.sma_20:,.2f} | SMA(50): {data.sma_50:,.2f}
║     Giá: {data.current_value:,.2f} - """
        
        # Price vs SMA position
        if data.current_value > data.sma_20 and data.current_value > data.sma_50:
            output += "Giá TRÊN cả 2 SMA → Uptrend"
        elif data.current_value < data.sma_20 and data.current_value < data.sma_50:
            output += "Giá DƯỚI cả 2 SMA → Downtrend"
        elif data.current_value > data.sma_20:
            output += "Giá TRÊN SMA20 → Ngưỡng kháng cự"
        elif data.current_value < data.sma_20:
            output += "Giá DƯỚI SMA20 → Cần theo dõi"
        else:
            output += "Giá gần SMA → Sideway"
        
        output += f"""
║  📊 ADX: {data.adx:.1f} - Xu hướng {adx_status}
║  📉 RSI(14): {data.rsi:.1f} - Zone: {rsi_zone}
╠══════════════════════════════════════════════════════════════╣
║  📊 MARKET BREADTH (Sức khỏe thị trường)
║  ────────────────────────────────────────────────────────────"""
        
        if data.market_breadth:
            advance = data.market_breadth.get('advance', 0)
            decline = data.market_breadth.get('decline', 0)
            unchanged = data.market_breadth.get('unchanged', 0)
            ratio = advance / decline if decline > 0 else 0
            
            output += f"""
║  Advance/Decline: {advance} ↑ / {decline} ↓ / {unchanged} ─
║  Tỷ lệ: {ratio:.1f}:1 ({breadth_status})
║  Tỷ lệ tăng: {data.breadth_percent:.1f}%"""
        
        output += f"""
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
    
    def _generate_insights(self, data: IndexData) -> List[str]:
        """Generate market insights based on data"""
        insights = []
        
        # Trend insight
        if data.trend == "UPTREND":
            insights.append("✅ Giá đang trên SMA50 → Uptrend được xác nhận")
        elif data.trend == "DOWNTREND":
            insights.append("⚠️ Giá đang dưới SMA50 → Downtrend")
        else:
            insights.append("🔄 Giá sideway quanh SMA → Chờ xác nhận")
        
        # ADX insight
        if data.adx > 25:
            insights.append(f"✅ ADX {data.adx:.1f} > 25 → Xu hướng có độ tin cậy")
        else:
            insights.append(f"⚠️ ADX {data.adx:.1f} < 25 → Xu hướng yếu, sideway")
        
        # RSI insight
        if data.rsi > 70:
            insights.append(f"⚠️ RSI {data.rsi:.1f} > 70 → Quá mua, có thể điều chỉnh")
        elif data.rsi < 30:
            insights.append(f"✅ RSI {data.rsi:.1f} < 30 → Quá bán, có thể rebound")
        else:
            insights.append(f"ℹ️ RSI {data.rsi:.1f} → Trung lập, chờ tín hiệu")
        
        # Breadth insight
        if data.breadth_percent >= 55:
            insights.append(f"✅ Breadth {data.breadth_percent:.1f}% → Đa số cổ phiếu tăng")
        elif data.breadth_percent <= 45:
            insights.append(f"⚠️ Breadth {data.breadth_percent:.1f}% → Đa số cổ phiếu giảm")
        else:
            insights.append(f"ℹ️ Breadth {data.breadth_percent:.1f}% → Phân hóa")
        
        return insights
    
    def _get_recommendation(self, data: IndexData) -> str:
        """Get investment recommendation"""
        score = 50  # Base score
        
        # Trend adjustment
        if data.trend == "UPTREND":
            score += 20
        elif data.trend == "DOWNTREND":
            score -= 20
        
        # ADX adjustment
        if data.adx > 30:
            score += 10
        elif data.adx < 20:
            score -= 5
        
        # RSI adjustment
        if data.rsi > 70:
            score -= 10  # Overbought
        elif data.rsi < 30:
            score += 10  # Oversold
        
        # Breadth adjustment
        if data.breadth_percent > 55:
            score += 15
        elif data.breadth_percent < 45:
            score -= 15
        
        # Change percent
        if data.change_percent > 1:
            score += 10
        elif data.change_percent < -1:
            score -= 10
        
        # Cap score
        score = max(0, min(100, score))
        data.master_score = int(score)
        
        if score >= 75:
            return "TÍCH CỰC - Nên tham gia"
        elif score >= 55:
            return "KHẢ QUAN - Có thể mua"
        elif score >= 45:
            return "TRUNG LẬG - Chờ xác nhận"
        elif score >= 25:
            return "THẬN TRỌNG - Có thể bán"
        else:
            return "TIÊU CỰC - Không nên tham gia"


# Add attributes to IndexData
IndexData.sma_20 = 0.0
IndexData.sma_50 = 0.0
