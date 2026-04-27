"""
Gold Analyzer Module - Phase 3 (Enhanced v2)
Phân tích vàng tách riêng: THẾ GIỚI vs SJC
- Module A: Dự báo Vàng Thế giới (The Driver)
- Module B: Dự báo Vàng SJC (The Follower)
"""
from dataclasses import dataclass
from typing import Optional, List
import pandas as pd
from datetime import datetime


@dataclass
class WorldGoldData:
    """Data for World Gold (Global Predictor)"""
    symbol: str = "WORLD"
    name: str = "Vàng Thế Giới (XAU/USD)"
    
    # Price data (USD/oz)
    current_price: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    high: float = 0.0
    low: float = 0.0
    
    # Inter-market (USD)
    dxy: float = 0.0  # Dollar Index
    us10y_yield: float = 0.0  # US 10Y Yield %
    
    # Technical indicators
    rsi: float = 50.0
    macd: float = 0.0
    macd_signal: float = 0.0
    adx: float = 25.0
    sma_20: float = 0.0
    sma_50: float = 0.0
    atr: float = 0.0
    
    # Fibonacci levels
    fib_618: float = 0.0
    fib_500: float = 0.0
    fib_382: float = 0.0
    fib_786: float = 0.0
    
    # Bollinger Bands
    bollinger_upper: float = 0.0
    bollinger_mid: float = 0.0
    bollinger_lower: float = 0.0
    
    # Support & Resistance
    resistance_1: float = 0.0
    resistance_2: float = 0.0
    support_1: float = 0.0
    support_2: float = 0.0
    
    # Prediction
    recommendation: str = "NEUTRAL"
    trend: str = "SIDEWAYS"
    probability: int = 50  # %
    entry_target: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward: float = 0.0
    master_score: int = 50
    
    # Signal
    dxy_signal: str = ""  # DXY impact on gold
    yield_signal: str = ""  # Yield impact on gold
    fibo_analysis: dict = None  # Fibo levels with support/resistance based on price position

    def __post_init__(self):
        if self.fibo_analysis is None:
            self.fibo_analysis = {}


@dataclass
class SjcGoldData:
    """Data for SJC Gold (Domestic Predictor)"""
    symbol: str = "SJC"
    name: str = "Vàng SJC Việt Nam"
    
    # SJC Prices (VND/lượng)
    sjc_buy: float = 0.0
    sjc_sell: float = 0.0
    sjc_change: float = 0.0
    sjc_change_pct: float = 0.0
    
    # World gold reference (from Module A)
    world_price_usd: float = 0.0
    vnd_usd: float = 25500.0
    
    # Premium analysis
    world_converted: float = 0.0  # Giá TT quy đổi
    premium: float = 0.0  # Chênh lệch VND
    premium_pct: float = 0.0
    premium_target: float = 8000000.0  # Mục tiêu 8M VND
    
    # Premium status
    premium_status: str = "NORMAL"  # CHEAP/NORMAL/EXPENSIVE/RISK
    risk_level: str = "LOW"  # LOW/MEDIUM/HIGH/CRITICAL
    
    # World trend impact
    world_trend: str = "NEUTRAL"  # From Module A
    expected_adjustment: float = 0.0  # Kỳ vọng điều chỉnh
    
    # Prediction
    recommendation: str = "HOLD"
    target_price: float = 0.0  # Giá mục tiêu
    reason: str = ""
    master_score: int = 50


class GoldAnalyzer:
    """Enhanced Gold Analyzer - Tách riêng Thế Giới và SJC"""
    
    def __init__(self, period_ta: int = 50):
        self.period_ta = period_ta
    
    def get_available_modes(self) -> List[str]:
        """Return available analysis modes"""
        return [
            "WORLD_ONLY - Dự báo Vàng Thế Giới (XAU/USD)",
            "SJC_ONLY - Dự báo Vàng SJC (Nội địa)",
            "GOLD_COMBO - So sánh Thế Giới vs SJC"
        ]
    
    def analyze(self, mode: str = "GOLD_COMBO") -> tuple:
        """
        Analyze gold based on mode
        
        Args:
            mode: "WORLD_ONLY" - Only XAU/USD analysis
                  "SJC_ONLY" - Only SJC analysis  
                  "GOLD_COMBO" - Both (returns tuple)
        
        Returns:
            WorldGoldData, SjcGoldData (for COMBO)
            WorldGoldData (for WORLD_ONLY)
            SjcGoldData (for SJC_ONLY)
        """
        if mode == "WORLD_ONLY":
            return self._analyze_world_only()
        elif mode == "SJC_ONLY":
            return self._analyze_sjc_only()
        else:  # GOLD_COMBO
            world = self._analyze_world_only()
            sjc = self._analyze_sjc_only(world)
            return world, sjc
    
    def _analyze_world_only(self) -> WorldGoldData:
        """Module A: Dự báo Vàng Thế giới (Global Predictor)"""
        data = WorldGoldData()
        
        # 1. Get XAU/USD price
        self._get_xau_price(data)
        
        # 2. Get inter-market data
        self._get_intermarket(data)
        
        # 3. Calculate technical indicators
        self._calculate_technical(data)
        
        # 4. Generate prediction
        self._predict_world(data)
        
        return data
    
    def _analyze_sjc_only(self, world_data: WorldGoldData = None) -> SjcGoldData:
        """Module B: Dự báo Vàng SJC (Domestic Predictor)"""
        data = SjcGoldData()
        
        # 1. Get SJC price
        self._get_sjc_price(data)
        
        # 2. Get world gold reference
        if world_data is None:
            # Get world data independently
            world_data = self._analyze_world_only()
        
        data.world_price_usd = world_data.current_price
        
        # 3. Get exchange rate
        self._get_exchange_rate(data)
        
        # 4. Calculate premium
        self._calculate_premium(data)
        
        # 5. Generate SJC prediction based on Module A
        self._predict_sjc(data, world_data)
        
        return data
    
    def _get_xau_price(self, data: WorldGoldData):
        """Get XAU/USD price via yfinance"""
        try:
            import yfinance as yf
            
            gold = yf.Ticker("GC=F")
            hist = gold.history(period="10d")
            
            if hist is not None and len(hist) > 0:
                last = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else last
                
                data.current_price = float(last['Close'])
                data.high = float(last['High'])
                data.low = float(last['Low'])
                
                prev_close = float(prev['Close'])
                if prev_close > 0:
                    data.change = data.current_price - prev_close
                    data.change_pct = round(data.change / prev_close * 100, 2)
        except Exception as e:
            print(f"[GoldAnalyzer] XAU price error: {e}")
    
    def _get_intermarket(self, data: WorldGoldData):
        """Get DXY and US10Y Yield"""
        try:
            import yfinance as yf
            
            # DXY
            try:
                dxy = yf.Ticker("DX-Y.NYB")
                hist = dxy.history(period="5d")
                if hist is not None and len(hist) > 0:
                    data.dxy = float(hist['Close'].iloc[-1])
            except:
                pass
            
            # US10Y
            try:
                us10y = yf.Ticker("^TNX")
                hist = us10y.history(period="5d")
                if hist is not None and len(hist) > 0:
                    data.us10y_yield = float(hist['Close'].iloc[-1])
            except:
                pass
        except Exception as e:
            print(f"[GoldAnalyzer] Inter-market error: {e}")
    
    def _calculate_technical(self, data: WorldGoldData):
        """Calculate technical indicators for XAU/USD"""
        try:
            import yfinance as yf
            
            gold = yf.Ticker("GC=F")
            df = gold.history(period=f"{max(100, self.period_ta)}d")
            
            if df is None or len(df) < 20:
                return
            
            close = df['Close']
            high = df['High']
            low = df['Low']
            
            # SMA
            if len(close) >= 20:
                data.sma_20 = float(close.rolling(20).mean().iloc[-1])
            if len(close) >= 50:
                data.sma_50 = float(close.rolling(50).mean().iloc[-1])
            
            # RSI
            if len(close) >= 14:
                delta = close.diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                data.rsi = float((100 - (100 / (1 + rs))).iloc[-1])
            
            # MACD
            if len(close) >= 26:
                ema12 = close.ewm(span=12, adjust=False).mean()
                ema26 = close.ewm(span=26, adjust=False).mean()
                macd_line = ema12 - ema26
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                data.macd = float(macd_line.iloc[-1])
                data.macd_signal = float(signal_line.iloc[-1])
            
            # ATR
            if len(df) >= 14:
                tr1 = high - low
                tr2 = abs(high - close.shift(1))
                tr3 = abs(low - close.shift(1))
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                data.atr = float(tr.rolling(14).mean().iloc[-1])
            
            # Bollinger Bands (50-day for longer-term view)
            if len(close) >= 20:
                sma20 = close.rolling(20).mean()
                std20 = close.rolling(20).std()
                data.bollinger_upper = float((sma20 + 2 * std20).iloc[-1])
                data.bollinger_mid = float(sma20.iloc[-1])
                data.bollinger_lower = float((sma20 - 2 * std20).iloc[-1])
            
            # Fibonacci Retracement (50-day swing)
            if len(close) >= 50:
                swing_high = float(close.tail(50).max())
                swing_low = float(close.tail(50).min())
                diff = swing_high - swing_low
                data.fib_786 = swing_high - diff * 0.786
                data.fib_618 = swing_high - diff * 0.618
                data.fib_500 = swing_high - diff * 0.500
                data.fib_382 = swing_high - diff * 0.382
            
            # Support & Resistance
            data.resistance_1 = float(close.tail(20).max() * 1.005)  # +0.5%
            data.support_1 = float(close.tail(20).min() * 0.995)  # -0.5%
            
        except Exception as e:
            print(f"[GoldAnalyzer] Technical error: {e}")
    
    def _predict_world(self, data: WorldGoldData):
        """Generate XAU/USD prediction based on technicals and macro"""
        score = 50
        
        # === DXY Analysis ===
        if data.dxy > 105:
            data.dxy_signal = "DXY mạnh → Vàng yếu"
            score -= 15
        elif data.dxy > 100:
            data.dxy_signal = "DXY cao → Vàng chịu áp lực"
            score -= 8
        elif data.dxy < 95:
            data.dxy_signal = "DXY yếu → Vàng được hỗ trợ"
            score += 15
        elif data.dxy < 100:
            data.dxy_signal = "DXY thấp → Vàng tích cực"
            score += 8
        
        # === US10Y Yield Analysis ===
        if data.us10y_yield > 5.0:
            data.yield_signal = "Yield cao → Vàng giảm"
            score -= 10
        elif data.us10y_yield > 4.5:
            data.yield_signal = "Yield khá cao → Áp lực lên vàng"
            score -= 5
        elif data.us10y_yield > 4.0:
            data.yield_signal = "Yield cao → Áp lực lên vàng"
            score -= 3
        elif data.us10y_yield < 3.5:
            data.yield_signal = "Yield thấp → Vàng hưởng lợi"
            score += 10
        elif data.us10y_yield < 4.0:
            data.yield_signal = "Yield vừa phải → Hỗ trợ vàng"
            score += 5
        else:
            data.yield_signal = "Yield trung bình → Trung lập"
            score += 0
        
        # === RSI Analysis ===
        if data.rsi > 75:
            score -= 10
        elif data.rsi > 70:
            score -= 5
        elif data.rsi < 30:
            score += 15
        elif data.rsi < 35:
            score += 10
        elif data.rsi < 45:
            score += 5
        
        # === MACD Analysis ===
        if data.macd > 0 and data.macd > data.macd_signal:
            score += 10
        elif data.macd < 0 and data.macd < data.macd_signal:
            score -= 10
        
        # === Trend Analysis ===
        if data.sma_20 > data.sma_50:
            score += 5  # Golden cross potential
        else:
            score -= 5
        
        # === Position in Bollinger ===
        if data.bollinger_upper > 0 and data.current_price > 0:
            position = (data.current_price - data.bollinger_lower) / (data.bollinger_upper - data.bollinger_lower) * 100
            if position > 80:
                score -= 10  # Near upper band
            elif position < 20:
                score += 10  # Near lower band
        
        # Cap score
        score = max(0, min(100, int(score)))
        data.master_score = score
        
        # === Determine Trend ===
        if data.sma_20 > data.sma_50 and data.current_price > data.sma_20:
            data.trend = "UPTREND"
        elif data.sma_20 < data.sma_50 and data.current_price < data.sma_20:
            data.trend = "DOWNTREND"
        else:
            data.trend = "SIDEWAYS"
        
        # === Set Recommendation ===
        if score >= 65:
            data.recommendation = "LONG"
            data.probability = min(85, score)
            data.entry_target = data.current_price
            data.stop_loss = data.support_1 if data.support_1 > 0 else data.current_price - data.atr
            data.take_profit = data.resistance_1 if data.resistance_1 > 0 else data.current_price + data.atr * 1.5
        elif score >= 55:
            data.recommendation = "ACCUMULATE"
            data.probability = 55
            data.entry_target = data.current_price
            data.stop_loss = data.support_1
            data.take_profit = data.resistance_1
        elif score >= 45:
            data.recommendation = "NEUTRAL"
            data.probability = 50
        elif score >= 35:
            data.recommendation = "REDUCE"
            data.probability = 55
        else:
            data.recommendation = "SHORT"
            data.probability = min(85, 100 - score)
            data.entry_target = data.current_price
            data.stop_loss = data.resistance_1 if data.resistance_1 > 0 else data.current_price + data.atr
            data.take_profit = data.support_1 if data.support_1 > 0 else data.current_price - data.atr * 1.5
        
        # Calculate Risk/Reward
        if data.stop_loss > 0 and data.take_profit > 0:
            if "LONG" in data.recommendation:
                risk = data.entry_target - data.stop_loss
                reward = data.take_profit - data.entry_target
                if risk > 0:
                    data.risk_reward = round(reward / risk, 1)
            else:
                risk = data.stop_loss - data.entry_target
                reward = data.entry_target - data.take_profit
                if risk > 0:
                    data.risk_reward = round(reward / risk, 1)

        # === Fibonacci Position Analysis ===
        # Determine which Fibo levels are support vs resistance based on price position
        data.fibo_analysis = {}
        if data.current_price > 0:
            price = data.current_price
            # Fibo levels above current price = resistance
            # Fibo levels below current price = support
            for level_name, level_value in [
                ("fib_786", data.fib_786),
                ("fib_618", data.fib_618),
                ("fib_500", data.fib_500),
                ("fib_382", data.fib_382),
            ]:
                if level_value > 0:
                    if price < level_value:
                        data.fibo_analysis[level_name] = {
                            "value": level_value,
                            "type": "RESISTANCE",
                            "distance": ((level_value - price) / price) * 100
                        }
                    else:
                        data.fibo_analysis[level_name] = {
                            "value": level_value,
                            "type": "SUPPORT",
                            "distance": ((price - level_value) / price) * 100
                        }
    
    def _get_sjc_price(self, data: SjcGoldData):
        """Get SJC gold prices"""
        try:
            from vnstock_data import CommodityPrice
            
            commodity = CommodityPrice()
            df = commodity.gold_vn(length=f"{self.period_ta}D")
            
            if df is not None and len(df) > 0:
                last = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else last
                
                # API trả về đơn vị "nghìn đồng" - CẦN NHÂN 1000
                raw_buy = float(last.get('buy', 0))
                raw_sell = float(last.get('sell', 0))
                
                data.sjc_buy = raw_buy * 1000
                data.sjc_sell = raw_sell * 1000
                
                if pd.notna(prev.get('sell')):
                    prev_sell = float(prev['sell']) * 1000
                    data.sjc_change = data.sjc_sell - prev_sell
                    if prev_sell > 0:
                        data.sjc_change_pct = round(data.sjc_change / prev_sell * 100, 2)
        except Exception as e:
            print(f"[GoldAnalyzer] SJC price error: {e}")
    
    def _get_exchange_rate(self, data: SjcGoldData):
        """Get USD/VND exchange rate"""
        try:
            import yfinance as yf
            
            usd_vnd = yf.Ticker("USDVND=X")
            hist = usd_vnd.history(period="5d")
            
            if hist is not None and len(hist) > 0:
                data.vnd_usd = float(hist['Close'].iloc[-1])
        except:
            pass
    
    def _calculate_premium(self, data: SjcGoldData):
        """Calculate SJC premium vs world gold"""
        if data.world_price_usd > 0 and data.vnd_usd > 0 and data.sjc_sell > 0:
            # Công thức: XAU_USD * 1.20565 * VND_USD
            data.world_converted = data.world_price_usd * 1.20565 * data.vnd_usd
            
            # Premium = SJC bán ra - Giá TT quy đổi
            data.premium = data.sjc_sell - data.world_converted
            
            # Premium %
            if data.world_converted > 0:
                data.premium_pct = round(data.premium / data.world_converted * 100, 2)
            
            # Premium status
            if data.premium > 15000000:
                data.premium_status = "CRITICAL"
                data.risk_level = "CRITICAL"
            elif data.premium > 12000000:
                data.premium_status = "EXPENSIVE"
                data.risk_level = "HIGH"
            elif data.premium > 8000000:
                data.premium_status = "NORMAL"
                data.risk_level = "MEDIUM"
            elif data.premium > 5000000:
                data.premium_status = "CHEAP"
                data.risk_level = "LOW"
            else:
                data.premium_status = "VERY_CHEAP"
                data.risk_level = "VERY_LOW"
    
    def _predict_sjc(self, data: SjcGoldData, world: WorldGoldData):
        """Generate SJC prediction based on Premium + World trend"""
        score = 50
        
        # === Premium Impact (Most important for SJC) ===
        if data.premium > 15000000:
            score -= 35
        elif data.premium > 12000000:
            score -= 20
        elif data.premium > 8000000:
            score -= 5
        elif data.premium > 5000000:
            score += 10
        else:
            score += 25
        
        # === World Trend Impact ===
        if world.recommendation == "LONG" or world.recommendation == "ACCUMULATE":
            data.world_trend = "BULLISH"
            if data.premium < 10000000:
                score += 15  # World up + Premium cheap = BUY signal
            elif data.premium > 15000000:
                score -= 10  # World up but Premium too high = warning
        elif world.recommendation == "SHORT":
            data.world_trend = "BEARISH"
            if data.premium > 15000000:
                score -= 25  # World down + Premium high = SELL signal
            else:
                score -= 10
        else:
            data.world_trend = "NEUTRAL"
        
        # === Expected Adjustment ===
        # If Premium > target, SJC should adjust down
        if data.premium > data.premium_target:
            data.expected_adjustment = data.premium - data.premium_target
        
        # === Set Recommendation ===
        score = max(0, min(100, int(score)))
        data.master_score = score
        
        if data.premium > 15000000:
            data.recommendation = "SELL_URGENT"
            data.reason = f"Premium quá cao ({data.premium/1e6:.1f}M). Rủi ro sập Premium."
            data.target_price = data.sjc_sell - data.expected_adjustment
        elif data.premium > 12000000:
            data.recommendation = "SELL"
            data.reason = f"Premium cao ({data.premium/1e6:.1f}M). Không nên mua mới."
            data.target_price = data.sjc_sell - data.expected_adjustment * 0.5
        elif data.premium > 8000000:
            data.recommendation = "HOLD"
            data.reason = f"Premium bình thường ({data.premium/1e6:.1f}M). {world.dxy_signal}."
            data.target_price = data.sjc_sell
        elif data.premium > 5000000:
            data.recommendation = "BUY"
            data.reason = f"Premium thấp ({data.premium/1e6:.1f}M). Cơ hội tích lũy."
            data.target_price = data.sjc_sell + abs(data.expected_adjustment)
        else:
            data.recommendation = "BUY_STRONG"
            data.reason = f"Premium rất thấp ({data.premium/1e6:.1f}M). Mua mạnh."
            data.target_price = data.sjc_sell + abs(data.expected_adjustment)
    
    def format_world(self, data: WorldGoldData) -> str:
        """Format World Gold Analysis (Module A)"""
        
        # Trend emoji
        if data.recommendation in ["LONG", "ACCUMULATE"]:
            rec_emoji = "🟢"
        elif data.recommendation == "NEUTRAL":
            rec_emoji = "🟡"
        else:
            rec_emoji = "🔴"
        
        # RSI zone
        if data.rsi > 70:
            rsi_zone = "QUÁ MUA"
            rsi_emoji = "🔴"
        elif data.rsi < 30:
            rsi_zone = "QUÁ BÁN"
            rsi_emoji = "🟢"
        else:
            rsi_zone = "TRUNG LẬP"
            rsi_emoji = "🟡"
        
        # RSI bar
        rsi_pct = min(100, max(0, data.rsi * 2))
        rsi_bar = "█" * int(rsi_pct / 5) + "░" * (20 - int(rsi_pct / 5))
        
        # Change emoji
        if data.change_pct >= 0:
            change_emoji = "🟢"
            change_str = f"+${data.change:.2f} ({data.change_pct:+.2f}%)"
        else:
            change_emoji = "🔴"
            change_str = f"${data.change:.2f} ({data.change_pct:+.2f}%)"
        
        # Score stars
        stars = "★" * (data.master_score // 20) + "☆" * (5 - data.master_score // 20)
        
        output = f"""
╔══════════════════════════════════════════════════════════════════╗
║  🌍 DỰ BÁO VÀNG THẾ GIỚI (XAU/USD)   | {datetime.now().strftime('%Y-%m-%d %H:%M')}       ║
╠══════════════════════════════════════════════════════════════════╣
║  💵 GIÁ XAU/USD                                               │
║  ────────────────────────────────────────────────────────────────│
║  Giá hiện tại:    ${data.current_price:,.2f}                                      │
║  {change_emoji} Thay đổi:    {change_str}                              │
║  ────────────────────────────────────────────────────────────────│
║  📊 VĨ MÔ (USD)                                               │
║  DXY (Dollar Index):     {data.dxy:>6.2f}  →  {data.dxy_signal}     │
║  US10Y (Lợi suất):        {data.us10y_yield:>5.2f}%  →  {data.yield_signal}   │
╠══════════════════════════════════════════════════════════════════╣
║  📊 PHÂN TÍCH KỸ THUẬT                                      │
║  ────────────────────────────────────────────────────────────────│
║  📈 ĐỘNG LƯỢNG                                                  │
║     RSI(14): {data.rsi:>5.1f} {rsi_bar} {rsi_emoji} Zone: {rsi_zone}                │
║     MACD: {data.macd:>+8.2f} (Signal: {data.macd_signal:+.2f})                       │
║  ────────────────────────────────────────────────────────────────│
║  🔄 XU HƯỚNG                                                  │
║     SMA(20): ${data.sma_20:,.2f} │ SMA(50): ${data.sma_50:,.2f}                  │
║     Giá đang {data.trend}                                    │
║  ────────────────────────────────────────────────────────────────│
║  🎯 FIBONACCI (50 ngày)                                        │
║     Giá hiện tại: ${data.current_price:,.2f}                                │"""
        
        # Show Fibo levels with correct support/resistance labels based on price position
        if data.fibo_analysis:
            for level_name in ["fib_786", "fib_618", "fib_500", "fib_382"]:
                if level_name in data.fibo_analysis:
                    info = data.fibo_analysis[level_name]
                    label = level_name.replace("fib_", "Fib ").replace("_", ".")
                    type_emoji = "🔴" if info["type"] == "RESISTANCE" else "🟢"
                    output += f"""
║     {type_emoji} {label}: ${info['value']:,.2f} ({info['type']})                    │"""
        
        output += """
║  ────────────────────────────────────────────────────────────────│
║  📐 BOLLINGER BANDS                                            │
║     Upper: ${data.bollinger_upper:,.2f} │ Mid: ${data.bollinger_mid:,.2f}                │
║     Lower: ${data.bollinger_lower:,.2f}                                      │
╠══════════════════════════════════════════════════════════════════╣
║  🤖 DỰ BÁO: {rec_emoji} {data.recommendation} ({data.probability}% likely)                   │
║  ────────────────────────────────────────────────────────────────│
║  Master Score: {data.master_score}/100 {stars}                                   │
║  ────────────────────────────────────────────────────────────────│
║  📌 CÁC VÙNG QUAN TRỌNG                                        │"""
        
        if data.recommendation in ["LONG", "ACCUMULATE"]:
            output += f"""
║     🎯 Target:    ${data.take_profit:,.2f}                                      │
║     🛑 Stop Loss: ${data.stop_loss:,.2f}                                      │
║     📐 Risk/Reward: {data.risk_reward:.1f}x                                        │"""
        elif data.recommendation == "SHORT":
            output += f"""
║     🎯 Target:    ${data.take_profit:,.2f}                                      │
║     🛑 Stop Loss: ${data.stop_loss:,.2f}                                      │
║     📐 Risk/Reward: {data.risk_reward:.1f}x                                        │"""
        else:
            output += f"""
║     Kháng cự: ${data.resistance_1:,.2f}                                      │
║     Hỗ trợ:   ${data.support_1:,.2f}                                      │"""
        
        output += """
╚══════════════════════════════════════════════════════════════════╝
"""
        return output
    
    def format_sjc(self, data: SjcGoldData, world: WorldGoldData = None) -> str:
        """Format SJC Gold Analysis (Module B)"""
        
        # Premium status emoji
        if data.premium_status == "CRITICAL":
            premium_emoji = "🔴"
            premium_status = "⚠️ NGUY HIỂM"
        elif data.premium_status == "EXPENSIVE":
            premium_emoji = "🟠"
            premium_status = "⚠️ ĐẮT"
        elif data.premium_status == "NORMAL":
            premium_emoji = "🟡"
            premium_status = "✓ BÌNH THƯỜNG"
        else:
            premium_emoji = "🟢"
            premium_status = "✓ RẺ"
        
        # Recommendation emoji
        if "BUY" in data.recommendation:
            rec_emoji = "🟢"
        elif "SELL" in data.recommendation:
            rec_emoji = "🔴"
        else:
            rec_emoji = "🟡"
        
        # Change emoji
        if data.sjc_change_pct >= 0:
            change_emoji = "🟢"
            change_str = f"+{data.sjc_change:,.0f} ({data.sjc_change_pct:+.2f}%)"
        else:
            change_emoji = "🔴"
            change_str = f"{data.sjc_change:,.0f} ({data.sjc_change_pct:+.2f}%)"
        
        # Score stars
        stars = "★" * (data.master_score // 20) + "☆" * (5 - data.master_score // 20)
        
        # Risk level color
        risk_color = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢", "VERY_LOW": "🟢"}
        risk_emoji = risk_color.get(data.risk_level, "🟡")
        
        output = f"""
╔══════════════════════════════════════════════════════════════════╗
║  🥇 DỰ BÁO VÀNG SJC (NỘI ĐỊA)        | {datetime.now().strftime('%Y-%m-%d %H:%M')}       ║
╠══════════════════════════════════════════════════════════════════╣
║  💰 GIÁ SJC VIỆT NAM                                         │
║  ────────────────────────────────────────────────────────────────│
║  Mua vào:       {data.sjc_buy:>15,.0f} VND/lượng                          │
║  Bán ra:        {data.sjc_sell:>15,.0f} VND/lượng                          │
║  {change_emoji} Thay đổi:   {change_str}                             │
╠══════════════════════════════════════════════════════════════════╣
║  📊 PREMIUM ANALYSIS                                          │
║  ────────────────────────────────────────────────────────────────│
║  Giá TT quy đổi:   {data.world_converted:>15,.0f} VND/lượng                          │
║  {premium_emoji} Premium:          {data.premium:>+15,.0f} VND/lượng                          │
║  Premium %:         {data.premium_pct:>+14,.2f}%                                   │
║  ────────────────────────────────────────────────────────────────│
║  {premium_emoji} Status: {premium_status} ({data.premium_status})                        │
║  {risk_emoji} Risk Level: {data.risk_level}                                           │
╠══════════════════════════════════════════════════════════════════╣
║  📊 WORLD IMPACT (Module A)                                   │
║  ────────────────────────────────────────────────────────────────│"""
        
        if world:
            output += f"""
║  XAU/USD: ${world.current_price:,.2f} ({world.recommendation})                           │
║  DXY: {world.dxy:>6.2f} → {world.dxy_signal}                  │
║  World Trend: {data.world_trend}                                   │"""
        
        output += f"""
╠══════════════════════════════════════════════════════════════════╣
║  🤖 DỰ BÁO SJC: {rec_emoji} {data.recommendation}                                    │
║  ────────────────────────────────────────────────────────────────│
║  Master Score: {data.master_score}/100 {stars}                                   │
║  Lý do: {data.reason}                            │
║  ────────────────────────────────────────────────────────────────│
║  📌 KỲ VỌNG ĐIỀU CHỈNH                                       │"""
        
        if data.expected_adjustment > 0:
            output += f"""
║  ⚠️ Premium đang cao hơn mục tiêu {data.premium_target/1e6:.0f}M               │
║  → SJC có thể giảm: {data.expected_adjustment:,.0f} VND/lượng              │
║  → Giá mục tiêu: {data.target_price:,.0f} VND/lượng                    │
║  ────────────────────────────────────────────────────────────────│
║  📋 CHIẾN LƯỢC:                                              │"""
        else:
            output += f"""
║  → Premium gần mức mục tiêu {data.premium_target/1e6:.0f}M                   │
║  → Giá dự kiến: {data.target_price:,.0f} VND/lượng                      │
║  ────────────────────────────────────────────────────────────────│
║  📋 CHIẾN LƯỢC:                                              │"""
        
        # Strategy
        if "BUY" in data.recommendation:
            output += """
║  🟢 MUA SJC - Premium thấp, cơ hội tích lũy                │
║     • Mua khi điều chỉnh nhẹ                               │
║     • Mục tiêu: Premium về 8M VND                           │
║     • Stoploss: Nếu Premium > 12M VND                        │"""
        elif "SELL" in data.recommendation:
            output += """
║  🔴 BÁN SJC - Premium quá cao, rủi ro sập Premium          │
║     • Bán để chốt lời / phòng vệ                           │
║     • Chờ mua lại khi Premium < 8M VND                        │
║     • Warning: NHNN có thể can thiệp nếu Premium > 15M       │"""
        else:
            output += """
║  🟡 THEO DÕI - Premium vừa phải                             │
║     • Không hành động vội                                   │
║     • Chờ tín hiệu rõ ràng từ thế giới                       │"""
        
        output += """
╚══════════════════════════════════════════════════════════════════╝
"""
        return output
    
    def format_combo(self, world: WorldGoldData, sjc: SjcGoldData) -> str:
        """Format combined analysis (both modules)"""
        return self.format_world(world) + "\n" + self.format_sjc(sjc, world)
    
    def show_modes(self):
        """Show available analysis modes"""
        print("\n" + "="*60)
        print("GOLD ANALYZER - Available Modes:")
        print("="*60)
        for i, mode in enumerate(self.get_available_modes(), 1):
            print(f"  {i}. {mode}")
        print("="*60)
        print()
