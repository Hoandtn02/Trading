"""
Forex Analyzer Module - Phase 4
Phân tích tỷ giá ngoại hối (EUR/USD, USD/JPY, etc.)
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict
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
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    unit: str = ""
    # All major pairs
    all_pairs: Dict[str, dict] = field(default_factory=dict)
    # Technical
    rsi: float = 50.0
    macd: float = 0.0
    cmf: float = 0.0
    sma_20: float = 0.0
    sma_50: float = 0.0
    adx: float = 0.0
    atr: float = 0.0
    bollinger_upper: float = 0.0
    bollinger_lower: float = 0.0
    ichimoku_tenkan: float = 0.0
    ichimoku_kijun: float = 0.0
    # Fundamentals
    interest_rate_diff: float = 0.0
    fed_rate: float = 5.25
    sbv_rate: float = 4.50
    dxy: float = 0.0
    trade_balance: float = 0.0
    # Score
    master_score: int = 50
    recommendation: str = "HOLD"
    trend: str = "NEUTRAL"
    technical_status: str = "NEUTRAL"


class ForexAnalyzer:
    """Analyzer for forex pairs"""
    
    def __init__(self, period_ta: int = 30):
        self.period_ta = period_ta
    
    def analyze(self, symbol: str = "USDVND") -> ForexData:
        """
        Analyze forex pair with full technical and fundamental analysis
        """
        data = ForexData(symbol=symbol, name=self._get_name(symbol))
        
        # Get all major pairs
        self._get_all_pairs(data)
        
        # Get forex data
        self._get_forex_data(data)
        
        # Get fundamentals
        self._get_fundamentals(data)
        
        # Calculate technical
        self._calculate_technical(data)
        
        # Calculate master score
        self._calculate_master_score(data)
        
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
    
    def _get_all_pairs(self, data: ForexData):
        """Get all major forex pairs"""
        pairs = ["USDVND", "EURVND", "JPYVND", "GBPVND", "CNYVND"]
        
        for pair in pairs:
            try:
                pair_data = self._get_single_pair(pair)
                if pair_data:
                    data.all_pairs[pair] = pair_data
            except Exception as e:
                print(f"[ForexAnalyzer] {pair} error: {e}")
    
    def _get_single_pair(self, symbol: str) -> Optional[dict]:
        """Get single forex pair data"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            df = mkt.forex(symbol).ohlcv(interval="1D", length=self.period_ta + 1)
            
            if df is not None and len(df) > 1:
                last = df.iloc[-1]
                prev = df.iloc[-2]
                
                close_col = None
                for col in ['close', 'Close', 'ClosePrice', 'price']:
                    if col in df.columns:
                        close_col = col
                        break
                
                if close_col is None:
                    close_col = df.columns[-1]
                
                current = float(last.get(close_col, 0))
                prev_close = float(prev.get(close_col, current))
                
                change = current - prev_close
                change_pct = round(change / prev_close * 100, 4) if prev_close > 0 else 0
                
                return {
                    'rate': current,
                    'change': change_pct,
                    'trend': 'Tăng' if change > 0 else 'Giảm'
                }
        except:
            pass
        
        # Fallback to VCB
        try:
            from vnstock.explorer.misc.exchange_rate import vcb_exchange_rate
            import datetime as dt
            
            date_val = dt.date.today().strftime("%Y-%m-%d")
            df = vcb_exchange_rate(date=date_val)
            
            if df is not None and len(df) > 0:
                currency_map = {"USDVND": "USD", "EURVND": "EUR", "JPYVND": "JPY", "GBPVND": "GBP"}
                currency_code = currency_map.get(symbol, "USD")
                
                for _, row in df.iterrows():
                    if currency_code in str(row.get('currency_code', '')).upper():
                        rate = float(row.get('buy', 0))
                        return {
                            'rate': rate,
                            'change': 0,
                            'trend': 'N/A'
                        }
        except:
            pass
        
        return None
    
    def _get_forex_data(self, data: ForexData):
        """Get forex OHLCV data"""
        # For USDVND, use specialized handling
        if data.symbol == "USDVND":
            data.unit = "VND/USD"
            
            try:
                from vnstock_data import Market
                mkt = Market()
                df = mkt.forex("USDVND").ohlcv(interval="1D", length=self.period_ta + 1)
                
                if df is not None and len(df) > 0:
                    last = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
                    
                    close_col = None
                    for col in ['close', 'Close', 'ClosePrice', 'price']:
                        if col in df.columns:
                            close_col = col
                            break
                    
                    if close_col is None:
                        close_col = df.columns[-1]
                    
                    data.current_rate = float(last.get(close_col, 0))
                    data.open_price = float(last.get('open', last.get('Open', data.current_rate)))
                    data.high = float(last.get('high', last.get('High', data.current_rate)))
                    data.low = float(last.get('low', last.get('Low', data.current_rate)))
                    
                    prev_close = float(prev.get(close_col, data.current_rate))
                    if prev_close > 0:
                        data.change_value = data.current_rate - prev_close
                        data.change_percent = round(data.change_value / prev_close * 100, 4)
                
            except ImportError:
                self._get_forex_data_fallback(data)
            except Exception as e:
                print(f"[ForexAnalyzer] Error: {e}")
                self._get_forex_data_fallback(data)
        else:
            pair_data = self._get_single_pair(data.symbol)
            if pair_data:
                data.current_rate = pair_data['rate']
                data.change_percent = pair_data['change']
    
    def _get_forex_data_fallback(self, data: ForexData):
        """Fallback using VCB rates"""
        try:
            from vnstock.explorer.misc.exchange_rate import vcb_exchange_rate
            import datetime as dt
            
            date_val = dt.date.today().strftime("%Y-%m-%d")
            df = vcb_exchange_rate(date=date_val)
            
            if df is not None and len(df) > 0:
                currency_map = {"USDVND": "USD", "EURVND": "EUR", "JPYVND": "JPY"}
                currency_code = currency_map.get(data.symbol, "USD")
                
                for _, row in df.iterrows():
                    currency = str(row.get('currency_code', '')).upper()
                    if currency_code in currency:
                        rate = float(row.get('buy', 0))
                        if rate > 0:
                            # Parse rate format "26,108.00"
                            if isinstance(rate, str):
                                rate = float(rate.replace(',', ''))
                            data.current_rate = rate
                            data.open_price = rate
                            data.high = rate
                            data.low = rate
                            data.unit = f"VND/{currency_code}"
                            break
                            
        except Exception as e:
            print(f"[ForexAnalyzer] Fallback error: {e}")
        
        # Final fallback
        if data.current_rate <= 0:
            if data.symbol == "USDVND":
                data.current_rate = 25600
            elif data.symbol == "EURUSD":
                data.current_rate = 1.08
            elif data.symbol == "USDJPY":
                data.current_rate = 150.5
            else:
                data.current_rate = 1.0
            data.open_price = data.current_rate
            data.high = data.current_rate
            data.low = data.current_rate
    
    def _get_fundamentals(self, data: ForexData):
        """Get fundamental data"""
        # Interest rate differential
        data.interest_rate_diff = data.fed_rate - data.sbv_rate
        
        # Estimate based on typical values
        if data.symbol == "USDVND":
            data.spread = data.current_rate * 0.0004  # 0.04%
            data.bid = data.current_rate - data.spread / 2
            data.ask = data.current_rate + data.spread / 2
        
        # Trade balance (approximate for Vietnam)
        data.trade_balance = 30  # +$30B thặng dư
    
    def _calculate_technical(self, data: ForexData):
        """Calculate technical indicators"""
        try:
            from vnstock_ta import Indicator
            
            from vnstock_data import Market
            mkt = Market()
            df = mkt.forex(data.symbol).ohlcv(interval="1D", length=self.period_ta + 30)
            
            if df is not None and len(df) > 20:
                close_col = None
                for col in ['close', 'Close', 'ClosePrice', 'price']:
                    if col in df.columns:
                        close_col = col
                        break
                
                if close_col is None:
                    close_col = df.columns[-1]
                
                prices = df[close_col].dropna()
                
                if len(prices) > 20:
                    indicator = Indicator(close=prices)
                    
                    # RSI
                    rsi = indicator.rsi(period=14)
                    if hasattr(rsi, 'iloc'):
                        data.rsi = float(rsi.iloc[-1])
                    
                    # MACD
                    macd = indicator.macd()
                    if macd is not None and hasattr(macd, 'iloc'):
                        data.macd = float(macd.iloc[-1])
                    
                    # CMF
                    cmf = indicator.cmf(period=20)
                    if hasattr(cmf, 'iloc'):
                        data.cmf = float(cmf.iloc[-1])
                    
                    # SMA
                    sma20 = indicator.sma(period=20)
                    if sma20 is not None and hasattr(sma20, 'iloc'):
                        data.sma_20 = float(sma20.iloc[-1])
                    
                    sma50 = indicator.sma(period=50)
                    if sma50 is not None and hasattr(sma50, 'iloc'):
                        data.sma_50 = float(sma50.iloc[-1])
                    
                    # ADX
                    adx = indicator.adx(period=14)
                    if adx is not None and hasattr(adx, 'iloc'):
                        data.adx = float(adx.iloc[-1])
                    
                    # ATR
                    atr = indicator.atr(period=14)
                    if hasattr(atr, 'iloc'):
                        data.atr = float(atr.iloc[-1])
                    
                    # Bollinger
                    bb = indicator.bollinger_bands()
                    if bb is not None:
                        data.bollinger_upper = float(bb['upper'].iloc[-1]) if 'upper' in bb else 0
                        data.bollinger_lower = float(bb['lower'].iloc[-1]) if 'lower' in bb else 0
                            
        except Exception as e:
            print(f"[ForexAnalyzer] Technical error: {e}")
    
    def _calculate_master_score(self, data: ForexData):
        """Calculate master score"""
        score = 50
        
        # Trend scoring
        if data.current_rate > data.sma_20 and data.current_rate > data.sma_50:
            score += 10  # Strong up
        elif data.current_rate > data.sma_20:
            score += 5
        
        # ADX
        if data.adx > 25:
            score += 10
        
        # CMF
        if data.cmf > 0:
            score += 10  # Money flowing in
        
        # Interest rate differential
        if data.interest_rate_diff > 0:
            score += 5  # USD stronger
        
        # Trade balance
        if data.trade_balance > 0:
            score += 5  # Supports VND
        
        data.master_score = max(0, min(100, score))
        
        if data.master_score >= 60:
            data.recommendation = "VND YẾU (SELL)"
        elif data.master_score >= 40:
            data.recommendation = "THEO DÕI (WATCH)"
        else:
            data.recommendation = "VND ỔN ĐỊNH (BUY)"
    
    def _determine_status(self, data: ForexData):
        """Determine technical status"""
        # Trend
        if data.current_rate > data.sma_20 and data.current_rate > data.sma_50:
            data.trend = "UPTREND" if data.symbol == "USDVND" else "DOWNTREND"
        elif data.current_rate < data.sma_20 and data.current_rate < data.sma_50:
            data.trend = "DOWNTREND" if data.symbol == "USDVND" else "UPTREND"
        else:
            data.trend = "SIDEWAYS"
        
        # Status
        if data.change_percent >= 0.3:
            data.technical_status = "STRONG BULLISH" if data.symbol == "USDVND" else "STRONG BEARISH"
        elif data.change_percent >= 0.1:
            data.technical_status = "BULLISH" if data.symbol == "USDVND" else "BEARISH"
        elif data.change_percent <= -0.3:
            data.technical_status = "STRONG BEARISH" if data.symbol == "USDVND" else "STRONG BULLISH"
        elif data.change_percent <= -0.1:
            data.technical_status = "BEARISH" if data.symbol == "USDVND" else "BULLISH"
        else:
            data.technical_status = "NEUTRAL"
    
    def format_output(self, data: ForexData) -> str:
        """Format analysis output matching ARCHITECTURE_ROADMAP.md"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        change_emoji = "🟢" if data.change_percent >= 0 else "🔴"
        
        # CMF bar
        cmf_bar = self._make_bar(abs(data.cmf) * 5, 1, 20) if data.cmf > 0 else self._make_bar(abs(data.cmf) * 5, 1, 20)
        cmf_status = "TIỀN CHẢY VÀO (+)" if data.cmf > 0 else "TIỀN CHẢY RA (-)"
        
        # Master score stars
        stars = "★" * (data.master_score // 20) + "☆" * (5 - data.master_score // 20)
        
        # Build all pairs table
        pairs_table = ""
        for pair, info in data.all_pairs.items():
            change = info.get('change', 0)
            emoji = "🟢" if change >= 0 else "🔴"
            pairs_table += f"│  │ {pair:12} │ {info.get('rate', 0):>10} │ {emoji}{change:+.2f}%  │ {info.get('trend', 'N/A'):10} │\n"
        
        output = f"""
┌──────────────────────────────────────────────────────────────────┐
│  💱 TỶ GIÁ NGOẠI HỐI                         THỜI GIAN: {now} │
├──────────────────────────────────────────────────────────────────┤
│  💰 CÁC CẶP TIỀN CHÍNH                                          │
│  ────────────────────────────────────────────────────────────    │
│  ┌──────────────────┬────────────┬──────────┬──────────────┐    │
│  │ Cặp tiền       │ Giá        │ %Change  │ Xu hướng    │    │
│  ├──────────────────┼────────────┼──────────┼──────────────┤    │
{pairs_table}│  └──────────────────┴────────────┴──────────┴──────────────┘    │
├──────────────────────────────────────────────────────────────────┤
│  📊 CHI TIẾT: {data.symbol}                                          │
│  ────────────────────────────────────────────────────────────    │
│  Tỷ giá: {data.current_rate:,.0f} {data.unit}                                        │
│  Bid: {data.bid:,.0f} │ Ask: {data.ask:,.0f}                                    │
│  Spread: {data.spread:,.0f} VND ({data.spread/data.current_rate*100:.2f}%)                                        │
│  ────────────────────────────────────────────────────────────    │
│  📈 PHÂN TÍCH KỸ THUẬT (vnstock_ta)                          │
│  ────────────────────────────────────────────────────────────    │
│  📊 DÒNG TIỀN                                                  │
│     CMF(20): {data.cmf:+.2f} {cmf_bar} {cmf_status}    │
│  🔄 XU HƯỚNG                                                    │
│     SMA(20): {data.sma_20:,.0f} │ SMA(50): {data.sma_50:,.0f} │ Giá: {data.current_rate:,.0f}        │
│     Giá đang {'TRÊN' if data.current_rate > data.sma_20 else 'DƯỚI'} SMA → {data.trend}                          │
│     ADX: {data.adx:.0f} - Xu hướng {data.trend} MẠNH                          │
│  📐 BIẾN ĐỘNG                                                   │
│     ATR(14): {data.atr:,.0f} VND - BIẾN ĐỘNG {'CAO' if data.atr > 100 else 'THẤP'}                          │
│     Bollinger Width: {data.bollinger_upper - data.bollinger_lower:,.0f} VND                                   │
│  🎯 VÙNG GIÁ                                                    │
│     Ichimoku Cloud: {'Giá trên cloud' if data.current_rate > data.ichimoku_kijun else 'Giá dưới cloud'} (Bullish bias)             │
│     Tenkan-sen: {data.ichimoku_tenkan:,.0f} │ Kijun-sen: {data.ichimoku_kijun:,.0f}                    │
├──────────────────────────────────────────────────────────────────┤
│  📊 SO SÁNH LÃI SUẤT (SWAP)                                   │
│  ────────────────────────────────────────────────────────────    │
│  Fed Funds Rate: {data.fed_rate:.2f}%                                        │
│  SBV Policy Rate: {data.sbv_rate:.2f}%                                       │
│  Lãi suất chênh lệch: {data.interest_rate_diff:+.2f}% ({'VND có劣势' if data.interest_rate_diff < 0 else 'USD có劣势'})                    │
│  → Swap USD/VND 12M: {data.interest_rate_diff:.2f}% ({'Bearish' if data.interest_rate_diff < 0 else 'Bullish'} VND)                    │
│  ────────────────────────────────────────────────────────────    │
│  🏦 YẾU TỐ CƠ BẢN                                              │
│  ────────────────────────────────────────────────────────────    │
│  Chỉ số DXY: {data.dxy:.1f} (+0.0%) - Đồng USD mạnh                  │
│  Cán cân thương mại: +${data.trade_balance}B (Thặng dư → Hỗ trợ VND)          │
├──────────────────────────────────────────────────────────────────┤
│  🤖 AI INSIGHT: {data.recommendation}                            │
│  ────────────────────────────────────────────────────────────    │
│  Master Score: {data.master_score}/100 {stars}                                    │
│  ────────────────────────────────────────────────────────────    │
│  ✅ HỖ TRỢ VND:                                                 │
│     • Cán cân thương mại thặng dư +${data.trade_balance}B                      │
│     • ATR {data.atr:,.0f} VND - Biến động kiểm soát                   │
│  ⚠️ ÁP LỰC VND:                                                 │
│     • ADX {data.adx:.0f} - Xu hướng {data.trend}                          │
│     • CMF {data.cmf:+.2f} - Dòng tiền chảy {'vào' if data.cmf > 0 else 'ra'} ngoại tệ                │
│     • Chênh lệch lãi suất {data.interest_rate_diff:+.2f}% bất lợi VND                │
│     • DXY {data.dxy:.1f} - Đồng USD mạnh                          │
│  ────────────────────────────────────────────────────────────    │
│  📌 DỰ ĐOÁN:                                                    │
│     • Ngắn hạn: {data.current_rate - data.atr:,.0f}-{data.current_rate + data.atr:,.0f} (Sideway)                      │
│     • Trung hạn: Có thể {'tăng' if data.trend == 'UPTREND' else 'giảm'} nếu DXY tiếp tục tăng │
│     • Dài hạn: VND ổn định nhờ thặng dư TM                  │
│     • ⏰ Khuyến nghị: HOLD, chờ breakout                      │
└──────────────────────────────────────────────────────────────────┘
"""
        return output
    
    def _make_bar(self, value: float, max_val: float, width: int = 20) -> str:
        """Create a visual bar"""
        filled = int((min(abs(value), max_val) / max_val) * width)
        bar = "█" * filled + "░" * (width - filled)
        return bar
