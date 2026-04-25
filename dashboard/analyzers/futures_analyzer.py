"""
Futures Analyzer Module - Phase 3
Phân tích hợp đồng tương lai (VN30F)
"""
from dataclasses import dataclass
from typing import Optional
import pandas as pd
from datetime import datetime


@dataclass
class FuturesData:
    """Data structure for futures information"""
    symbol: str = ""
    name: str = ""
    current_price: float = 0.0  # Futures price
    spot_price: float = 0.0  # VN30 index price
    change_value: float = 0.0
    change_percent: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open_price: float = 0.0
    volume: int = 0
    basis: float = 0.0  # Chênh lệch với VN30
    trend: str = "NEUTRAL"
    technical_status: str = "NEUTRAL"
    rsi: float = 50.0
    adx: float = 25.0
    atr: float = 0.0
    recommendation: str = "WATCH"
    sma_20: float = 0.0
    sma_50: float = 0.0

    @property
    def futures_price(self):
        return self.current_price


class FuturesAnalyzer:
    """Analyzer for futures contracts (VN30F)"""
    
    def __init__(self, period_ta: int = 30):
        self.period_ta = period_ta
    
    def analyze(self, symbol: str = "VN30F") -> FuturesData:
        """
        Analyze futures contract
        
        Args:
            symbol: Contract symbol - "VN30F" for VN30 Futures
        """
        data = FuturesData(symbol=symbol, name=self._get_name(symbol))
        
        self._get_futures_data(data)
        self._calculate_basis(data)
        self._determine_status(data)
        
        return data
    
    def _get_name(self, symbol: str) -> str:
        names = {
            "VN30F": "VN30 Futures",
            "VN30F1M": "VN30 Futures - Tháng 1",
            "VN30F2M": "VN30 Futures - Tháng 2",
        }
        return names.get(symbol, symbol)
    
    def _get_futures_data(self, data: FuturesData):
        """Get futures OHLCV data"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            
            # VN30F - get current month contract
            # Try common contract codes
            for contract in ["VN30F1M", "VN30F", "VN30F2506"]:
                try:
                    # Use correct interval: 1D instead of 1d
                    df = mkt.futures(contract).ohlcv(
                        interval="1D",
                        length=self.period_ta
                    )
                    if df is not None and len(df) > 0:
                        data.symbol = contract
                        self._extract_data(data, df)
                        return
                except Exception as inner_e:
                    print(f"[FuturesAnalyzer] Try {contract} failed: {inner_e}")
                    continue
            
            # If no futures data, try index as proxy
            try:
                df = mkt.index("VN30").ohlcv(interval="1D", length=self.period_ta)
                if df is not None and len(df) > 0:
                    self._extract_data(data, df, is_index=True)
            except Exception as e:
                print(f"[FuturesAnalyzer] Index fallback failed: {e}")
                
        except Exception as e:
            print(f"[FuturesAnalyzer] Error: {e}")
    
    def _extract_data(self, data: FuturesData, df: pd.DataFrame, is_index: bool = False):
        """Extract data from OHLCV dataframe"""
        if len(df) > 0:
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last
            
            # Prices
            for col in ['close', 'Close']:
                if col in df.columns:
                    data.current_price = float(last.get(col, 0))
                    break
            
            data.open_price = float(last.get('open', data.current_price))
            data.high = float(last.get('high', data.current_price))
            data.low = float(last.get('low', data.current_price))
            
            # Volume
            vol_col = 'volume' if 'volume' in df.columns else 'Volume'
            if vol_col in df.columns:
                data.volume = int(last.get(vol_col, 0))
            
            # Change
            for col in ['close', 'Close']:
                if col in df.columns and col in prev.index:
                    prev_close = float(prev.get(col, 0))
                    if prev_close > 0:
                        data.change_value = data.current_price - prev_close
                        data.change_percent = round(data.change_value / prev_close * 100, 2)
    
    def _calculate_basis(self, data: FuturesData):
        """Calculate basis (difference between futures and underlying)"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            index_df = mkt.index("VN30").ohlcv(
                start="2026-04-23",
                end="2026-04-24"
            )
            
            if index_df is not None and len(index_df) > 0:
                # Get underlying index value from OHLCV
                index_value = float(index_df.iloc[-1].get('close', 0))
                
                if index_value > 0 and data.current_price > 0:
                    # Basis = Futures - Index
                    data.basis = data.current_price - index_value
                    
        except Exception as e:
            print(f"[FuturesAnalyzer] Basis calculation error: {e}")
    
    def _determine_status(self, data: FuturesData):
        """Determine technical status"""
        # Trend based on change
        if data.change_percent >= 0.5:
            data.trend = "UPTREND"
        elif data.change_percent <= -0.5:
            data.trend = "DOWNTREND"
        else:
            data.trend = "SIDEWAYS"
        
        # Status
        if data.change_percent >= 1.0:
            data.technical_status = "BULLISH"
        elif data.change_percent <= -1.0:
            data.technical_status = "BEARISH"
        else:
            data.technical_status = "NEUTRAL"
        
        # Basis interpretation
        if data.basis > 10:
            data.trend += " (Premium)"
        elif data.basis < -10:
            data.trend += " (Discount)"
    
    def format_output(self, data: FuturesData) -> str:
        """Format analysis output"""
        change_emoji = "🟢" if data.change_percent >= 0 else "🔴"
        
        output = f"""
╔══════════════════════════════════════════════════════════════╗
║  📊 FUTURES ANALYSIS: {data.symbol}
║  Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M')}
╠══════════════════════════════════════════════════════════════╣
║  💹 GIÁ HIỆN TẠI: {data.current_price:,.2f} điểm
║  {change_emoji} Thay đổi: {data.change_value:+,.2f} ({data.change_percent:+.2f}%)
║  Cao/Thấp: {data.high:,.2f} / {data.low:,.2f}
║  Open: {data.open_price:,.2f}
╠══════════════════════════════════════════════════════════════╣
║  📊 KHỐI LƯỢNG: {data.volume:,} hợp đồng
║  📐 BASIS: {data.basis:+,.2f} điểm
╠══════════════════════════════════════════════════════════════╣
║  📈 XU HƯỚNG: {data.trend}
║  📊 TÌNH TRẠNG: {data.technical_status}
╠══════════════════════════════════════════════════════════════╣
║  🤖 ĐÁNH GIÁ: {self._get_recommendation(data)}
╚══════════════════════════════════════════════════════════════╝
"""
        return output
    
    def _get_recommendation(self, data: FuturesData) -> str:
        """Get trading recommendation"""
        score = 50
        
        # Trend
        if data.trend.startswith("UP"):
            score += 15
        elif data.trend.startswith("DOWN"):
            score -= 15
        
        # Basis analysis
        if abs(data.basis) > 20:
            score -= 10  # High basis = risk
        
        # Volatility
        if abs(data.change_percent) > 1.5:
            score -= 5
        
        if score >= 65:
            return "TÍCH CỰC - Có thể LONG"
        elif score >= 45:
            return "TRUNG LẬG - Chờ xác nhận"
        else:
            return "THẬN TRỌNG - Có thể SHORT"
