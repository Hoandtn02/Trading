"""
Fund Analyzer Module - Phase 4
Phân tích ETF và Quỹ đầu tư mở
"""
from dataclasses import dataclass
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
    top_holdings: List[dict] = None  # [{symbol, weight}]
    trend: str = "NEUTRAL"
    technical_status: str = "NEUTRAL"


class FundAnalyzer:
    """Analyzer for ETF and mutual funds"""
    
    def __init__(self, period_ta: int = 30):
        self.period_ta = period_ta
    
    def analyze(self, symbol: str = "E1VFVN30") -> FundData:
        """
        Analyze ETF or fund
        
        Args:
            symbol: Fund symbol - "E1VFVN30", "VFMVN30", etc.
        """
        data = FundData(symbol=symbol, name=self._get_name(symbol))
        
        # Try ETF first
        etf_data = self._get_etf_data(symbol)
        if etf_data:
            data.current_price = etf_data.get('price', 0)
            data.nav = etf_data.get('nav', data.current_price)
            data.nav_change = etf_data.get('change', 0)
            data.nav_change_percent = etf_data.get('change_pct', 0)
            data.volume = etf_data.get('volume', 0)
        else:
            # Try mutual fund
            fund_data = self._get_fund_data(symbol)
            if fund_data:
                data.nav = fund_data.get('nav', 0)
                data.nav_change = fund_data.get('change', 0)
                data.nav_change_percent = fund_data.get('change_pct', 0)
                data.top_holdings = fund_data.get('holdings', [])
        
        # Get 52w high/low
        self._get_52w_range(data)
        
        # Get top holdings
        self._get_top_holdings(data)
        
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
    
    def _get_etf_data(self, symbol: str) -> Optional[dict]:
        """Get ETF price data"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            df = mkt.etf(symbol).ohlcv(
                interval="1D",
                length=self.period_ta + 1
            )
            
            if df is not None and len(df) > 1:
                last = df.iloc[-1]
                prev = df.iloc[-2]
                
                current_price = float(last.get('close', 0)) * 1000  # Scale
                prev_price = float(prev.get('close', 0)) * 1000
                
                change = current_price - prev_price
                change_pct = round(change / prev_price * 100, 2) if prev_price > 0 else 0
                
                return {
                    'price': current_price,
                    'nav': current_price,  # ETF price ≈ NAV
                    'change': change,
                    'change_pct': change_pct,
                    'volume': int(last.get('volume', 0)) if pd.notna(last.get('volume')) else 0
                }
            
            return None
        except Exception as e:
            print(f"[FundAnalyzer] ETF error: {e}")
            return None
    
    def _get_fund_data(self, symbol: str) -> Optional[dict]:
        """Get mutual fund NAV data"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            df = mkt.fund(symbol).history(length=f"{self.period_ta}D")
            
            if df is not None and len(df) > 1:
                last = df.iloc[-1]
                prev = df.iloc[-2]
                
                # Find the nav value column
                nav_col = None
                for col in df.columns:
                    if 'nav' in col.lower() or 'close' in col.lower():
                        nav_col = col
                        break
                
                if nav_col:
                    nav = float(last.get(nav_col, 0))
                    prev_nav = float(prev.get(nav_col, 0))
                    
                    change = nav - prev_nav
                    change_pct = round(change / prev_nav * 100, 2) if prev_nav > 0 else 0
                    
                    return {
                        'nav': nav,
                        'change': change,
                        'change_pct': change_pct
                    }
            
            return None
        except Exception as e:
            print(f"[FundAnalyzer] Fund error: {e}")
            return None
    
    def _get_52w_range(self, data: FundData):
        """Get 52-week high/low"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            
            # Try ETF first
            try:
                df = mkt.etf(data.symbol).ohlcv(
                    start="2025-04-01",
                    end="2026-04-24"
                )
            except:
                df = mkt.fund(data.symbol).history(length="1Y")
            
            if df is not None and len(df) > 0:
                close_col = 'close' if 'close' in df.columns else df.columns[-1]
                prices = df[close_col].dropna() * 1000 if close_col == 'close' else df[close_col].dropna()
                
                if len(prices) > 0:
                    data.high_52w = float(prices.max())
                    data.low_52w = float(prices.min())
                    
        except Exception as e:
            print(f"[FundAnalyzer] 52w range error: {e}")
    
    def _get_top_holdings(self, data: FundData):
        """Get top holdings"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            holdings = mkt.fund(data.symbol).top_holding()
            
            if holdings is not None and len(holdings) > 0:
                data.top_holdings = []
                for _, row in holdings.head(5).iterrows():
                    data.top_holdings.append({
                        'symbol': str(row.iloc[0]) if len(row) > 0 else 'N/A',
                        'weight': float(row.iloc[1]) if len(row) > 1 else 0
                    })
                    
        except Exception as e:
            # ETF might not have holdings API
            data.top_holdings = []
    
    def _determine_status(self, data: FundData):
        """Determine technical status"""
        change = data.nav_change_percent
        
        if change >= 0.5:
            data.trend = "UPTREND"
        elif change <= -0.5:
            data.trend = "DOWNTREND"
        else:
            data.trend = "SIDEWAYS"
        
        if change >= 1.0:
            data.technical_status = "BULLISH"
        elif change <= -1.0:
            data.technical_status = "BEARISH"
        else:
            data.technical_status = "NEUTRAL"
    
    def format_output(self, data: FundData) -> str:
        """Format analysis output"""
        change_emoji = "🟢" if data.nav_change_percent >= 0 else "🔴"
        
        output = f"""
╔══════════════════════════════════════════════════════════════╗
║  📊 FUND ANALYSIS: {data.symbol} ({data.name})
║  Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M')}
╠══════════════════════════════════════════════════════════════╣
║  💰 NAV: {data.nav:,.2f}
║  {change_emoji} Thay đổi: {data.nav_change:+,.2f} ({data.nav_change_percent:+.2f}%)
║  Cao/Thấp 52w: {data.high_52w:,.2f} / {data.low_52w:,.2f}
║  Khối lượng: {data.volume:,}"""
        
        if data.top_holdings:
            output += """
╠══════════════════════════════════════════════════════════════╣
║  🏦 TOP HOLDINGS:"""
            for h in data.top_holdings[:5]:
                output += f"\n║     {h['symbol']}: {h['weight']:.1f}%"
        
        output += f"""
╠══════════════════════════════════════════════════════════════╣
║  📈 XU HƯỚNG: {data.trend}
║  📊 TÌNH TRẠNG: {data.technical_status}
╠══════════════════════════════════════════════════════════════╣
║  🤖 ĐÁNH GIÁ: {self._get_recommendation(data)}
╚══════════════════════════════════════════════════════════════╝
"""
        return output
    
    def _get_recommendation(self, data: FundData) -> str:
        """Get investment recommendation"""
        score = 50
        
        if data.trend == "UPTREND":
            score += 15
        elif data.trend == "DOWNTREND":
            score -= 15
        
        # Position in 52w range
        if data.high_52w > data.low_52w:
            position = (data.nav - data.low_52w) / (data.high_52w - data.low_52w) * 100
            if position > 80:
                score -= 10  # Near 52w high
            elif position < 20:
                score += 10  # Near 52w low
        
        if score >= 65:
            return "TÍCH CỰC - Có thể mua"
        elif score >= 45:
            return "TRUNG LẬP - Chờ xác nhận"
        else:
            return "THẬN TRỌNG - Có thể bán"


class ETFAnalyzer(FundAnalyzer):
    """Alias for ETFAnalyzer - same as FundAnalyzer"""
    pass
