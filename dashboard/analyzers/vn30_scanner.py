"""
VN30 Scanner - Short-term Momentum Alpha Scanner v5 (FULL UPGRADE)
Mục tiêu: Tìm mã cổ phiếu tốt nhất để đánh T+ (Swing Trading ngắn hạn)

V5 CHANGES:
1. Expand Universe: Top 100 mã thanh khoản HOSE thay VN30
2. Fix Inverted Stop Loss: SL phải < Entry
3. R:R Ranking Priority: Ưu tiên R:R >= 2.0
4. Smart Est. Days: RSI>80 thì cộng thêm 3 ngày
5. UI: N/A + High Risk label cho missing data
"""
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd


@dataclass
class StockPick:
    """Kết quả phân tích một mã cổ phiếu cho trading ngắn hạn"""
    symbol: str = ""
    company_name: str = ""

    # === SCORES ===
    master_score: int = 50
    technical_score: int = 50
    fundamental_score: int = 50

    # === TECHNICAL ===
    rsi: float = 50.0
    adx: float = 25.0
    plus_di: float = 0.0
    minus_di: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    atr: float = 0.0
    sma_10: float = 0.0
    sma_20: float = 0.0
    sma_50: float = 0.0
    current_price: float = 0.0
    cmf: float = 0.0
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    bb_percent: float = 50.0
    volume_ratio: float = 1.0
    avg_volume_value: float = 0.0  # Triệu VND

    # === FUNDAMENTAL ===
    pe: float = 0.0
    pb: float = 0.0
    roe: float = 0.0
    f_score: int = 0
    has_fundamental_data: bool = False
    is_high_risk: bool = False

    # === PRICE ACTION ===
    change_percent: float = 0.0

    # === STATUS ===
    trend: str = "SIDEWAYS"
    breakout_status: str = ""
    signal: str = "WAIT"

    # === FILTERS ===
    is_breakout: bool = False
    is_short_term_qualified: bool = False
    is_fast_pick: bool = False

    # === TRADING LEVELS ===
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward_ratio: float = 0.0
    has_inverted_sl: bool = False

    # === HOLDING ===
    estimated_days_to_target: float = 0.0
    is_slow_mode: bool = False

    # === CRITERIA ===
    criteria_met: int = 0
    criteria_list: List[str] = field(default_factory=list)

    # === VETO ===
    is_vetoed: bool = False
    veto_reason: str = ""

    # === CONTEXT ===
    market_overbought_warning: bool = False
    market_rsi: float = 0.0

    def __post_init__(self):
        # FAST Pick: ADX > 18 AND Volume > 0.8x
        if self.adx > 18 and self.volume_ratio > 0.8:
            self.is_fast_pick = True

        # High Risk: missing fundamental data
        if not self.has_fundamental_data:
            self.is_high_risk = True

        # Breakout status
        if self.is_vetoed:
            self.breakout_status = "🛑 VETO"
        elif self.is_fast_pick and self.cmf > 0:
            self.is_breakout = True
            self.breakout_status = "🚨 BREAKOUT"
        elif self.is_short_term_qualified:
            self.breakout_status = "⚡ QUALIFIED"
        elif self.is_fast_pick:
            self.breakout_status = "⚡ FAST"
        else:
            self.breakout_status = "⏳ CONSOLIDATION"

        # BB Percent
        if self.bb_upper > self.bb_lower:
            self.bb_percent = round(
                (self.current_price - self.bb_lower) / (self.bb_upper - self.bb_lower) * 100, 1
            )


@dataclass
class ScanResult:
    """Kết quả quét toàn bộ"""
    scan_time: datetime = field(default_factory=datetime.now)
    stocks: List[StockPick] = field(default_factory=list)
    top_picks: List[StockPick] = field(default_factory=list)
    fast_picks: List[StockPick] = field(default_factory=list)
    slow_picks: List[StockPick] = field(default_factory=list)
    market_status: str = "NEUTRAL"
    market_rsi: float = 0.0

    # Warnings
    signal_conflict: bool = False
    conflict_message: str = ""
    market_overbought_warning: bool = False
    market_warning_message: str = ""

    # Summary
    total_scanned: int = 0
    bullish_count: int = 0
    bearish_count: int = 0
    breakout_count: int = 0
    qualified_count: int = 0
    fast_count: int = 0
    vetoed_count: int = 0
    high_risk_count: int = 0


class Top100Scanner:
    """
    Top 100 Liquidity Scanner v5

    UNIVERSE: Top 100 mã thanh khoản cao nhất HOSE
    VETO: CMF<0 OR R:R<1.0 → Score<=50, Signal=WAIT
    RANKING: R:R>=2.0 ưu tiên trước Master Score
    EST.DAYS: RSI>80 → +3 ngày
    """

    CACHE_DURATION = timedelta(hours=1)
    TOP_PICKS_LIMIT = 8
    MIN_SCORE_FOR_PICK = 55
    SLOW_THRESHOLD_DAYS = 10
    MIN_HOLDING_DAYS = 3

    # Universe filters
    MIN_LIQUIDITY_BILLION = 15  # 15 tỷ/phiên
    MIN_PRICE = 10000  # > 10,000 VND

    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self._cache: Optional[ScanResult] = None
        self._cache_time: Optional[datetime] = None

    def is_cache_valid(self) -> bool:
        if not self.use_cache or self._cache is None or self._cache_time is None:
            return False
        return datetime.now() - self._cache_time < self.CACHE_DURATION

    def get_cached_result(self) -> Optional[ScanResult]:
        return self._cache if self.is_cache_valid() else None

    def scan(self, force_refresh: bool = False) -> ScanResult:
        if not force_refresh and self.is_cache_valid():
            return self.get_cached_result()

        result = ScanResult()

        try:
            # Get Top 100 by liquidity
            symbols = self._get_top_100_by_liquidity()
            result.total_scanned = len(symbols)

            result.market_rsi = self._get_market_rsi()
            result.market_overbought_warning = result.market_rsi > 70

            stocks = []
            for symbol in symbols:
                try:
                    pick = self._analyze_stock(symbol, result.market_rsi)
                    if pick:
                        stocks.append(pick)

                        if pick.is_vetoed:
                            result.vetoed_count += 1
                        elif "BUY" in pick.signal or "ACCUMULATE" in pick.signal:
                            result.bullish_count += 1
                        elif "SELL" in pick.signal:
                            result.bearish_count += 1
                        if pick.is_breakout:
                            result.breakout_count += 1
                        if pick.is_short_term_qualified:
                            result.qualified_count += 1
                        if pick.is_fast_pick and not pick.is_vetoed:
                            result.fast_count += 1
                        if pick.is_high_risk:
                            result.high_risk_count += 1
                except Exception as e:
                    print(f"[Scanner] Error {symbol}: {e}")
                    continue

            # Sort: R:R>=2.0 first, then by Master Score
            stocks = self._sort_stocks(stocks)
            result.stocks = stocks

            # Filter eligible picks
            eligible = [s for s in stocks
                       if s.master_score >= self.MIN_SCORE_FOR_PICK
                       and not s.is_vetoed]

            # R:R >= 2.0 first
            rr_priority = [s for s in eligible if s.risk_reward_ratio >= 2.0]
            other = [s for s in eligible if s.risk_reward_ratio < 2.0]

            fast_picks = rr_priority[:self.TOP_PICKS_LIMIT]
            slow_picks = [s for s in other if s.is_slow_mode][:3]

            result.fast_picks = fast_picks
            result.slow_picks = slow_picks
            result.top_picks = fast_picks + slow_picks

            self._analyze_market_status(result)
            self._generate_market_warnings(result)

        except Exception as e:
            print(f"[Scanner] Scan error: {e}")

        self._cache = result
        self._cache_time = datetime.now()
        return result

    def _sort_stocks(self, stocks: List[StockPick]) -> List[StockPick]:
        """Sort: R:R>=2.0 first, then Master Score"""
        def sort_key(s: StockPick):
            if s.risk_reward_ratio >= 2.0:
                return (0, -s.master_score)  # R:R >= 2.0 group, sorted by score
            return (1, -s.master_score)  # Others, sorted by score

        return sorted(stocks, key=sort_key)

    def _get_top_100_by_liquidity(self) -> List[str]:
        """Lấy Top 100 mã thanh khoản cao nhất HOSE"""
        try:
            from vnstock import Quote, Listing
            import warnings
            warnings.filterwarnings('ignore')

            # Get all HOSE symbols
            try:
                listing = Listing(source="vci")
                all_symbols = listing.all_symbols()
                hose_symbols = []
                if isinstance(all_symbols, list):
                    hose_symbols = all_symbols[:200]  # Lấy 200 mã đầu
                elif hasattr(all_symbols, 'tolist'):
                    hose_symbols = all_symbols.tolist()[:200]
            except:
                hose_symbols = None

            if not hose_symbols:
                hose_symbols = [
                    "VNM", "VCB", "VHM", "VIC", "VPB", "BID", "TCB", "CTG", "MBB", "ACB",
                    "STB", "HPG", "FPT", "MWG", "PNJ", "TPB", "SHB", "SSI", "MSN", "GAS",
                    "PLX", "VRE", "VPB", "VIB", "VJC", "SAB", "HDB", "LPB", "SSB", "PVS",
                    "GVR", "DGC", "KDH", "GMD", "SBT", "DGW", "CMG", "IMP", "VHC", "MWG",
                    "REE", "NT2", "BCM", "POW", "VGR", "TCH", "HAG", "NVL", "DIG", "FLC",
                    "ROS", "ASM", "SCR", "ILD", "DRC", "TVT", "VEA", "HHS", "HCM", "SMA",
                    "PVI", "MIG", "BSR", "PVD", "PLT", "PET", "VCW", "VNR", "KLB", "QNS",
                    "CLC", "VSC", "VNG", "NSC", "GTN", "HUT", "VGT", "VPK", "VCC", "VGS",
                    "VLB", "VTO", "VNF", "VDS", "VBB", "VAB", "VND", "VCI", "BSC", "MBS",
                    "EIB", "OCB", "KBS", "HCM", "KSK", "SHS", "VDS", "BVS", "SHS", "TVS",
                    "VIG", "VFM", "BBW", "VGC", "HVN", "CIA", "AGR", "AMS", "ASM", "BBC"
                ][:100]

            # Calculate liquidity for each symbol
            liquidity_data = []
            for symbol in hose_symbols:
                try:
                    q = Quote(symbol=symbol, source="vci")
                    df = q.history(
                        start=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                        end=datetime.now().strftime("%Y-%m-%d"),
                        interval="1D"
                    )
                    if df is not None and len(df) >= 10:
                        avg_volume = df['volume'].tail(20).mean()
                        avg_price = df['close'].tail(5).mean()
                        avg_value = avg_volume * avg_price  # VND

                        if avg_price > self.MIN_PRICE and avg_value > self.MIN_LIQUIDITY_BILLION * 1e9:
                            liquidity_data.append((symbol, avg_value))
                except:
                    continue

            # Sort by liquidity descending
            liquidity_data.sort(key=lambda x: x[1], reverse=True)

            # Return top 100
            return [s[0] for s in liquidity_data[:100]]

        except Exception as e:
            print(f"[Scanner] Error getting top 100: {e}")

        # Fallback: VN30 + một số midcap phổ biến
        return [
            "VNM", "VCB", "VHM", "VIC", "VPB", "BID", "TCB", "CTG", "MBB", "ACB",
            "STB", "HPG", "FPT", "MWG", "PNJ", "TPB", "SHB", "SSI", "MSN", "GAS",
            "PLX", "VRE", "VIB", "VJC", "SAB", "HDB", "LPB", "SSB", "GVR", "DGC",
            "KDH", "GMD", "SBT", "DGW", "CMG", "IMP", "VHC", "REE", "NT2", "BCM",
            "POW", "HAG", "NVL", "DIG", "ASM", "DRC", "HCM", "PVI", "BSR", "PVD",
            "VND", "OCB", "EIB", "KBS", "SHS", "VDS", "BVS", "TVS", "VIG", "VFM"
        ][:60]

    def _get_market_rsi(self) -> float:
        try:
            from vnstock import Quote
            q = Quote(symbol="VNINDEX", source="vci")
            df = q.history(
                start=(datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
                end=datetime.now().strftime("%Y-%m-%d"),
                interval="1D"
            )
            if df is not None and len(df) >= 15:
                close = df['close']
                delta = close.diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                return float(rsi.iloc[-1])
        except:
            pass
        return 50.0

    def _analyze_stock(self, symbol: str, market_rsi: float = 50.0) -> Optional[StockPick]:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                pick = StockPick(symbol=symbol, market_rsi=market_rsi)

                # Get price data
                df = None
                try:
                    from vnstock_data import Market
                    mkt = Market()
                    df = mkt.equity(symbol).ohlcv(
                        start=(datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d"),
                        end=datetime.now().strftime("%Y-%m-%d")
                    )
                except:
                    pass

                if df is None:
                    try:
                        from vnstock import Quote
                        q = Quote(symbol=symbol, source="vci")
                        df = q.history(
                            start=(datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d"),
                            end=datetime.now().strftime("%Y-%m-%d"),
                            interval="1D"
                        )
                    except:
                        return None

                if df is None or len(df) < 30:
                    return None

                close = df['close']
                high = df['high']
                low = df['low']
                volume = df['volume']

                # Current price & change
                pick.current_price = float(close.iloc[-1])
                if len(close) > 1:
                    prev_close = float(close.iloc[-2])
                    if prev_close > 0:
                        pick.change_percent = round(
                            (pick.current_price - prev_close) / prev_close * 100, 2
                        )

                # Calculate avg volume value
                avg_vol = volume.tail(20).mean()
                if avg_vol > 0 and pick.current_price > 0:
                    pick.avg_volume_value = round(avg_vol * pick.current_price / 1e9, 1)  # Tỷ VND

                # RSI
                if len(close) >= 14:
                    delta = close.diff()
                    gain = delta.where(delta > 0, 0).rolling(14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                    rs = gain / loss
                    pick.rsi = round(float((100 - (100 / (1 + rs))).iloc[-1]), 1)

                # MACD
                if len(close) >= 26:
                    ema12 = close.ewm(span=12, adjust=False).mean()
                    ema26 = close.ewm(span=26, adjust=False).mean()
                    macd_line = ema12 - ema26
                    signal_line = macd_line.ewm(span=9, adjust=False).mean()
                    pick.macd = round(float(macd_line.iloc[-1]), 2)
                    pick.macd_signal = round(float(signal_line.iloc[-1]), 2)

                # ADX + DI + ATR
                if len(df) >= 15:
                    high_diff = high.diff()
                    low_diff = -low.diff()
                    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
                    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

                    tr1 = high - low
                    tr2 = abs(high - close.shift(1))
                    tr3 = abs(low - close.shift(1))
                    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                    atr_series = tr.rolling(14).mean()
                    pick.atr = round(float(atr_series.iloc[-1]), 2)

                    # FIX: Đảm bảo ATR > 0
                    if pick.atr <= 0:
                        # Fallback: dùng 2% của giá
                        pick.atr = round(pick.current_price * 0.02, 2)

                    plus_di = 100 * (plus_dm.rolling(14).mean() / atr_series)
                    minus_di = 100 * (minus_dm.rolling(14).mean() / atr_series)
                    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
                    adx_values = dx.rolling(14).mean()

                    pick.adx = round(float(adx_values.iloc[-1]), 1)
                    pick.plus_di = round(float(plus_di.iloc[-1]), 1)
                    pick.minus_di = round(float(minus_di.iloc[-1]), 1)

                # CMF
                if len(df) >= 20:
                    mf_multiplier = ((close - low) - (high - close)) / (high - low)
                    mf_multiplier = mf_multiplier.fillna(0)
                    mf_volume = mf_multiplier * volume
                    total_mf = mf_volume.rolling(20).sum().iloc[-1]
                    total_vol = volume.rolling(20).sum().iloc[-1]
                    pick.cmf = round(total_mf / total_vol, 3) if total_vol > 0 else 0

                # Bollinger
                if len(close) >= 20:
                    bb_middle = close.rolling(20).mean()
                    bb_std = close.rolling(20).std()
                    pick.bb_upper = round(float((bb_middle + 2 * bb_std).iloc[-1]), 2)
                    pick.bb_middle = round(float(bb_middle.iloc[-1]), 2)
                    pick.bb_lower = round(float((bb_middle - 2 * bb_std).iloc[-1]), 2)

                # SMAs
                if len(close) >= 10:
                    pick.sma_10 = round(float(close.rolling(10).mean().iloc[-1]), 2)
                if len(close) >= 20:
                    pick.sma_20 = round(float(close.rolling(20).mean().iloc[-1]), 2)
                if len(close) >= 50:
                    pick.sma_50 = round(float(close.rolling(50).mean().iloc[-1]), 2)

                # Volume Ratio
                avg_volume = volume.tail(20).mean()
                if avg_volume > 0:
                    pick.volume_ratio = round(float(volume.iloc[-1]) / avg_volume, 2)

                # Get fundamental
                self._get_fundamental_data(pick)

                # Trading levels - PHẢI chạy TRƯỚC để có RR cho VETO
                self._calculate_trading_levels(pick, market_rsi)

                # VETO check - chạy SAU khi đã có RR
                self._check_veto(pick)

                # Evaluate criteria (AFTER VETO)
                self._evaluate_criteria(pick)

                # Scores
                self._calculate_scores(pick)

                # Trend
                self._detect_trend(pick)

                # Qualified
                self._check_short_term_qualified(pick)

                return pick

        except Exception as e:
            print(f"[Scanner] Error {symbol}: {e}")
            return None

    def _get_fundamental_data(self, pick: StockPick):
        """Lấy fundamental data"""
        fundamental_found = False

        try:
            from vnstock_data import Fundamental
            fun = Fundamental()
            ratios = fun.equity(pick.symbol).ratio()
            if ratios is not None and len(ratios) > 0:
                latest = ratios.iloc[-1]

                # P/E
                for col in ['pe', 'pe_ratio', 'p_e']:
                    if col in latest.index:
                        try:
                            val = float(latest[col])
                            if 0 < val < 1000:
                                pick.pe = val
                                fundamental_found = True
                                break
                        except:
                            pass

                # P/B
                for col in ['pb', 'pb_ratio', 'p_b']:
                    if col in latest.index:
                        try:
                            val = float(latest[col])
                            if 0 < val < 100:
                                pick.pb = val
                                fundamental_found = True
                                break
                        except:
                            pass

                # ROE
                for col in ['roe', 'roe_ratio', 'roe_d']:
                    if col in latest.index:
                        try:
                            val = float(latest[col])
                            if -100 < val < 100:
                                pick.roe = val
                                fundamental_found = True
                                break
                        except:
                            pass

        except:
            pass

        # Calculate ROE from P/B and P/E
        if pick.roe == 0 and pick.pe > 0 and pick.pb > 0:
            pick.roe = round((pick.pb / pick.pe) * 100, 2)
            fundamental_found = True

        pick.has_fundamental_data = fundamental_found
        if not fundamental_found:
            pick.is_high_risk = True

    def _check_veto(self, pick: StockPick):
        """VETO: CMF<0 OR R:R<1.0 OR inverted SL"""
        if pick.cmf < 0:
            pick.is_vetoed = True
            pick.veto_reason = "CMF Negative (Tiền chảy ra)"
        elif pick.has_inverted_sl:
            pick.is_vetoed = True
            pick.veto_reason = f"Inverted SL (Entry={pick.entry_price}, SL={pick.stop_loss})"
        elif pick.risk_reward_ratio < 1.0 and pick.risk_reward_ratio > 0:
            pick.is_vetoed = True
            pick.veto_reason = f"R:R = {pick.risk_reward_ratio:.1f} < 1.0"
        elif pick.risk_reward_ratio == 0:
            pick.is_vetoed = True
            pick.veto_reason = "R:R = 0 (Không tính được)"
        elif pick.atr == 0:
            pick.is_vetoed = True
            pick.veto_reason = "ATR = 0 (Thiếu dữ liệu biến động)"

    def _calculate_trading_levels(self, pick: StockPick, market_rsi: float = 50.0):
        """Tính Entry, SL, TP - FIX inverted SL - Đảm bảo min 3% distance"""
        if pick.current_price <= 0:
            return

        pick.entry_price = pick.current_price

        # FIX: Stop Loss phải cách Entry ít nhất 3%
        min_sl_distance = pick.current_price * 0.03  # 3% minimum

        # Tìm support tự nhiên
        bb_lower_support = pick.bb_lower if pick.bb_lower > 0 else 0
        sma20_support = pick.sma_20 if pick.sma_20 > 0 else 0
        atr_support = pick.current_price - (pick.atr * 2) if pick.atr > 0 else 0

        # Chọn support cao nhất nhưng vẫn cách Entry ít nhất 3%
        supports = [s for s in [bb_lower_support, sma20_support, atr_support] if s > 0]

        if supports:
            raw_sl = max(supports)
            # Đảm bảo cách Entry ít nhất 3%
            if pick.current_price - raw_sl < min_sl_distance:
                raw_sl = pick.current_price - min_sl_distance
        else:
            # Không có support → dùng 5% dưới Entry
            raw_sl = pick.current_price * 0.95
            pick.has_inverted_sl = True

        # Final check: SL phải < Entry
        if raw_sl >= pick.current_price:
            pick.has_inverted_sl = True
            raw_sl = pick.current_price * 0.95

        pick.stop_loss = round(raw_sl, 2)

        # Take Profit: BB Upper hoặc +10%
        bb_upper_tp = pick.bb_upper if pick.bb_upper > 0 else 0
        target_tp = pick.current_price * 1.10
        pick.take_profit = round(min(bb_upper_tp, target_tp) if bb_upper_tp > 0 else target_tp, 2)

        # R:R
        risk = pick.entry_price - pick.stop_loss
        reward = pick.take_profit - pick.entry_price
        if risk >= min_sl_distance:  # Đảm bảo risk >= 3%
            pick.risk_reward_ratio = round(reward / risk, 2)
        else:
            pick.risk_reward_ratio = 0

        # Est. Days
        if pick.atr > 0:
            price_diff = pick.take_profit - pick.entry_price
            if price_diff > 0:
                raw_days = price_diff / pick.atr
                # RSI > 80: cộng thêm 3 ngày
                if market_rsi > 80:
                    raw_days += 3
                pick.estimated_days_to_target = max(raw_days, self.MIN_HOLDING_DAYS)
                pick.estimated_days_to_target = round(pick.estimated_days_to_target, 1)

        if pick.estimated_days_to_target > self.SLOW_THRESHOLD_DAYS:
            pick.is_slow_mode = True

    def _evaluate_criteria(self, pick: StockPick):
        """10 tiêu chí - chỉ đánh giá khi không bị VETO"""
        criteria = []

        # Skip if vetoed
        if pick.is_vetoed:
            pick.criteria_met = 0
            pick.criteria_list = []
            return

        # 1. RSI Sweet Spot
        if 50 <= pick.rsi <= 65:
            criteria.append("RSI Sweet Spot (50-65)")

        # 2. ADX Strong
        if pick.adx > 20:
            criteria.append("ADX Strong (>20)")

        # 3. +DI > -DI
        if pick.plus_di > pick.minus_di:
            criteria.append("DI Bullish")

        # 4. CMF Positive (VETO nếu âm)
        if pick.cmf > 0:
            criteria.append("CMF Positive")

        # 5. Volume Active
        if pick.volume_ratio > 1.0:
            criteria.append("Volume Active")

        # 6. Above SMA20
        if pick.sma_20 > 0 and pick.current_price > pick.sma_20:
            criteria.append("Above SMA20")

        # 7. MACD Bullish
        if pick.macd > pick.macd_signal:
            criteria.append("MACD Bullish")

        # 8. R:R Good
        if pick.risk_reward_ratio >= 2.0:
            criteria.append("R:R Excellent (>=2.0)")
        elif pick.risk_reward_ratio >= 1.5:
            criteria.append("R:R Good (>=1.5)")
        elif pick.risk_reward_ratio >= 1.0:
            criteria.append("R:R OK (>=1.0)")

        # 9. F-Score OK (nếu có data)
        if pick.has_fundamental_data and pick.f_score >= 2:
            criteria.append("F-Score OK (>=2)")

        # 10. Fast Holding
        if 0 < pick.estimated_days_to_target <= self.SLOW_THRESHOLD_DAYS:
            criteria.append("Fast Holding (<=10d)")

        pick.criteria_met = len(criteria)
        pick.criteria_list = criteria

    def _calculate_scores(self, pick: StockPick):
        """Tính điểm"""
        # VETO
        if pick.is_vetoed:
            pick.technical_score = 35
            pick.fundamental_score = 40
            pick.master_score = 37
            pick.signal = "WAIT"
            return

        tech_score = 50

        # RSI
        if 50 <= pick.rsi <= 65:
            tech_score += 12 if 55 <= pick.rsi <= 62 else 8
        elif pick.rsi > 70:
            tech_score -= 15
        elif pick.rsi > 65:
            tech_score -= 8
        elif pick.rsi < 50:
            tech_score += 4

        # ADX
        if pick.adx > 25:
            tech_score += 12
        elif pick.adx > 20:
            tech_score += 8
        elif pick.adx > 15:
            tech_score += 4

        # +DI
        if pick.plus_di > pick.minus_di:
            diff = pick.plus_di - pick.minus_di
            tech_score += 10 if diff > 10 else (6 if diff > 5 else 3)
        else:
            tech_score -= 8

        # MACD
        if pick.macd > pick.macd_signal:
            tech_score += 8
        elif pick.macd > 0:
            tech_score += 4

        # CMF
        if pick.cmf > 0.1:
            tech_score += 12
        elif pick.cmf > 0:
            tech_score += 8
        else:
            tech_score -= 15

        # SMA
        if pick.sma_20 > 0:
            if pick.current_price > pick.sma_20 > pick.sma_50:
                tech_score += 10
            elif pick.current_price > pick.sma_20:
                tech_score += 6
            else:
                tech_score -= 8

        # Volume
        if pick.volume_ratio > 2:
            tech_score += 8
        elif pick.volume_ratio > 1.5:
            tech_score += 5
        elif pick.volume_ratio > 1.3:
            tech_score += 3

        # R:R
        if pick.risk_reward_ratio >= 2.0:
            tech_score += 10
        elif pick.risk_reward_ratio >= 1.5:
            tech_score += 6
        elif pick.risk_reward_ratio >= 1.0:
            tech_score += 3
        else:
            tech_score -= 10

        # Inverted SL penalty
        if pick.has_inverted_sl:
            tech_score -= 10

        # FAST bonus
        if pick.is_fast_pick:
            tech_score += 5

        # SLOW penalty
        if pick.is_slow_mode:
            tech_score -= 8

        pick.technical_score = max(0, min(100, tech_score))

        # Fund Score
        fund_score = 50

        if 0 < pick.pe <= 10:
            fund_score += 10
        elif 10 < pick.pe <= 15:
            fund_score += 7
        elif 15 < pick.pe <= 20:
            fund_score += 3
        elif pick.pe > 25:
            fund_score -= 5

        if pick.roe > 20:
            fund_score += 10
        elif pick.roe > 15:
            fund_score += 7
        elif pick.roe > 10:
            fund_score += 4
        elif pick.roe > 0:
            fund_score += 1

        if 0 < pick.pb <= 1:
            fund_score += 5
        elif 1 < pick.pb <= 2:
            fund_score += 3
        elif pick.pb > 3:
            fund_score -= 3

        # Missing data penalty
        if not pick.has_fundamental_data:
            fund_score -= 20

        pick.fundamental_score = max(0, min(100, fund_score))

        # Master Score
        pick.master_score = int(pick.technical_score * 0.7 + pick.fundamental_score * 0.3)

        # Signal - SELL ZONE cần khắt khe hơn
        # Trong SELL ZONE (RSI > 70), chỉ mạnh dạn BUY khi thực sự tốt
        is_sell_zone = pick.market_rsi > 70

        if pick.criteria_met >= 9 and not pick.is_slow_mode:
            # SELL ZONE: cần thêm ADX>25 và Volume>1.0x
            if is_sell_zone:
                if pick.adx > 25 and pick.volume_ratio > 1.0:
                    pick.signal = "STRONG_BUY"
                elif pick.adx > 20:
                    pick.signal = "BUY"  # Hạ xuống BUY
                else:
                    pick.signal = "WATCH"
            else:
                pick.signal = "STRONG_BUY"
        elif pick.master_score >= 75:
            if is_sell_zone and (pick.adx <= 25 or pick.volume_ratio <= 1.0):
                pick.signal = "BUY" if pick.master_score >= 65 else "WATCH"
            else:
                pick.signal = "STRONG_BUY"
        elif pick.master_score >= 65:
            pick.signal = "BUY" if not is_sell_zone else "ACCUMULATE"
        elif pick.master_score >= 55:
            pick.signal = "ACCUMULATE"
        elif pick.master_score >= 45:
            pick.signal = "NEUTRAL"
        else:
            pick.signal = "WAIT"

    def _detect_trend(self, pick: StockPick):
        if pick.sma_20 > 0 and pick.sma_50 > 0:
            if pick.current_price > pick.sma_20 > pick.sma_50:
                pick.trend = "UPTREND"
            elif pick.current_price < pick.sma_20 < pick.sma_50:
                pick.trend = "DOWNTREND"
            else:
                pick.trend = "SIDEWAYS"
        elif pick.sma_20 > 0:
            pick.trend = "UPTREND" if pick.current_price > pick.sma_20 else "DOWNTREND"

    def _check_short_term_qualified(self, pick: StockPick):
        """Qualified T+: >= 9/10 + không VETO + không SLOW + có fundamental"""
        if pick.is_vetoed or pick.is_slow_mode:
            pick.is_short_term_qualified = False
            return

        conditions = [
            pick.criteria_met >= 9,
            pick.risk_reward_ratio >= 1.0,
            pick.cmf > 0,
            pick.current_price > pick.sma_20 if pick.sma_20 > 0 else False,
        ]

        pick.is_short_term_qualified = all(conditions)

    def _analyze_market_status(self, result: ScanResult):
        eligible = result.total_scanned - result.vetoed_count
        if eligible <= 0:
            result.market_status = "NO_SIGNAL"
            return

        bullish_ratio = result.bullish_count / eligible

        if bullish_ratio > 0.6:
            result.market_status = "STRONG_BULL"
        elif bullish_ratio > 0.4:
            result.market_status = "BULL"
        elif bullish_ratio < 0.2:
            result.market_status = "BEAR"
        else:
            result.market_status = "NEUTRAL"

    def _generate_market_warnings(self, result: ScanResult):
        if result.market_rsi > 80:
            result.market_overbought_warning = True
            result.market_warning_message = (
                f"🚨 EXTREME OVERBOUGHT! VNIndex RSI: {result.market_rsi:.0f}. "
                f"Thị trường quá mua nguy hiểm. Chỉ chốt lời, không mua mới!"
            )
        elif result.market_rsi > 75:
            result.market_overbought_warning = True
            result.market_warning_message = (
                f"⚠️ THỊ TRƯỜNG QUÁ MUA! VNIndex RSI: {result.market_rsi:.0f}. "
                f"Ưu tiên tỷ trọng thấp hoặc chốt lời sớm."
            )
        elif result.market_rsi > 70:
            result.market_overbought_warning = True
            result.market_warning_message = (
                f"⚠️ CẢNH BÁO: VNIndex RSI {result.market_rsi:.0f} - Thị trường quá mua. "
                f"Chỉ nên giải ngân 20-30% tiền mặt."
            )


_scanner_instance: Optional[Top100Scanner] = None


def get_top100_scanner() -> Top100Scanner:
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = Top100Scanner()
    return _scanner_instance


def scan_top100(force_refresh: bool = False) -> ScanResult:
    scanner = get_top100_scanner()
    return scanner.scan(force_refresh=force_refresh)


# Backward compatibility
VN30Scanner = Top100Scanner
scan_vn30 = scan_top100
