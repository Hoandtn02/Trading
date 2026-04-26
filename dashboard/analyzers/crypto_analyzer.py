"""
Crypto Analyzer Module - Phase 4
Phân tích tiền mã hóa (BTC, ETH, etc.) qua Yahoo Finance
"""
from dataclasses import dataclass, field
from typing import Optional, List
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
    market_cap: float = 0.0
    dominance: float = 0.0
    # Technical
    rsi: float = 50.0
    macd: float = 0.0
    macd_signal: float = 0.0
    cmf: float = 0.0
    sma_20: float = 0.0
    sma_50: float = 0.0
    sma_200: float = 0.0
    adx: float = 0.0
    bollinger_upper: float = 0.0
    bollinger_middle: float = 0.0
    bollinger_lower: float = 0.0
    vwap: float = 0.0
    # Sentiment
    fear_greed: int = 50
    funding_rate: float = 0.0
    open_interest: float = 0.0
    etf_flow: float = 0.0
    # Score
    master_score: int = 50
    recommendation: str = "HOLD"
    trend: str = "NEUTRAL"
    technical_status: str = "NEUTRAL"


class CryptoAnalyzer:
    """Analyzer for cryptocurrencies (via Yahoo Finance)"""
    
    def __init__(self, period_ta: int = 90):
        self.period_ta = period_ta
    
    def analyze(self, symbol: str = "BTCUSDT") -> CryptoData:
        """
        Analyze cryptocurrency with full technical analysis
        """
        data = CryptoData(symbol=symbol, name=self._get_name(symbol))
        
        self._get_crypto_data(data)
        self._get_historical_data(data)
        self._calculate_technical(data)
        self._calculate_master_score(data)
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
        """Get crypto data from Yahoo Finance"""
        try:
            import requests
            
            # Map symbol to Yahoo Finance format
            yf_map = {
                "BTCUSDT": "BTC-USD",
                "ETHUSDT": "ETH-USD",
                "BNBUSDT": "BNB-USD",
                "SOLUSDT": "SOL-USD",
                "XRPUSDT": "XRP-USD",
                "ADAUSDT": "ADA-USD",
            }
            yf_symbol = yf_map.get(data.symbol, f"{data.symbol.replace('USDT', '-USD')}")
            
            # Get current quote
            import time
            time.sleep(0.3)
            end = int(pd.Timestamp.now().timestamp())
            start = end - 86400
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, params={"period1": start, "period2": end, "interval": "1d"}, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                result = resp.json().get("chart", {}).get("result", [])
                if result:
                    meta = result[0].get("meta", {})
                    data.current_price = float(meta.get("regularMarketPrice", 0))
                    data.high_24h = float(meta.get("regularMarketDayHigh", 0))
                    data.low_24h = float(meta.get("regularMarketDayLow", 0))
                    data.open_price = float(meta.get("regularMarketOpen", 0))
                    data.volume_24h = float(meta.get("regularMarketVolume", 0))
                    data.market_cap = float(meta.get("marketCap", 0))
                    
                    # Calculate change
                    prev_close = float(meta.get("chartPreviousClose", data.current_price))
                    if prev_close > 0:
                        data.change_24h = data.current_price - prev_close
                        data.change_percent_24h = round((data.current_price - prev_close) / prev_close * 100, 2)
                            
        except Exception as e:
            print(f"[CryptoAnalyzer] Error: {e}")
            self._get_crypto_data_vnstock(data)
    
    def _get_crypto_data_vnstock(self, data: CryptoData):
        """Fallback using vnstock"""
        try:
            from vnstock_data import Market
            
            mkt = Market()
            quote = mkt.crypto(data.symbol).quote()
            
            if quote is not None and len(quote) > 0:
                row = quote.iloc[0]
                data.current_price = float(row.get('open_price', 0))
                data.high_24h = float(row.get('high_price', 0))
                data.low_24h = float(row.get('low_price', 0))
                        
        except Exception as e:
            print(f"[CryptoAnalyzer] VNStock error: {e}")
    
    def _get_historical_data(self, data: CryptoData):
        """Get historical data for technical analysis"""
        try:
            import requests
            
            yf_map = {
                "BTCUSDT": "BTC-USD",
                "ETHUSDT": "ETH-USD",
                "BNBUSDT": "BNB-USD",
                "SOLUSDT": "SOL-USD",
            }
            yf_symbol = yf_map.get(data.symbol, f"{data.symbol.replace('USDT', '-USD')}")
            
            import time
            time.sleep(0.3)
            end = int(pd.Timestamp.now().timestamp())
            start = end - (self.period_ta + 30) * 86400
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, params={"period1": start, "period2": end, "interval": "1d"}, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                result = resp.json().get("chart", {}).get("result", [])
                if result:
                    ohlc = result[0]["indicators"]["quote"][0]
                    timestamps = result[0]["timestamp"]
                    
                    df = pd.DataFrame({
                        "time": pd.to_datetime(timestamps, unit="s"),
                        "open": ohlc["open"],
                        "high": ohlc["high"],
                        "low": ohlc["low"],
                        "close": ohlc["close"],
                        "volume": ohlc["volume"]
                    })
                    df = df.dropna()
                    
                    if len(df) > 50:
                        data.ohlcv_data = df
                            
        except Exception as e:
            print(f"[CryptoAnalyzer] Historical data error: {e}")
    
    def _calculate_technical(self, data: CryptoData):
        """Calculate technical indicators"""
        if not hasattr(data, 'ohlcv_data') or data.ohlcv_data is None:
            return
        
        try:
            from vnstock_ta import Indicator
            
            df = data.ohlcv_data
            prices = df['close'].dropna()
            
            if len(prices) < 20:
                return
            
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
            
            sma200 = indicator.sma(period=200)
            if sma200 is not None and hasattr(sma200, 'iloc'):
                data.sma_200 = float(sma200.iloc[-1])
            
            # ADX
            adx = indicator.adx(period=14)
            if adx is not None and hasattr(adx, 'iloc'):
                data.adx = float(adx.iloc[-1])
            
            # Bollinger
            bb = indicator.bollinger_bands()
            if bb is not None:
                data.bollinger_upper = float(bb['upper'].iloc[-1]) if 'upper' in bb else 0
                data.bollinger_middle = float(bb['middle'].iloc[-1]) if 'middle' in bb else 0
                data.bollinger_lower = float(bb['lower'].iloc[-1]) if 'lower' in bb else 0
            
            # VWAP
            if len(df) > 0:
                typical = (df['high'] + df['low'] + df['close']) / 3
                data.vwap = float((typical * df['volume']).sum() / df['volume'].sum())
                        
        except Exception as e:
            print(f"[CryptoAnalyzer] Technical error: {e}")
    
    def _calculate_master_score(self, data: CryptoData):
        """Calculate master score"""
        score = 50
        
        # Trend scoring
        if data.current_price > data.sma_20 and data.current_price > data.sma_50 and data.current_price > data.sma_200:
            score += 15
        elif data.current_price > data.sma_20:
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
        
        # CMF
        if data.cmf > 0:
            score += 7
        elif data.cmf < 0:
            score -= 7
        
        data.master_score = max(0, min(100, score))
        
        if data.master_score >= 65:
            data.recommendation = "TIẾP TỤC NẮM GIỮ (HOLD)"
        elif data.master_score >= 45:
            data.recommendation = "THEO DÕI (WATCH)"
        else:
            data.recommendation = "BÁN (SELL)"
    
    def _determine_status(self, data: CryptoData):
        """Determine technical status"""
        # Trend
        if data.current_price > data.sma_20 and data.current_price > data.sma_50:
            data.trend = "UPTREND"
        elif data.current_price < data.sma_20 and data.current_price < data.sma_50:
            data.trend = "DOWNTREND"
        else:
            data.trend = "SIDEWAYS"
        
        # Technical status
        if data.rsi > 70:
            data.technical_status = "OVERBOUGHT"
        elif data.rsi < 30:
            data.technical_status = "OVERSOLD"
        else:
            data.technical_status = "NEUTRAL"
    
    def format_output(self, data: CryptoData) -> str:
        """Format analysis output matching ARCHITECTURE_ROADMAP.md"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        change_emoji = "🟢" if data.change_percent_24h >= 0 else "🔴"
        
        # RSI bar
        rsi_bar = self._make_bar(data.rsi, 100, 20)
        rsi_zone = "QUÁ MUA" if data.rsi > 70 else "QUÁ BÁN" if data.rsi < 30 else "TRUNG LẬP"
        
        # MACD signal
        macd_status = "TĂNG" if data.macd > 0 else "GIẢM"
        
        # CMF status
        cmf_bar = self._make_bar(abs(data.cmf) * 5, 1, 20) if data.cmf > 0 else self._make_bar(abs(data.cmf) * 5, 1, 20)
        cmf_status = "TIỀN CHẢY VÀO (+)" if data.cmf > 0 else "TIỀN CHẢY RA (-)"
        
        # Position in Bollinger
        bb_position = 0
        if data.bollinger_upper > data.bollinger_lower:
            bb_position = (data.current_price - data.bollinger_lower) / (data.bollinger_upper - data.bollinger_lower) * 100
        
        # VWAP status
        vwap_status = "TRÊN" if data.current_price > data.vwap else "DƯỚI"
        
        # Master score stars
        stars = "★" * (data.master_score // 20) + "☆" * (5 - data.master_score // 20)
        
        # Fear & Greed
        fg_text = "GREED" if data.fear_greed > 60 else "FEAR" if data.fear_greed < 40 else "NEUTRAL"
        fg_emoji = "🟢" if data.fear_greed > 60 else "🔴" if data.fear_greed < 40 else "🟡"
        
        # Format large numbers
        price_str = f"${data.current_price:,.2f}" if data.current_price < 10000 else f"${data.current_price:,.0f}"
        volume_str = f"${data.volume_24h/1e9:,.1f}B" if data.volume_24h > 1e9 else f"${data.volume_24h/1e6:,.1f}M"
        market_cap_str = f"${data.market_cap/1e12:,.2f}T" if data.market_cap > 1e12 else f"${data.market_cap/1e9:,.1f}B"
        
        output = f"""
┌──────────────────────────────────────────────────────────────────┐
│  ₿ {data.name.upper()} ({data.symbol})           THỜI GIAN: {now} │
├──────────────────────────────────────────────────────────────────┤
│  💰 GIÁ HIỆN TẠI                                              │
│  ────────────────────────────────────────────────────────────    │
│  Giá: {price_str} ({change_emoji}{data.change_percent_24h:+.2f}%)                                        │
│  24h High: ${data.high_24h:,.2f} │ 24h Low: ${data.low_24h:,.2f}                        │
│  Volume 24h: {volume_str}                                             │
│  Market Cap: {market_cap_str} │ Dominance: {data.dominance:.1f}%                        │
├──────────────────────────────────────────────────────────────────┤
│  📊 PHÂN TÍCH KỸ THUẬT (vnstock_ta)                          │
│  ────────────────────────────────────────────────────────────    │
│  📈 ĐỘNG LƯỢNG                                                  │
│     RSI(14): {data.rsi:.0f} {rsi_bar} Zone: {rsi_zone}          │
│     MACD: {data.macd:+.2f} (Signal: {macd_status})                       │
│  📊 DÒNG TIỀN                                                  │
│     CMF(20): {data.cmf:+.2f} {cmf_bar} {cmf_status}      │
│  🎯 VÙNG GIÁ                                                    │
│     Bollinger: Upper ${data.bollinger_upper:,.0f} │ Middle ${data.bollinger_middle:,.0f} │ Lower ${data.bollinger_lower:,.0f} │
│     Giá đang ở vùng {bb_position:.0f}% (Trên middle)                        │
│     VWAP: ${data.vwap:,.2f} - Giá đang {vwap_status} VWAP                        │
│  🔄 XU HƯỚNG                                                    │
│     SMA(20): ${data.sma_20:,.2f} │ SMA(50): ${data.sma_50:,.2f} │ SMA(200): ${data.sma_200:,.2f}  │
│     Giá đang {'TRÊN' if data.current_price > data.sma_20 else 'DƯỚI'} SMA → {data.trend}             │
│     ADX: {data.adx:.0f} ({'Xu hướng MẠNH' if data.adx > 25 else 'Xu hướng yếu'})                            │
├──────────────────────────────────────────────────────────────────┤
│  📊 SENTIMENT & ON-CHAIN                                       │
│  ────────────────────────────────────────────────────────────    │
│  Fear & Greed Index: {fg_emoji}{data.fear_greed} ({fg_text})                              │
│  ────────────────────────────────────────────────────────────    │
│  Funding Rate: {data.funding_rate:+.3f}%/8h ({'Long > Short' if data.funding_rate > 0 else 'Short > Long'})           │
│  Open Interest: {volume_str} (Cao - Thận trọng)                     │
│  ETF Flow 24h: {change_emoji if data.etf_flow > 0 else '🔴'}{data.etf_flow:+.0f}M (Mu {'vào' if data.etf_flow > 0 else 'ra'})                               │
├──────────────────────────────────────────────────────────────────┤
│  🤖 AI INSIGHT: {data.recommendation}                       │
│  ────────────────────────────────────────────────────────────    │
│  Master Score: {data.master_score}/100 {stars}                                    │
│  ────────────────────────────────────────────────────────────    │
│  ✅ ƯU ĐIỂM:                                                   │
│     • Giá {'TRÊN' if data.current_price > data.sma_20 else 'DƯỚI'} SMA - {data.trend}                     │
│     • CMF {cmf_status.lower()} (CMF {data.cmf:+.2f})             │
│     • ADX {data.adx:.0f} - {'Xu hướng mạnh' if data.adx > 25 else 'Xu hướng yếu'}                              │
│  ⚠️ RỦI RO:                                                    │
│     • RSI {data.rsi:.0f} - Vùng {rsi_zone.lower()}                              │
│     • Fear & Greed {data.fear_greed} ({fg_text}) - {'Cẩn thận đỉnh local' if data.fear_greed > 70 else 'Có thể đáy local' if data.fear_greed < 30 else 'Trung lập'}                     │
│     • BB Position {bb_position:.0f}% - {'Gần Upper' if bb_position > 80 else 'Gần Lower' if bb_position < 20 else 'Giữa vùng'}                              │
│  ────────────────────────────────────────────────────────────    │
│  📌 HÀNH ĐỘNG CỤ THỂ:                                        │
│     • {'Đã có: GIỮ - Chốt lời dần quanh Upper BB' if bb_position > 70 else 'Chưa có: CHỜ MUA quanh Lower BB'}        │
│     • 🛑 Stop Loss: ${data.bollinger_lower:,.0f} (-{(data.current_price - data.bollinger_lower) / data.current_price * 100:.1f}%)                           │
│     • 🎯 Mục tiêu: ${data.bollinger_upper:,.0f} (+{(data.bollinger_upper - data.current_price) / data.current_price * 100:.1f}%)                          │
│     • ⏰ Timeframe: SWING (1-4 tuần)                          │
└──────────────────────────────────────────────────────────────────┘
"""
        return output
    
    def _make_bar(self, value: float, max_val: float, width: int = 20) -> str:
        """Create a visual bar"""
        filled = int((min(value, max_val) / max_val) * width)
        bar = "█" * filled + "░" * (width - filled)
        return bar
