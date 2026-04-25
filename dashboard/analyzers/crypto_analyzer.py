"""
Crypto Analyzer Module - Phase 4
Phân tích tiền mã hóa (BTC, ETH, etc.) qua Binance
"""
from dataclasses import dataclass
from typing import Optional
import pandas as pd
from datetime import datetime


@dataclass
class CryptoData:
    """Data structure for cryptocurrency information"""
    symbol: str = ""
    name: str = ""
    current_price: float = 0.0
    change_24h: float = 0.0
    change_percent_24h: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    open_price: float = 0.0
    volume_24h: float = 0.0
    trend: str = "NEUTRAL"
    technical_status: str = "NEUTRAL"


class CryptoAnalyzer:
    """Analyzer for cryptocurrencies (via Binance)"""
    
    def __init__(self, period_ta: int = 30):
        self.period_ta = period_ta
    
    def analyze(self, symbol: str = "BTCUSDT") -> CryptoData:
        """
        Analyze cryptocurrency
        
        Args:
            symbol: Crypto pair - "BTCUSDT", "ETHUSDT", etc.
        """
        data = CryptoData(symbol=symbol, name=self._get_name(symbol))
        
        self._get_crypto_data(data)
        self._determine_status(data)
        
        return data
    
    def _get_name(self, symbol: str) -> str:
        names = {
            "BTCUSDT": "Bitcoin (BTC)",
            "ETHUSDT": "Ethereum (ETH)",
            "BNBUSDT": "Binance Coin (BNB)",
            "SOLUSDT": "Solana (SOL)",
            "XRPUSDT": "Ripple (XRP)",
            "ADAUSDT": "Cardano (ADA)",
        }
        return names.get(symbol, symbol)
    
    def _get_crypto_data(self, data: CryptoData):
        """Get crypto data from Binance"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            
            # Get 24h quote stats
            quote = mkt.crypto(data.symbol).quote()
            
            if quote is not None and len(quote) > 0:
                row = quote.iloc[0]
                
                # Extract data from quote
                data.current_price = float(row.get('open_price', 0))
                data.high_24h = float(row.get('high_price', 0))
                data.low_24h = float(row.get('low_price', 0))
                
                # Estimate change from current vs low (as a proxy)
                if data.current_price > 0 and data.low_24h > 0:
                    data.open_price = data.current_price
                    
                # Try rolling stats for change percent
                try:
                    rolling = mkt.crypto(data.symbol).rolling_stats()
                    if rolling is not None and len(rolling) > 0:
                        r = rolling.iloc[0]
                        for col in r.index:
                            val = float(r[col]) if pd.notna(r[col]) else 0
                            col_lower = str(col).lower()
                            if 'percent' in col_lower and -100 <= val <= 100:
                                data.change_percent_24h = val
                except:
                    pass
                        
        except Exception as e:
            print(f"[CryptoAnalyzer] Error: {e}")
    
    def _determine_status(self, data: CryptoData):
        """Determine technical status"""
        change = data.change_percent_24h
        
        if change >= 3:
            data.trend = "STRONG UPTREND"
        elif change >= 1:
            data.trend = "UPTREND"
        elif change <= -3:
            data.trend = "STRONG DOWNTREND"
        elif change <= -1:
            data.trend = "DOWNTREND"
        else:
            data.trend = "SIDEWAYS"
        
        if change >= 5:
            data.technical_status = "VERY BULLISH"
        elif change >= 2:
            data.technical_status = "BULLISH"
        elif change <= -5:
            data.technical_status = "VERY BEARISH"
        elif change <= -2:
            data.technical_status = "BEARISH"
        else:
            data.technical_status = "NEUTRAL"
    
    def format_output(self, data: CryptoData) -> str:
        """Format analysis output"""
        change_emoji = "🟢" if data.change_percent_24h >= 0 else "🔴"
        
        # Format large numbers
        price_str = f"${data.current_price:,.2f}" if data.current_price < 1000 else f"${data.current_price:,.0f}"
        
        output = f"""
╔══════════════════════════════════════════════════════════════╗
║  🪙 CRYPTO ANALYSIS: {data.name}
║  Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M')}
╠══════════════════════════════════════════════════════════════╣
║  💰 GIÁ: {price_str}
║  {change_emoji} 24h: {data.change_percent_24h:+.2f}%
║  Cao/Thấp 24h: ${data.high_24h:,.2f} / ${data.low_24h:,.2f}
╠══════════════════════════════════════════════════════════════╣
║  📈 XU HƯỚNG: {data.trend}
║  📊 TÌNH TRẠNG: {data.technical_status}
╠══════════════════════════════════════════════════════════════╣
║  🤖 ĐÁNH GIÁ: {self._get_recommendation(data)}
╚══════════════════════════════════════════════════════════════╝
"""
        return output
    
    def _get_recommendation(self, data: CryptoData) -> str:
        """Get trading recommendation"""
        score = 50
        
        if data.trend.startswith("STRONG UP"):
            score += 20
        elif data.trend.startswith("UP"):
            score += 10
        elif data.trend.startswith("STRONG DOWN"):
            score -= 20
        elif data.trend.startswith("DOWN"):
            score -= 10
        
        if score >= 70:
            return "TÍCH CỰC - Có thể mua"
        elif score >= 45:
            return "TRUNG LẬP - Chờ xác nhận"
        elif score >= 30:
            return "THẬN TRỌNG - Có thể bán"
        else:
            return "TIÊU CỰC - Không nên tham gia"
