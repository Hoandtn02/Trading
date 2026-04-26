"""
Fund Analyzer Module - Phase 4
Phân tích ETF và Quỹ đầu tư mở
"""
from dataclasses import dataclass, field
from typing import Optional, List
import pandas as pd
from datetime import datetime


@dataclass
class FundData:
    """Data structure for fund information"""
    symbol: str = ""
    name: str = ""
    nav: float = 0.0  # Net Asset Value
    nav_change: float = 0.0
    nav_change_percent: float = 0.0
    current_price: float = 0.0
    high_52w: float = 0.0
    low_52w: float = 0.0
    volume: int = 0
    # Premium/Discount
    premium_discount: float = 0.0
    # Performance
    return_1d: float = 0.0
    return_1w: float = 0.0
    return_1m: float = 0.0
    return_ytd: float = 0.0
    # Technical
    rsi: float = 50.0
    macd: float = 0.0
    sma_20: float = 0.0
    sma_50: float = 0.0
    adx: float = 0.0
    trend_status: str = "NEUTRAL"
    # Sentiment
    master_score: int = 50
    recommendation: str = "HOLD"
    top_holdings: List[dict] = field(default_factory=list)
    trend: str = "NEUTRAL"
    technical_status: str = "NEUTRAL"


class FundAnalyzer:
    """Analyzer for ETF and mutual funds"""
    
    def __init__(self, period_ta: int = 90):
        self.period_ta = period_ta
    
    def analyze(self, symbol: str = "E1VFVN30") -> FundData:
        """
        Analyze ETF or fund with full technical analysis
        """
        data = FundData(symbol=symbol, name=self._get_name(symbol))
        
        # Get OHLCV data
        self._get_etf_data(data)
        
        # Get performance metrics
        self._get_performance(data)
        
        # Get 52w high/low
        self._get_52w_range(data)
        
        # Calculate technical indicators
        self._calculate_technical(data)
        
        # Calculate master score
        self._calculate_master_score(data)
        
        self._determine_status(data)
        return data
    
    def _get_name(self, symbol: str) -> str:
        names = {
            "E1VFVN30": "SSIAM VNX50 ETF",
            "VFMVN30": "VFM VN30 ETF",
            "E1VFVN50": "SSIAM VN50 ETF",
            "VNFINLead": "VFM FINLead ETF",
        }
        return names.get(symbol, symbol)
    
    def _get_etf_data(self, data: FundData):
        """Get ETF price data"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            df = mkt.etf(data.symbol).ohlcv(
                interval="1D",
                length=self.period_ta + 1
            )
            
            if df is not None and len(df) > 1:
                last = df.iloc[-1]
                prev = df.iloc[-2]
                
                current_price = float(last.get('close', 0)) * 1000
                prev_price = float(prev.get('close', 0)) * 1000
                
                change = current_price - prev_price
                change_pct = round(change / prev_price * 100, 2) if prev_price > 0 else 0
                
                data.nav = current_price  # ETF price ≈ NAV
                data.nav_change = change
                data.nav_change_percent = change_pct
                data.current_price = current_price
                data.volume = int(last.get('volume', 0)) if pd.notna(last.get('volume')) else 0
                
        except ImportError:
            self._get_etf_data_fallback(data)
        except Exception as e:
            print(f"[FundAnalyzer] ETF error: {e}")
            self._get_etf_data_fallback(data)
    
    def _get_etf_data_fallback(self, data: FundData):
        """Fallback using vnstock (free library)"""
        try:
            from vnstock.explorer.kbs.trading import Trading
            trading = Trading(show_log=False)
            df = trading.price_board(symbols_list=[data.symbol], get_all=False)
            
            if df is not None and len(df) > 0:
                row = df.iloc[0]
                data.current_price = float(row.get('close', 0))
                data.nav = data.current_price
                data.nav_change = float(row.get('change', 0))
                data.nav_change_percent = float(row.get('pct_change', 0))
                data.volume = 0
        except Exception as e:
            print(f"[FundAnalyzer] ETF fallback error: {e}")
    
    def _get_performance(self, data: FundData):
        """Get performance metrics"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            df = mkt.etf(data.symbol).ohlcv(interval="1D", length=365)
            
            if df is not None and len(df) > 0:
                close_col = 'close'
                prices = df[close_col].dropna() * 1000
                
                if len(prices) > 1:
                    current = prices.iloc[-1]
                    
                    # 1D
                    if len(prices) > 1:
                        data.return_1d = round((current - prices.iloc[-2]) / prices.iloc[-2] * 100, 2)
                    # 1W
                    if len(prices) > 5:
                        data.return_1w = round((current - prices.iloc[-6]) / prices.iloc[-6] * 100, 2)
                    # 1M
                    if len(prices) > 20:
                        data.return_1m = round((current - prices.iloc[-21]) / prices.iloc[-21] * 100, 2)
                    # YTD
                    year_start = prices[prices.index >= f"{pd.Timestamp.now().year}-01-01"]
                    if len(year_start) > 0:
                        data.return_ytd = round((current - year_start.iloc[0]) / year_start.iloc[0] * 100, 2)
                        
        except Exception as e:
            print(f"[FundAnalyzer] Performance error: {e}")
    
    def _get_52w_range(self, data: FundData):
        """Get 52-week high/low"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            df = mkt.etf(data.symbol).ohlcv(
                start="2025-04-01",
                end=pd.Timestamp.today().strftime("%Y-%m-%d")
            )
            
            if df is not None and len(df) > 0:
                close_col = 'close'
                prices = df[close_col].dropna() * 1000
                
                if len(prices) > 0:
                    data.high_52w = float(prices.max())
                    data.low_52w = float(prices.min())
                    
        except Exception as e:
            print(f"[FundAnalyzer] 52w range error: {e}")
    
    def _calculate_technical(self, data: FundData):
        """Calculate technical indicators"""
        try:
            from vnstock_ta import Indicator
            
            from vnstock_data import Market
            mkt = Market()
            df = mkt.etf(data.symbol).ohlcv(interval="1D", length=self.period_ta + 30)
            
            if df is not None and len(df) > 50:
                close_col = 'close'
                prices = df[close_col].dropna()
                
                if len(prices) > 20:
                    indicator = Indicator(close=prices)
                    
                    # RSI
                    data.rsi = indicator.rsi(period=14)
                    if hasattr(data.rsi, 'iloc'):
                        data.rsi = float(data.rsi.iloc[-1])
                    
                    # MACD
                    macd_data = indicator.macd()
                    if macd_data is not None and hasattr(macd_data, 'iloc'):
                        data.macd = float(macd_data.iloc[-1])
                    
                    # SMA
                    sma_data = indicator.sma(period=20)
                    if sma_data is not None and hasattr(sma_data, 'iloc'):
                        data.sma_20 = float(sma_data.iloc[-1]) * 1000
                    
                    sma50_data = indicator.sma(period=50)
                    if sma50_data is not None and hasattr(sma50_data, 'iloc'):
                        data.sma_50 = float(sma50_data.iloc[-1]) * 1000
                    
                    # ADX
                    adx_data = indicator.adx(period=14)
                    if adx_data is not None and hasattr(adx_data, 'iloc'):
                        data.adx = float(adx_data.iloc[-1])
                        
        except Exception as e:
            print(f"[FundAnalyzer] Technical error: {e}")
    
    def _calculate_master_score(self, data: FundData):
        """Calculate master score"""
        score = 50
        
        # Trend scoring
        if data.nav > data.sma_20 and data.nav > data.sma_50:
            score += 15
        elif data.nav > data.sma_20:
            score += 7
        
        # ADX strength
        if data.adx > 25:
            score += 10
        elif data.adx > 20:
            score += 5
        
        # RSI zone
        if 40 <= data.rsi <= 60:
            score += 5
        elif data.rsi < 30:
            score += 10
        elif data.rsi > 70:
            score -= 5
        
        # 52w position
        if data.high_52w > data.low_52w:
            position = (data.nav - data.low_52w) / (data.high_52w - data.low_52w) * 100
            if position < 30:
                score += 10  # Near 52w low - potential
            elif position > 80:
                score -= 5   # Near 52w high
        
        data.master_score = max(0, min(100, score))
        
        if data.master_score >= 65:
            data.recommendation = "MUA (BUY)"
        elif data.master_score >= 45:
            data.recommendation = "NẮM GIỮ (HOLD)"
        else:
            data.recommendation = "BÁN (SELL)"
    
    def _determine_status(self, data: FundData):
        """Determine technical status"""
        change = data.nav_change_percent
        
        if data.nav > data.sma_20 and data.nav > data.sma_50:
            data.trend = "UPTREND"
        elif data.nav < data.sma_20 and data.nav < data.sma_50:
            data.trend = "DOWNTREND"
        else:
            data.trend = "SIDEWAYS"
        
        if change >= 1.0:
            data.trend_status = "BULLISH"
        elif change <= -1.0:
            data.trend_status = "BEARISH"
        else:
            data.trend_status = "NEUTRAL"
        
        if data.rsi > 70:
            data.technical_status = "OVERBOUGHT"
        elif data.rsi < 30:
            data.technical_status = "OVERSOLD"
        else:
            data.technical_status = "NEUTRAL"
    
    def format_output(self, data: FundData) -> str:
        """Format analysis output matching ARCHITECTURE_ROADMAP.md"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        change_emoji = "🟢" if data.nav_change_percent >= 0 else "🔴"
        
        # RSI bar
        rsi_bar = self._make_bar(data.rsi, 100, 20)
        rsi_zone = "QUÁ MUA" if data.rsi > 70 else "QUÁ BÁN" if data.rsi < 30 else "TRUNG LẬP"
        if data.rsi > 70:
            rsi_zone = "QUÁ MUA"
        elif data.rsi < 30:
            rsi_zone = "QUÁ BÁN"
        elif data.rsi > 55:
            rsi_zone = "TÍCH CỰC"
        elif data.rsi < 45:
            rsi_zone = "TIÊU CỰC"
        else:
            rsi_zone = "TRUNG LẬP"
        
        # MACD signal
        macd_signal = "TĂNG" if data.macd > 0 else "GIẢM"
        
        # Trend direction
        trend_direction = "TRÊN" if data.nav > data.sma_20 else "DƯỚI"
        
        # Master score stars
        stars = "★" * (data.master_score // 20) + "☆" * (5 - data.master_score // 20)
        
        # Recommendation text
        if data.recommendation == "MUA (BUY)":
            rec_emoji = "🟢"
            rec_text = "MUA"
        elif data.recommendation == "BÁN (SELL)":
            rec_emoji = "🔴"
            rec_text = "BÁN"
        else:
            rec_emoji = "🟡"
            rec_text = "NẮM GIỮ"
        
        # Calculate position in 52w
        position_52w = 0
        if data.high_52w > data.low_52w and data.nav > 0:
            position_52w = (data.nav - data.low_52w) / (data.high_52w - data.low_52w) * 100
        
        # Position 52w display
        if data.high_52w > 0 and data.low_52w > 0:
            pos_52w_text = f"({position_52w:.0f}% từ đáy)"
        else:
            pos_52w_text = "(N/A)"
        
        output = f"""
┌──────────────────────────────────────────────────────────────────┐
│  📊 {data.symbol.upper()} - {data.name}      THỜI GIAN: {now} │
├──────────────────────────────────────────────────────────────────┤
│  💰 THÔNG TIN CƠ BẢN                                           │
│  ────────────────────────────────────────────────────────────    │
│  NAV/CCQ: {data.nav:,.0f} VND                                          │
│  Giá thị trường: {data.current_price:,.0f} VND ({change_emoji}{data.nav_change_percent:+.2f}%)                 │
│  Premium/Discount: {data.premium_discount:+.2f}% ({'Giá > NAV' if data.premium_discount > 0 else 'Giá < NAV'})                      │
│  ────────────────────────────────────────────────────────────    │
│  Tổng tài sản (AUM): ~{data.nav * data.volume / 1e9:.0f} tỷ VND                        │
├──────────────────────────────────────────────────────────────────┤
│  📊 SO SÁNH VỚI CHỈ SỐ VN30                                    │
│  ────────────────────────────────────────────────────────────    │
│  VN30 Index: --- (+---%)                                       │
│  {data.symbol} NAV: {data.nav:,.0f} ({change_emoji}{data.nav_change_percent:+.2f}%)                               │
│  Cao/Thấp 52w: {data.high_52w:,.0f} / {data.low_52w:,.0f} {pos_52w_text}             │
│  ────────────────────────────────────────────────────────────    │
│  📈 HIỆU SUẤT                                                 │
│  ────────────────────────────────────────────────────────────    │
│  1D: {change_emoji}{data.return_1d:+.1f}% │ 1W: {data.return_1w:+.1f}% │ 1M: {data.return_1m:+.1f}% │ YTD: {data.return_ytd:+.1f}%        │
├──────────────────────────────────────────────────────────────────┤
│  📊 PHÂN TÍCH KỸ THUẬT NAV (vnstock_ta)                       │
│  ────────────────────────────────────────────────────────────    │
│  📈 ĐỘNG LƯỢNG                                                  │
│     RSI(14) NAV: {data.rsi:.0f} {rsi_bar} Zone: {rsi_zone}        │
│     MACD NAV: {data.macd:+.0f} (Signal: {macd_signal})                 │
│  🔄 XU HƯỚNG                                                    │
│     SMA(20): {data.sma_20:,.0f} │ SMA(50): {data.sma_50:,.0f} │ NAV: {data.nav:,.0f}          │
│     NAV đang {trend_direction} SMA20/50 → {data.trend}                      │
│     ADX: {data.adx:.0f} - Xu hướng {data.trend}                              │
├──────────────────────────────────────────────────────────────────┤
│  🤖 AI INSIGHT: {rec_text}                                       │
│  ────────────────────────────────────────────────────────────    │
│  Master Score: {data.master_score}/100 {stars}                                    │
│  ────────────────────────────────────────────────────────────    │
│  ✅ ƯU ĐIỂM:                                                   │
│     • NAV {trend_direction} SMA20/50 - {data.trend}                             │
│     • ADX {data.adx:.0f} - Xu hướng {'mạnh' if data.adx > 25 else 'trung bình'}                               │
│     • RSI {data.rsi:.0f} - Vùng {rsi_zone.lower()}                                │
│  ⚠️ RỦI RO:                                                    │
│     • Premium/Discount {data.premium_discount:+.2f}% - {'Thanh khoản tốt' if abs(data.premium_discount) < 0.5 else 'Cần theo dõi'}                │
│     • {position_52w:.0f}% từ đáy 52w - {'Gần đáy' if position_52w < 30 else 'Gần đỉnh' if position_52w > 70 else 'Giữa vùng'}                             │
│  ────────────────────────────────────────────────────────────    │
│  📌 HÀNH ĐỘNG:                                                  │
│     • {rec_text}: Phù hợp cho người muốn đầu tư an toàn      │
│     • Mục tiêu NAV: {data.high_52w:,.0f} {f'(+{(data.high_52w - data.nav) / data.nav * 100:.1f}%)' if data.nav > 0 and data.high_52w > 0 else ''}                              │
│     • 🛑 Cắt lỗ NAV: {data.low_52w:,.0f} {f'(-{(data.nav - data.low_52w) / data.nav * 100:.1f}%)' if data.nav > 0 and data.low_52w > 0 else ''}                          │
│     • ⏰ Timeframe: DÀI HẠN (6-12 tháng)                     │
└──────────────────────────────────────────────────────────────────┘
"""
        return output
    
    def _make_bar(self, value: float, max_val: float, width: int = 20) -> str:
        """Create a visual bar"""
        filled = int((value / max_val) * width)
        bar = "█" * filled + "░" * (width - filled)
        return bar


class ETFAnalyzer(FundAnalyzer):
    """Alias for ETFAnalyzer - same as FundAnalyzer"""
    pass
