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
        
        # Determine trend
        if len(close) >= 50:
            if data.current_value > data.sma_50:
                data.trend = "UPTREND"
            elif data.current_value < data.sma_50:
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
        """Format analysis output as readable string"""
        change_emoji = "🟢" if data.change_percent >= 0 else "🔴"
        status_emoji = {
            "BULL": "🟢",
            "BEAR": "🔴",
            "NEUTRAL": "🟡"
        }.get(data.technical_status, "🟡")
        
        output = f"""
╔══════════════════════════════════════════════════════════════╗
║  📊 INDEX ANALYSIS: {data.symbol} ({data.name})
║  Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M')}
╠══════════════════════════════════════════════════════════════╣
║  CHỈ SỐ: {data.current_value:,.2f} điểm
║  {change_emoji} Thay đổi: {data.change_value:+,.2f} ({data.change_percent:+.2f}%)
║  Cao/Thấp: {data.high:,.2f} / {data.low:,.2f}
╠══════════════════════════════════════════════════════════════╣
║  📈 XU HƯỚNG: {data.trend}
║  {status_emoji} Tình trạng: {data.technical_status}
╠══════════════════════════════════════════════════════════════╣"""
        
        # Market Breadth
        if data.market_breadth:
            output += f"""
║  📊 MARKET BREADTH
║  ────────────────────────────────────────────────────────────
║     Tăng: {data.market_breadth.get('advance', 0)} | Giảm: {data.market_breadth.get('decline', 0)} | Đứng: {data.market_breadth.get('unchanged', 0)}
║     Tỷ lệ tăng: {data.breadth_percent:.1f}%
╠══════════════════════════════════════════════════════════════╣"""
        
        output += f"""
║  🤖 ĐÁNH GIÁ: {self._get_recommendation(data)}
╚══════════════════════════════════════════════════════════════╝
"""
        return output
    
    def _get_recommendation(self, data: IndexData) -> str:
        """Get investment recommendation"""
        score = 50  # Base score
        
        # Trend adjustment
        if data.trend == "UPTREND":
            score += 20
        elif data.trend == "DOWNTREND":
            score -= 20
        
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
        
        if score >= 75:
            return "TÍCH CỰC - Nên tham gia"
        elif score >= 55:
            return "KHẢ QUAN - Có thể mua"
        elif score >= 45:
            return "TRUNG LẬP - Chờ xác nhận"
        elif score >= 25:
            return "THẬN TRỌNG - Có thể bán"
        else:
            return "TIÊU CỰC - Không nên tham gia"


# Add attributes to IndexData
IndexData.sma_20 = 0.0
IndexData.sma_50 = 0.0
