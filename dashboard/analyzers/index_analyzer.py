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
    avg_volume_20: int = 0  # Average volume 20 days
    market_breadth: Dict[str, int] = None  # {advance: N, decline: M}
    breadth_percent: float = 0.0  # % cổ phiếu tăng
    # Money flow (tỷ đồng)
    advance_value: float = 0.0  # Tổng giá trị nhóm tăng
    decline_value: float = 0.0  # Tổng giá trị nhóm giảm
    technical_status: str = "NEUTRAL"  # BULL, BEAR, NEUTRAL
    trend: str = "SIDEWAYS"
    # Technical indicators
    sma_20: float = 0.0
    sma_50: float = 0.0
    sma_50_available: bool = False  # Flag để check dữ liệu đủ 50 phiên
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
    advance_value: float = 0.0  # Tổng giá trị nhóm tăng (triệu VND)
    decline_value: float = 0.0  # Tổng giá trị nhóm giảm (triệu VND)


class IndexAnalyzer:
    """Analyzer for market indices and breadth"""
    
    def __init__(self, period_ta: int = 60):
        self.period_ta = period_ta
        self._breadth_scope_note = "subset"
    
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
            data.advance_value = breadth.advance_value
            data.decline_value = breadth.decline_value
        
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
            # Need ~70 trading days for SMA50, get 90 calendar days to be safe
            start = (pd.Timestamp.today() - pd.DateOffset(days=90)).strftime("%Y-%m-%d")
            
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
            data.sma_50_available = True
        
        # Average Volume 20 days
        if 'volume' in df.columns and len(df) >= 20:
            data.avg_volume_20 = int(df['volume'].tail(20).mean())
        
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
        # CHỈ xác định xu hướng khi đủ dữ liệu SMA50
        if not data.sma_50_available:
            data.trend = "ĐANG TÍNH TOÁN"  # Chưa đủ 50 phiên
        elif data.adx < 20:
            data.trend = "SIDEWAY"  # Không có xu hướng rõ ràng
        elif data.current_value > data.sma_50 and data.current_value > data.sma_20:
            data.trend = "UPTREND"
        elif data.current_value < data.sma_50 and data.current_value < data.sma_20:
            data.trend = "DOWNTREND"
        else:
            data.trend = "SIDEWAY"
    
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
            
            # NOTE: KBS/VCI API typically returns VN100 constituents
            # We'll note this limitation
            is_vn100_limited = True
            
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
            
            # Store note about scope (dynamic based on actual count)
            self._breadth_scope_note = f"{len(symbols)} mã (VN100/Index subset)"
            
            # Limit to 100 for performance
            symbols = symbols[:100]
            
            # Update note after limiting
            self._breadth_scope_note = f"~{len(symbols)} mã (VN100/Index subset)"
            
            # Get quotes for all symbols (batch call)
            mkt = Market()
            quotes = mkt.quote(symbols)
            
            if quotes is None or len(quotes) == 0:
                return breadth
            
            # Calculate breadth and money flow
            # volume col names: volume, trading_volume, volume_shares
            for _, row in quotes.iterrows():
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
                
                # Get volume
                vol = 0
                for vol_col in ['volume', 'trading_volume', 'volume_shares']:
                    if vol_col in row.index:
                        val = row.get(vol_col, 0)
                        if pd.notna(val):
                            vol = float(val)
                            break
                
                # Calculate money flow (price * volume in millions)
                # Volume is in shares, price in VND, convert to millions
                money_flow = (close * vol) / 1_000_000 if close > 0 and vol > 0 else 0
                
                if close > ref:
                    breadth.advance += 1
                    breadth.advance_value += money_flow
                elif close < ref:
                    breadth.decline += 1
                    breadth.decline_value += money_flow
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
        
        # SMA50 status - check both flag AND value to handle edge cases
        sma50_available = data.sma_50_available and data.sma_50 > 0
        sma50_str = f"{data.sma_50:,.2f}" if sma50_available else "N/A"
        
        # Volume comparison vs 20-day average
        vol_change_pct = 0
        vol_change_str = ""
        if data.avg_volume_20 > 0:
            vol_change_pct = ((data.volume - data.avg_volume_20) / data.avg_volume_20) * 100
            if vol_change_pct > 0:
                vol_change_str = f"(↑ {vol_change_pct:.0f}% so với TB 20 phiên)"
            else:
                vol_change_str = f"(↓ {abs(vol_change_pct):.0f}% so với TB 20 phiên)"
        
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
║  Khối lượng: {vol_str} {vol_change_str}
╠══════════════════════════════════════════════════════════════╣
║  📈 PHÂN TÍCH KỸ THUẬT
║  ────────────────────────────────────────────────────────────
║  📐 XU HƯỚNG
║     SMA(20): {data.sma_20:,.2f} | SMA(50): {sma50_str}
║     Giá: {data.current_value:,.2f} - """
        
        # Price vs SMA position - NHẤT QUÁN với trend logic
        if not sma50_available:
            output += "Chưa đủ dữ liệu SMA50 → Chờ xác nhận"
        elif data.adx < 20:
            output += "ADX < 20 → Sideway, không có xu hướng rõ"
        elif data.current_value > data.sma_20 and data.current_value > data.sma_50:
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
║  📊 MARKET BREADTH ({self._breadth_scope_note})
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
            
            # Money Flow Distribution
            if data.advance_value > 0 or data.decline_value > 0:
                adv_val_str = f"{data.advance_value/1000:.1f}T" if data.advance_value > 1000 else f"{data.advance_value:.0f}M"
                dec_val_str = f"{data.decline_value/1000:.1f}T" if data.decline_value > 1000 else f"{data.decline_value:.0f}M"
                output += f"""
║  💰 DÒNG TIỀN:
║     Tăng: {adv_val_str} | Giảm: {dec_val_str}"""
                if data.decline_value > data.advance_value * 1.5:
                    output += " → Áp lực bán mạnh hơn thực tế"
        
        # Calculate Master Score first to display it
        self._get_recommendation(data)
        
        # Get recommendation and override info
        recommendation = self._get_recommendation(data)
        has_override = hasattr(data, '_override_reason') and data._override_reason
        is_pillar_drag = hasattr(data, '_is_pillar_drag') and data._is_pillar_drag
        
        # Calculate decline percent
        decline_percent = 100 - data.breadth_percent
        
        # Build the enhanced AI Insight section
        star = "*" * int(data.master_score / 20)
        empty = "o" * int((100 - data.master_score) / 20)
        
        output += f"""
╠══════════════════════════════════════════════════════════════╣
║  AI INSIGHT: {data.master_score}/100 {star}{empty} 
║     Khuyến nghị: {recommendation}
╠══════════════════════════════════════════════════════════════╣"""
        
        # CRITICAL: Pillar Drag Warning Section
        if is_pillar_drag or has_override:
            output += """
║  ------------------------------------------------------------"""
            
            if is_pillar_drag:
                index_direction = "tăng nhẹ" if data.change_percent > 0 else "giảm nhẹ"
                output += f"""
║  [!] CẢNH BÁO: PHÁT HIỆN KÉO TRỤ (XANH VỎ ĐỎ LÒNG)
║  • {decline_percent:.0f}% cổ phiếu giảm/đi ngang dù Index {index_direction}.
║  • Phân kỳ nghiêm trọng: Trụ giữ giá - Midcap/Smallcap bị xả."""
            elif has_override:
                output += f"""
║  [!] CẢNH BÁO: {data._override_reason}"""
            
            output += """
║  ------------------------------------------------------------"""
            
            # Breadth risk
            if data.breadth_percent < 40:
                risk_level = "Rất thấp" if data.breadth_percent < 30 else "Thấp"
                output += f"""
║  [X] Rủi ro: Breadth {data.breadth_percent:.0f}% ({risk_level}) -> Độ tin cậy Uptrend thấp"""
            
            # RSI risk
            if data.rsi > 70:
                risk_desc = "Cực lớn" if data.rsi > 80 else "Lớn"
                output += f"""
║  [X] Rủi ro: RSI {data.rsi:.1f} (Quá mua) -> Áp lực điều chỉnh {risk_desc}"""
            
            # Volume risk
            vol_change_pct = 0
            if data.avg_volume_20 > 0:
                vol_change_pct = ((data.volume - data.avg_volume_20) / data.avg_volume_20) * 100
            if vol_change_pct < -10:
                output += f"""
║  [X] Rủi ro: Vol giảm {abs(vol_change_pct):.0f}% -> Lực cầu suy yếu ở vùng cao"""
            
            # Technical signals status
            if data.trend == "UPTREND" and data.adx > 25:
                output += """
║  [OK] Kỹ thuật: SMA & ADX vẫn báo tăng nhưng bị "vô hiệu hóa" """
            elif data.adx > 25:
                output += """
║  [OK] Kỹ thuật: ADX mạnh nhưng cần xác nhận từ Breadth"""
        
        output += """
╠══════════════════════════════════════════════════════════════╣"""
        
        # Generate insights (existing detailed insights)
        insights = self._generate_insights(data)
        for insight in insights:
            output += f"""
║  {insight}"""
        
        output += """
╚══════════════════════════════════════════════════════════════╝
"""
        return output
    
    def _generate_insights(self, data: IndexData) -> List[str]:
        """Generate market insights based on data - NHẤT QUÁN với trend logic"""
        insights = []
        
        # Check SMA50 availability
        sma50_available = data.sma_50_available and data.sma_50 > 0
        
        # Trend insight - NHẤT QUÁN với _calculate_index_indicators
        if not sma50_available:
            insights.append("⏳ SMA50 chưa đủ dữ liệu → Không xác định xu hướng")
        elif data.adx < 20:
            insights.append("⚠️ ADX < 20 → Không có xu hướng rõ ràng (Sideway)")
        elif data.trend == "UPTREND":
            insights.append("✅ Giá trên cả 2 SMA + ADX > 20 → Uptrend xác nhận")
        elif data.trend == "DOWNTREND":
            insights.append("⚠️ Giá dưới cả 2 SMA + ADX > 20 → Downtrend")
        else:
            insights.append("🔄 Giá sideway quanh SMA → Chờ xác nhận xu hướng")
        
        # ADX insight
        if data.adx > 40:
            insights.append(f"✅ ADX {data.adx:.1f} > 40 → Xu hướng RẤT MẠNH")
        elif data.adx > 25:
            insights.append(f"✅ ADX {data.adx:.1f} > 25 → Xu hướng đáng tin cậy")
        elif data.adx >= 20:
            insights.append(f"⚠️ ADX {data.adx:.1f} 20-25 → Xu hướng yếu")
        else:
            insights.append(f"⚠️ ADX {data.adx:.1f} < 20 → Sideway, không có xu hướng")
        
        # RSI insight
        if data.rsi > 70:
            insights.append(f"⚠️ RSI {data.rsi:.1f} > 70 → QUÁ MUA, có thể điều chỉnh")
        elif data.rsi < 30:
            insights.append(f"✅ RSI {data.rsi:.1f} < 30 → QUÁ BÁN, có thể rebound")
        else:
            insights.append(f"ℹ️ RSI {data.rsi:.1f} → Trung lập, chờ tín hiệu")
        
        # Breadth insight
        if data.breadth_percent >= 55:
            insights.append(f"✅ Breadth {data.breadth_percent:.1f}% → Đa số cổ phiếu tăng")
        elif data.breadth_percent <= 45:
            insights.append(f"⚠️ Breadth {data.breadth_percent:.1f}% → Đa số cổ phiếu giảm")
        else:
            insights.append(f"ℹ️ Breadth {data.breadth_percent:.1f}% → Phân hóa")
        
        # Volume insight - Weak demand at high prices
        vol_change_pct = 0
        if data.avg_volume_20 > 0:
            vol_change_pct = ((data.volume - data.avg_volume_20) / data.avg_volume_20) * 100
        
        if vol_change_pct < -10 and data.change_percent > 0 and data.rsi > 60:
            insights.append(f"⚠️ Vol giảm {abs(vol_change_pct):.0f}% ở vùng cao → Phân phối, cẩn trọng!")
        elif vol_change_pct < -15:
            insights.append(f"⚠️ Vol giảm {abs(vol_change_pct):.0f}% → Lực cầu yếu")
        elif vol_change_pct > 20:
            insights.append(f"✅ Vol tăng {vol_change_pct:.0f}% → Dòng tiền tham gia mạnh")
        
        return insights
    
    def _get_recommendation(self, data: IndexData) -> str:
        """
        Get investment recommendation based on weighted analysis.
        
        Scoring weights:
        - Trend (60%): Based on ADX and price position vs SMAs
        - Breadth (40%): Based on market breadth and RSI conditions
        """
        score = 50  # Base score
        
        # ========================================
        # TREND COMPONENT (60% weight)
        # ========================================
        
        # ADX strength (how reliable is the trend)
        trend_score = 0
        if data.adx >= 40:
            trend_score = 20  # Very strong trend
        elif data.adx >= 25:
            trend_score = 15  # Strong trend
        elif data.adx >= 20:
            trend_score = 10  # Weak trend
        else:
            trend_score = 0  # Sideway
        
        # Price position vs SMAs
        position_score = 0
        if data.sma_50_available and data.sma_50 > 0:
            if data.current_value > data.sma_20 and data.current_value > data.sma_50:
                position_score = 15  # Strong bullish position
            elif data.current_value > data.sma_20:
                position_score = 5  # Mild bullish
            elif data.current_value < data.sma_20 and data.current_value < data.sma_50:
                position_score = -15  # Strong bearish position
            elif data.current_value < data.sma_20:
                position_score = -5  # Mild bearish
        
        trend_component = (trend_score + position_score) * 0.6
        
        # ========================================
        # BREADTH COMPONENT (40% weight)
        # ========================================
        
        # RSI condition
        rsi_score = 0
        if data.rsi > 75:
            rsi_score = -20  # EXTREME overbought - danger zone
        elif data.rsi > 70:
            rsi_score = -10  # Overbought
        elif data.rsi < 30:
            rsi_score = 15  # Oversold - potential rebound
        elif data.rsi < 35:
            rsi_score = 5   # Near oversold
        
        # Breadth condition
        breadth_score = 0
        if data.breadth_percent >= 55:
            breadth_score = 20  # Most stocks rising
        elif data.breadth_percent >= 45:
            breadth_score = 5   # Mild bullish
        elif data.breadth_percent <= 25:
            breadth_score = -20  # EXTREME - most stocks falling
        elif data.breadth_percent <= 40:
            breadth_score = -10  # Bearish
        
        breadth_component = (rsi_score + breadth_score) * 0.4
        
        # ========================================
        # FINAL SCORE
        # ========================================
        
        score += trend_component + breadth_component
        
        # ========================================
        # CRITICAL OVERRIDE RULES
        # These MUST override the score when specific dangerous conditions exist
        # ========================================
        
        override_reason = None
        is_pillar_drag = False  # Flag for pillar dragging detection
        
        # ========================================
        # RULE 0: PILLAR DRAG DETECTION (KÉO TRỤ)
        # Index up/flt but Breadth < 35% = Dangerous
        # ========================================
        if data.breadth_percent < 35:
            if data.change_percent >= 0:
                # Index up/flating but most stocks down = PILLAR DRAG
                is_pillar_drag = True
                score = min(score, 30)  # Cap at 30
                override_reason = "⚠️ KÉO TRỤ: Index lên nhưng chỉ {0:.0f}% mã tăng".format(data.breadth_percent)
            elif data.change_percent > -1 and data.breadth_percent < 25:
                # Index flat/slight drop + very weak breadth = Warning
                is_pillar_drag = True
                score = min(score, 35)
                override_reason = "⚠️ KÉO TRỤ TIỀM ẨN: Chỉ {0:.0f}% mã tăng".format(data.breadth_percent)
        
        # Store pillar drag flag for insights
        data._is_pillar_drag = is_pillar_drag
        
        # ========================================
        # BUILD OVERRIDE REASON - Separate Breadth vs RSI concepts
        # ========================================
        
        override_parts = []  # List of warning parts
        
        # 1. Breadth warning (KÉO TRỤ)
        if is_pillar_drag:
            if data.change_percent >= 0:
                override_parts.append("Breadth yếu ({:.0f}%) - Sự đồng thuận thấp".format(data.breadth_percent))
            else:
                override_parts.append("Breadth yếu ({:.0f}%) - Kéo trụ tiềm ẩn".format(data.breadth_percent))
        
        # 2. RSI warning (Động lượng)
        if data.rsi > 80:
            override_parts.append("RSI Quá mua cực độ ({:.0f})".format(data.rsi))
        elif data.rsi > 75 and not is_pillar_drag:
            override_parts.append("RSI Quá mua ({:.0f})".format(data.rsi))
        
        # 3. Volume warning (Phân phối)
        vol_change_pct = 0
        if data.avg_volume_20 > 0:
            vol_change_pct = ((data.volume - data.avg_volume_20) / data.avg_volume_20) * 100
        
        if vol_change_pct < -10 and data.change_percent > 0 and data.rsi > 65:
            override_parts.append("Vol giảm ở vùng cao - Phân phối")
        
        # 4. Oversold potential
        if data.rsi < 25:
            override_parts.append("RSI Quá bán ({:.0f}) - Tiềm năng rebound".format(data.rsi))
        
        # Combine override parts
        if override_parts:
            override_reason = "⚠️ KÉO TRỤ: " + " | ".join(override_parts) if is_pillar_drag else "⚠️ CẢNH BÁO: " + " | ".join(override_parts)
        else:
            override_reason = None
        
        # ========================================
        # CRITICAL OVERRIDE RULES - Adjust scores based on conditions
        # ========================================
        
        # Rule 0: PILLAR DRAG - Already handled above with is_pillar_drag flag
        if is_pillar_drag:
            score = min(score, 30)  # Cap at 30 for pillar drag
        
        # Rule 1: RSI > 75 + Breadth < 40% = "Xanh vỏ đỏ lòng"
        if not is_pillar_drag and data.rsi > 75 and data.breadth_percent < 40:
            score = min(score, 40)  # Cap at 40 regardless of trend
        
        # Rule 2: RSI > 80 = Extreme overbought regardless of other factors
        if data.rsi > 80:
            score = min(score, 35)
        
        # Rule 3: Volume weakening at high prices
        if vol_change_pct < -10 and data.change_percent > 0 and data.rsi > 65:
            if not is_pillar_drag:
                score = min(score, 45)
        
        # Rule 4: RSI < 25 = Extreme oversold (potential rebound)
        if data.rsi < 25:
            score = max(score, 60)  # At least 60 for extreme oversold
        
        # Cap score
        score = max(0, min(100, score))
        data.master_score = int(score)
        
        # ========================================
        # RECOMMENDATION MAPPING
        # ========================================
        
        if score >= 75:
            return "TÍCH CỰC - Nên tham gia"
        elif score >= 60:
            return "KHẢ QUAN - Có thể mua nhẹ"
        elif score >= 50:
            return "TRUNG LẬP - Chờ xác nhận"
        elif score >= 40:
            return "THẬN TRỌNG - Chốt lời từng phần"
        elif score >= 25:
            return "TIÊU CỰC - Cắt lỗ hoặc chờ"
        else:
            return "NGUY HIỂM - Không nên tham gia"


# Add attributes to IndexData
IndexData.sma_20 = 0.0
IndexData.sma_50 = 0.0
IndexData.sma_50_available = False
IndexData.avg_volume_20 = 0
IndexData.advance_value = 0.0
IndexData.decline_value = 0.0

# Instance attribute for breadth scope note
IndexAnalyzer._breadth_scope_note = "subset"  # Will be set during analysis
