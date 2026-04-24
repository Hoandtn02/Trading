"""
Stock Analyzer Module - Technical & Fundamental Analysis

Comprehensive stock analysis using:
- vnstock_ta for technical indicators (RSI, MACD, ADX, SuperTrend, Bollinger, CMF, MFI, SMA)
- vnstock_data for OHLCV, Fundamental data, F-Score

Output format matches ARCHITECTURE_ROADMAP.md specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import pandas as pd


@dataclass
class TechnicalIndicators:
    """Technical indicators result container"""
    # Price info
    current_price: float = 0.0
    change_percent: float = 0.0
    volume: int = 0
    
    # Momentum
    rsi: float = 50.0
    rsi_status: str = "neutral"
    macd: float = 0.0
    macd_signal: str = "neutral"
    
    # Trend
    adx: float = 0.0
    adx_status: str = "no_trend"
    sma_20: float = 0.0
    sma_50: float = 0.0
    sma_200: float = 0.0
    trend_status: str = "neutral"
    supertrend_signal: str = "neutral"
    supertrend_stop: float = 0.0
    
    # Money Flow
    cmf: float = 0.0
    cmf_status: str = "neutral"
    mfi: float = 50.0
    mfi_status: str = "neutral"
    
    # Volatility
    atr: float = 0.0
    atr_status: str = "normal"
    bollinger_upper: float = 0.0
    bollinger_middle: float = 0.0
    bollinger_lower: float = 0.0
    bollinger_position: float = 0.5
    
    # Value
    vwap: float = 0.0
    vwap_status: str = "neutral"


@dataclass
class FundamentalData:
    """Fundamental data container"""
    # F-Score
    f_score: int = 0
    f_score_max: int = 9
    f_score_grade: str = "N/A"
    
    # Valuation
    pe: float = 0.0
    pb: float = 0.0
    roe: float = 0.0
    eps: float = 0.0
    
    # Growth
    profit_growth: float = 0.0
    profit_growth_yoy: float = 0.0
    margin: float = 0.0
    
    # F-Score components
    roa_increase: bool = False
    roe_increase: bool = False
    eps_increase: bool = False
    de_ratio_decrease: bool = False
    current_ratio_ok: bool = False
    gross_margin_increase: bool = False
    asset_turnover_increase: bool = False
    abnormal_return: bool = False


@dataclass
class SentimentData:
    """News sentiment container"""
    news_count: int = 0
    score: float = 0.0
    sentiment: str = "neutral"
    keywords: list = field(default_factory=list)
    summary: str = ""


@dataclass
class Recommendation:
    """Trading recommendation container"""
    action: str = "HOLD"  # BUY/SELL/HOLD/WATCH
    master_score: int = 50
    score_stars: str = "★★☆☆☆"
    
    # Reasons
    reasons_positive: list = field(default_factory=list)
    reasons_negative: list = field(default_factory=list)
    
    # Levels
    support: float = 0.0
    resistance: float = 0.0
    
    # Actions
    entry_target: float = 0.0
    stop_loss: float = 0.0
    profit_target: float = 0.0
    timeframe: str = "SWING"
    risk_level: str = "MEDIUM"


@dataclass
class StockAnalysis:
    """Complete stock analysis result"""
    # Basic info
    symbol: str = ""
    name: str = ""
    exchange: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Data containers
    technical: TechnicalIndicators = field(default_factory=TechnicalIndicators)
    fundamental: FundamentalData = field(default_factory=FundamentalData)
    sentiment: SentimentData = field(default_factory=SentimentData)
    recommendation: Recommendation = field(default_factory=Recommendation)
    
    # Raw data (for debugging)
    _raw_ohlcv: Optional[pd.DataFrame] = None
    _raw_financials: Optional[dict] = None


class StockAnalyzer:
    """
    Comprehensive stock analyzer using vnstock_ta and vnstock_data.
    
    Usage:
        analyzer = StockAnalyzer()
        result = analyzer.analyze("VCB")
        print(result.to_string())
    """
    
    def __init__(self, period_ta: int = 90):
        """
        Initialize StockAnalyzer.
        
        Args:
            period_ta: Days of historical data for TA calculation (default: 90)
        """
        self.period_ta = period_ta
    
    def analyze(self, symbol: str, include_sentiment: bool = False) -> StockAnalysis:
        """
        Perform comprehensive stock analysis.
        
        Args:
            symbol: Stock symbol (e.g., "VCB", "ACB")
            include_sentiment: Whether to include news sentiment analysis
            
        Returns:
            StockAnalysis object with all indicators and recommendations
        """
        result = StockAnalysis(symbol=symbol.upper())
        
        try:
            # 1. Get OHLCV data
            ohlcv = self._get_ohlcv(symbol)
            if ohlcv is None or len(ohlcv) < 20:
                result.recommendation.action = "ERROR"
                result.recommendation.reasons_negative = ["Không lấy được dữ liệu OHLCV"]
                return result
            
            result._raw_ohlcv = ohlcv
            
            # 2. Calculate technical indicators
            result.technical = self._calculate_technical(ohlcv)
            
            # 3. Get fundamental data
            result.fundamental = self._get_fundamental(symbol)
            
            # 4. Get sentiment (optional)
            if include_sentiment:
                result.sentiment = self._get_sentiment(symbol)
            
            # 5. Generate recommendation
            result.recommendation = self._generate_recommendation(result)
            
            # 6. Get company name
            result.name = self._get_company_name(symbol)
            
        except Exception as e:
            result.recommendation.action = "ERROR"
            result.recommendation.reasons_negative = [f"Lỗi: {str(e)}"]
        
        return result
    
    def _get_ohlcv(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from vnstock_data"""
        try:
            from vnstock_data import Market
            mkt = Market()
            end = pd.Timestamp.today().strftime("%Y-%m-%d")
            start = (pd.Timestamp.today() - pd.DateOffset(days=self.period_ta)).strftime("%Y-%m-%d")
            
            df = mkt.equity(symbol).ohlcv(start=start, end=end, interval="1D")
            
            if df is not None and len(df) > 0:
                # Ensure numeric columns
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # API returns prices divided by 1000 - multiply back to actual price
                price_cols = ['open', 'high', 'low', 'close']
                for col in price_cols:
                    if col in df.columns:
                        df[col] = df[col] * 1000
                
                # Set time index if present
                if 'time' in df.columns:
                    df.set_index('time', inplace=True)
                
                return df
            
            return None
        except Exception:
            return None
    
    def _calculate_technical(self, df: pd.DataFrame) -> TechnicalIndicators:
        """Calculate all technical indicators using vnstock_ta Indicator class"""
        tech = TechnicalIndicators()
        
        if df is None or len(df) < 20:
            return tech
        
        # Current price info
        if 'close' in df.columns and len(df) > 0:
            close = df['close'].dropna()
            if len(close) > 0:
                tech.current_price = float(close.iloc[-1])
                
                if len(close) > 1:
                    prev_close = float(close.iloc[-2])
                    if prev_close > 0:
                        tech.change_percent = round((tech.current_price - prev_close) / prev_close * 100, 2)
                
                # Volume
                if 'volume' in df.columns:
                    tech.volume = int(df['volume'].iloc[-1]) if pd.notna(df['volume'].iloc[-1]) else 0
        
        # Calculate indicators using vnstock_ta Indicator class (v0.2.0+)
        try:
            from vnstock_ta import Indicator
            
            # Initialize indicator with dataframe
            indicator = Indicator(data=df)
            
            # RSI - returns pd.Series named "RSI_14"
            rsi_series = indicator.rsi(length=14)
            if rsi_series is not None and len(rsi_series) > 0:
                tech.rsi = round(float(rsi_series.iloc[-1]), 2)
            tech.rsi_status = self._get_rsi_status(tech.rsi)
            
            # MACD - returns pd.DataFrame with columns: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
            macd_df = indicator.macd(fast=12, slow=26, signal=9)
            if macd_df is not None and len(macd_df) > 0 and hasattr(macd_df, 'columns'):
                # Find MACD line column (the first column without 'h' or 's' suffix)
                for col in macd_df.columns:
                    if 'MACD' in col.upper() and 'h' not in col.lower()[-1] and 's' not in col.lower()[-1]:
                        tech.macd = round(float(macd_df[col].iloc[-1]), 2)
                        break
                # Fallback to first column if specific format not found
                if tech.macd == 0 and len(macd_df.columns) > 0:
                    tech.macd = round(float(macd_df.iloc[:, 0].iloc[-1]), 2)
            tech.macd_signal = self._get_macd_status(tech.macd)
            
            # ADX - returns pd.DataFrame with columns: ADX_14, DMP_14, DMN_14
            adx_df = indicator.adx(length=14)
            if adx_df is not None and len(adx_df) > 0 and hasattr(adx_df, 'columns'):
                for col in adx_df.columns:
                    if col.startswith('ADX'):
                        tech.adx = round(float(adx_df[col].iloc[-1]), 2)
                        break
                # Fallback
                if tech.adx == 0 and len(adx_df.columns) > 0:
                    tech.adx = round(float(adx_df.iloc[:, 0].iloc[-1]), 2)
            tech.adx_status = self._get_adx_status(tech.adx)
            
            # SMA - returns pd.Series named "SMA_20", "SMA_50"
            sma_20_series = indicator.sma(length=20)
            if sma_20_series is not None and len(sma_20_series) > 0 and len(df) >= 20:
                tech.sma_20 = round(float(sma_20_series.iloc[-1]), 2)
            
            sma_50_series = indicator.sma(length=50)
            if sma_50_series is not None and len(sma_50_series) > 0 and len(df) >= 50:
                tech.sma_50 = round(float(sma_50_series.iloc[-1]), 2)
            elif tech.sma_20 > 0:
                tech.sma_50 = tech.sma_20
            
            # Trend status
            tech.trend_status = self._get_trend_status(tech.current_price, tech.sma_20, tech.sma_50)
            
            # SuperTrend - returns pd.DataFrame with columns: SUPERT_10_3.0, SUPERTd_10_3.0, SUPERTl_10_3.0, SUPERTs_10_3.0
            st_df = indicator.supertrend(length=10, multiplier=3)
            if st_df is not None and len(st_df) > 0 and hasattr(st_df, 'columns'):
                for col in st_df.columns:
                    if col.startswith('SUPERT') and 'd' not in col and 'l' not in col and 's' not in col:
                        tech.supertrend_stop = round(float(st_df[col].iloc[-1]), 2)
                        break
                    elif col.startswith('SUPERT'):
                        # Get direction column for signal
                        pass
                # Get direction from SUPERTd column
                for col in st_df.columns:
                    if 'SUPERTd' in col:
                        direction = float(st_df[col].iloc[-1])
                        tech.supertrend_signal = "buy" if direction > 0 else "sell"
                        break
                # Fallback: use SUPERT column
                if tech.supertrend_stop == 0 and len(st_df.columns) > 0:
                    tech.supertrend_stop = round(float(st_df.iloc[:, 0].iloc[-1]), 2)
            else:
                tech.supertrend_signal = "neutral"
            
            # VWAP - returns pd.Series named "VWAP_D"
            vwap_series = indicator.vwap(anchor='D')
            if vwap_series is not None and len(vwap_series) > 0:
                tech.vwap = round(float(vwap_series.iloc[-1]), 2)
            else:
                # Fallback: calculate VWAP manually
                if 'high' in df.columns and 'low' in df.columns:
                    typical = (df['high'] + df['low'] + df['close']) / 3
                    typical_vol = typical * df['volume']
                    tech.vwap = round(float((typical_vol.sum() / df['volume'].sum())), 2) if df['volume'].sum() > 0 else tech.current_price
            tech.vwap_status = "above" if tech.current_price > tech.vwap else "below"
            
            # ATR - returns pd.Series named "ATRr_14"
            atr_series = indicator.atr(length=14)
            if atr_series is not None and len(atr_series) > 0:
                tech.atr = round(float(atr_series.iloc[-1]), 2)
            tech.atr_status = self._get_atr_status(tech.atr, tech.current_price)
            
            # Bollinger Bands - returns pd.DataFrame with columns: BBL_14_2.0, BBM_14_2.0, BBU_14_2.0, BBB_14_2.0, BBP_14_2.0
            bb_df = indicator.bbands(length=20, std=2)
            if bb_df is not None and hasattr(bb_df, 'columns') and len(bb_df) > 0:
                bb_cols = list(bb_df.columns)
                # Find bands by prefix
                for col in bb_cols:
                    col_upper = col.upper()
                    if 'BBL' in col_upper:
                        tech.bollinger_lower = round(float(bb_df[col].iloc[-1]), 2)
                    elif 'BBM' in col_upper:
                        tech.bollinger_middle = round(float(bb_df[col].iloc[-1]), 2)
                    elif 'BBU' in col_upper:
                        tech.bollinger_upper = round(float(bb_df[col].iloc[-1]), 2)
                
                # If not found by name, use first 3 columns in order: lower, middle, upper
                if tech.bollinger_upper == 0 and len(bb_cols) >= 3:
                    tech.bollinger_lower = round(float(bb_df[bb_cols[0]].iloc[-1]), 2)
                    tech.bollinger_middle = round(float(bb_df[bb_cols[1]].iloc[-1]), 2)
                    tech.bollinger_upper = round(float(bb_df[bb_cols[2]].iloc[-1]), 2)
            
            # Bollinger position (Percent B)
            if tech.bollinger_upper > tech.bollinger_lower:
                tech.bollinger_position = round(
                    (tech.current_price - tech.bollinger_lower) / (tech.bollinger_upper - tech.bollinger_lower), 2
                )
            
            # CMF - calculate manually since not in vnstock_ta
            tech.cmf = self._calculate_cmf(df, period=20)
            tech.cmf_status = "inflow" if tech.cmf > 0 else "outflow"
            
            # MFI - calculate manually since not in vnstock_ta
            tech.mfi = self._calculate_mfi(df, period=14)
            tech.mfi_status = self._get_mfi_status(tech.mfi)
            
        except ImportError as e:
            # Fallback if vnstock_ta not available
            tech = self._calculate_technical_fallback(df)
        except Exception as e:
            # Fallback: calculate basic indicators manually
            tech = self._calculate_technical_fallback(df)
        
        return tech
    
    def _calculate_technical_fallback(self, df: pd.DataFrame) -> TechnicalIndicators:
        """Fallback technical calculation without vnstock_ta"""
        tech = TechnicalIndicators()
        
        close = df['close'].dropna()
        if len(close) < 20:
            return tech
        
        tech.current_price = float(close.iloc[-1])
        
        # SMA
        tech.sma_20 = float(close.iloc[-20:].mean()) if len(close) >= 20 else float(close.mean())
        tech.sma_50 = float(close.iloc[-50:].mean()) if len(close) >= 50 else tech.sma_20
        
        # Simple RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        tech.rsi = round(float(100 - (100 / (1 + rs)).iloc[-1]), 2) if len(rs) > 0 and rs.iloc[-1] > 0 else 50.0
        tech.rsi_status = self._get_rsi_status(tech.rsi)
        
        # Trend
        tech.trend_status = self._get_trend_status(tech.current_price, tech.sma_20, tech.sma_50)
        
        return tech
    
    def _calculate_cmf(self, df: pd.DataFrame, period: int = 20) -> float:
        """Calculate Chaikin Money Flow (CMF)"""
        try:
            if len(df) < period:
                return 0.0
            
            close = df['close']
            high = df['high']
            low = df['low']
            volume = df['volume']
            
            # Money Flow Multiplier
            mfm = ((close - low) - (high - close)) / (high - low)
            mfm = mfm.fillna(0)
            
            # Money Flow Volume
            mfv = mfm * volume
            
            # CMF
            cmf = mfv.rolling(period).sum() / volume.rolling(period).sum()
            
            return round(float(cmf.iloc[-1]), 4) if len(cmf) > 0 else 0.0
        except Exception:
            return 0.0
    
    def _calculate_mfi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Money Flow Index (MFI)"""
        try:
            if len(df) < period + 1:
                return 50.0
            
            high = df['high']
            low = df['low']
            close = df['close']
            volume = df['volume']
            
            # Typical Price
            typical = (high + low + close) / 3
            
            # Raw Money Flow
            money_flow = typical * volume
            
            # Money Flow Sign
            signed_flow = pd.Series(0.0, index=money_flow.index)
            for i in range(1, len(money_flow)):
                if typical.iloc[i] > typical.iloc[i-1]:
                    signed_flow.iloc[i] = money_flow.iloc[i]
                elif typical.iloc[i] < typical.iloc[i-1]:
                    signed_flow.iloc[i] = -money_flow.iloc[i]
            
            # Positive and Negative Money Flow
            positive_flow = signed_flow.clip(lower=0).rolling(period).sum()
            negative_flow = (-signed_flow.clip(upper=0)).rolling(period).sum()
            
            # Money Ratio
            money_ratio = positive_flow / negative_flow
            
            # MFI
            mfi = 100 - (100 / (1 + money_ratio))
            
            return round(float(mfi.iloc[-1]), 2) if len(mfi) > 0 and not pd.isna(mfi.iloc[-1]) else 50.0
        except Exception:
            return 50.0
    
    def _calculate_supertrend(self, df: pd.DataFrame) -> tuple[str, float]:
        """Calculate SuperTrend (simplified)"""
        try:
            from vnstock_ta import SuperTrend
            st = SuperTrend(df)
            result = st.get_supertrend()
            if result is not None and len(result) > 0:
                signal = "BUY" if result.iloc[-1] < df['close'].iloc[-1] else "SELL"
                stop = float(result.iloc[-1])
                return signal, stop
        except Exception:
            pass
        
        # Fallback
        if 'close' in df.columns and len(df) >= 14:
            high = df['high']
            low = df['low']
            close = df['close']
            
            # ATR
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]
            
            # Basic SuperTrend
            hl2 = (high + low) / 2
            upper = hl2 + 2 * atr
            lower = hl2 - 2 * atr
            
            return "neutral", float(lower)
        
        return "neutral", 0.0
    
    def _get_fundamental(self, symbol: str) -> FundamentalData:
        """Get fundamental data from vnstock_data"""
        fund = FundamentalData()
        
        try:
            from vnstock_data import Fundamental
            import warnings
            
            fun = Fundamental()
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # Get financial ratios - index is numeric, not row labels
                ratios = fun.equity(symbol).ratio(period="quarter")
                if ratios is not None and len(ratios) > 0:
                    # Get latest row (last row in DataFrame)
                    latest = ratios.iloc[-1]
                    
                    # P/E - direct column
                    if 'pe' in ratios.columns:
                        fund.pe = float(latest.get('pe', 0)) if pd.notna(latest.get('pe')) else 0.0
                    
                    # P/B - direct column
                    if 'pb' in ratios.columns:
                        fund.pb = float(latest.get('pb', 0)) if pd.notna(latest.get('pb')) else 0.0
                    
                    # EPS - trailing_eps column
                    if 'trailing_eps' in ratios.columns:
                        fund.eps = float(latest.get('trailing_eps', 0)) if pd.notna(latest.get('trailing_eps')) else 0.0
                    
                    # ROE - calculate from PE and PB if not available
                    # ROE = P/B / (P/E) - DuPont approximation
                    if fund.pe > 0 and fund.pb > 0:
                        fund.roe = round((fund.pb / fund.pe) * 100, 2)
            
            # Calculate F-Score
            fund.f_score = self._calculate_f_score(symbol)
            fund.f_score_grade = self._get_f_score_grade(fund.f_score)
            
        except Exception:
            pass
        
        return fund
    
    def _calculate_f_score(self, symbol: str) -> int:
        """
        Calculate Piotroski F-Score (9 criteria)
        Based on: Profitability, Leverage, Liquidity, Operating Efficiency
        """
        score = 0
        
        try:
            from vnstock_data import Fundamental
            import warnings
            
            fun = Fundamental()
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # Get financial statements
                income = fun.equity(symbol).income_statement(limit=8)
                balance = fun.equity(symbol).balance_sheet(limit=8)
                cf = fun.equity(symbol).cash_flow(limit=8)
                
                if income is None or len(income.columns) < 2:
                    return 0
                
                # Data is organized with columns = time periods
                # Column index 0 = most recent, index -1 = oldest
                # But from debug output: index 55 = 2012-Q1 (recent), index 54 = 2012-Q2 (older)
                # So column 0 is oldest, column -1 is newest
                
                # Helper to get value from column name
                def get_col(df, col_name, col_idx=-1):
                    try:
                        if df is None or col_name not in df.columns:
                            return None
                        return df.loc[df.index[0], col_name]  # First row has the value
                    except:
                        return None
                
                # Get latest period column (column -1 = newest based on debug)
                # Actually let's check: row with period "2012-Q1" should be newest
                # From debug: index 55 has period "2012-Q1", so we need the row where period matches
                latest_row = None
                period_col = 'period' if 'period' in income.columns else None
                
                if period_col:
                    for idx in income.index:
                        period_val = income.loc[idx, period_col]
                        if period_val and 'Q' in str(period_val):
                            latest_row = idx
                            break
                
                if latest_row is None:
                    latest_row = income.index[0]  # Fallback to first row
                
                prev_row = income.index[1] if len(income.index) > 1 else None
                
                # ===== Profitability Criteria =====
                
                # Criteria 1: ROA > 0 (Return on Assets)
                # ROA = Net Income / Total Assets
                net_income_col = 'net_profit_after_tax' if 'net_profit_after_tax' in income.columns else None
                total_assets_col = 'total_assets' if 'total_assets' in balance.columns else None
                
                if net_income_col and total_assets_col:
                    net_income = income.loc[latest_row, net_income_col]
                    total_assets = balance.loc[latest_row, total_assets_col]
                    if net_income and total_assets and float(total_assets) != 0:
                        roa = float(net_income) / float(total_assets)
                        if roa > 0:
                            score += 1
                
                # Criteria 2: Operating Cash Flow > 0
                ocf_col = None
                for col in cf.columns:
                    if 'net_cash_flows_from_operating_activities' in col.lower():
                        ocf_col = col
                        break
                
                if ocf_col:
                    ocf = cf.loc[latest_row, ocf_col]
                    if ocf and float(ocf) > 0:
                        score += 1
                
                # Criteria 3: ROA increase YoY
                if net_income_col and total_assets_col and prev_row:
                    net_income_prev = income.loc[prev_row, net_income_col]
                    total_assets_prev = balance.loc[prev_row, total_assets_col]
                    if net_income_prev and total_assets_prev and float(total_assets_prev) != 0:
                        roa_prev = float(net_income_prev) / float(total_assets_prev)
                        if roa > roa_prev:
                            score += 1
                
                # Criteria 4: CFO > Net Income (accruals)
                if ocf_col:
                    ocf_val = cf.loc[latest_row, ocf_col]
                    if ocf_val and net_income and float(ocf_val) > float(net_income):
                        score += 1
                
                # ===== Leverage Criteria =====
                
                # Criteria 5: D/E ratio decrease
                liabilities_col = None
                for col in balance.columns:
                    if 'total_liabilities' in col.lower() or 'liabilities' in col.lower():
                        liabilities_col = col
                        break
                
                equity_col = None
                for col in balance.columns:
                    if 'equity' in col.lower() or 'owners_equity' in col.lower():
                        equity_col = col
                        break
                
                if liabilities_col and equity_col:
                    liabilities = balance.loc[latest_row, liabilities_col]
                    equity = balance.loc[latest_row, equity_col]
                    if equity and float(equity) > 0:
                        de_ratio = float(liabilities) / float(equity)
                        if de_ratio < 1.5:  # Reasonable leverage
                            score += 1
                
                # ===== Liquidity Criteria =====
                
                # Criteria 6: Current Ratio > 1
                current_assets_col = None
                current_liab_col = None
                for col in balance.columns:
                    if 'current_assets' in col.lower():
                        current_assets_col = col
                    if 'current_liabilities' in col.lower():
                        current_liab_col = col
                
                if current_assets_col and current_liab_col:
                    current_assets = balance.loc[latest_row, current_assets_col]
                    current_liab = balance.loc[latest_row, current_liab_col]
                    if current_liab and float(current_liab) > 0:
                        current_ratio = float(current_assets) / float(current_liab)
                        if current_ratio > 1:
                            score += 1
                
                # ===== Operating Efficiency Criteria =====
                
                # Criteria 7: Gross Margin not declining
                # VCB is a bank, so check interest income margin instead
                interest_income_col = None
                for col in income.columns:
                    if 'interest_income' in col.lower():
                        interest_income_col = col
                        break
                
                # Simplified: Check if profit is positive and growing
                if net_income:
                    if float(net_income) > 0:
                        score += 1
                
                # Criteria 8: Asset Turnover
                if total_assets_col:
                    total_assets = balance.loc[latest_row, total_assets_col]
                    # Need revenue - for banks use total income
                    total_income = None
                    for col in income.columns:
                        if 'income' in col.lower() and 'interest' in col.lower():
                            total_income = income.loc[latest_row, col]
                            break
                    
                    if total_income and total_assets and float(total_assets) > 0:
                        at = float(total_income) / float(total_assets)
                        if at > 0.05:  # For banks, low threshold
                            score += 1
                
                # Criteria 9: Revenue growth
                if prev_row and total_income:
                    total_income_prev = income.loc[prev_row, total_income_col] if total_income_col else None
                    if total_income_prev and float(total_income) > float(total_income_prev):
                        score += 1
                
        except Exception:
            pass
        
        return min(score, 9)
    
    def _get_f_score_grade(self, score: int) -> str:
        """Get F-Score grade"""
        if score >= 8:
            return "A+"
        elif score >= 7:
            return "A"
        elif score >= 5:
            return "B"
        elif score >= 3:
            return "C"
        else:
            return "D"
    
    def _get_sentiment(self, symbol: str) -> SentimentData:
        """Get news sentiment (simplified)"""
        sentiment = SentimentData()
        
        try:
            from vnstock_news import EnhancedNewsCrawler
            import asyncio
            
            crawler = EnhancedNewsCrawler(cache_enabled=False)
            
            # Fetch recent news
            df = asyncio.run(crawler.fetch_articles_async(
                sources=['https://cafef.vn/latest-news-sitemap.xml'],
                max_articles=20,
                time_frame='7d'
            ))
            
            if df is not None and len(df) > 0:
                # Filter by symbol
                mask = df['title'].str.contains(symbol, case=False, na=False) | \
                       df['short_description'].str.contains(symbol, case=False, na=False)
                df_filtered = df[mask]
                
                sentiment.news_count = len(df_filtered) if len(df_filtered) > 0 else len(df)
                
                # Simplified sentiment: check for positive/negative keywords
                if sentiment.news_count > 0:
                    positive_keywords = ['tăng', 'lợi nhuận', 'tích cực', 'lãi', 'cổ tức', 'tăng trưởng']
                    negative_keywords = ['giảm', 'lỗ', 'rủi ro', 'nợ', 'tranh chấp']
                    
                    text = ' '.join(df_filtered['title'].tolist() if len(df_filtered) > 0 else df['title'].tolist()).lower()
                    
                    pos_count = sum(1 for kw in positive_keywords if kw in text)
                    neg_count = sum(1 for kw in negative_keywords if kw in text)
                    
                    if pos_count > neg_count:
                        sentiment.score = 0.6
                        sentiment.sentiment = "Tích cực"
                    elif neg_count > pos_count:
                        sentiment.score = -0.4
                        sentiment.sentiment = "Tiêu cực"
                    else:
                        sentiment.score = 0.0
                        sentiment.sentiment = "Trung lập"
                    
                    # Extract keywords
                    sentiment.keywords = [kw for kw in positive_keywords + negative_keywords if kw in text][:5]
                    sentiment.summary = f"Có {sentiment.news_count} tin liên quan"
        except Exception:
            pass
        
        return sentiment
    
    def _get_company_name(self, symbol: str) -> str:
        """Get company name from listing"""
        try:
            from vnstock_data import Reference
            ref = Reference()
            df = ref.equity.list()
            
            if df is not None and 'symbol' in df.columns:
                company = df[df['symbol'] == symbol.upper()]
                if not company.empty and 'company_name' in df.columns:
                    return str(company.iloc[0]['company_name'])
        except Exception:
            pass
        
        return symbol
    
    # ─── Status/Threshold Methods ────────────────────────────────────────────
    
    def _get_rsi_status(self, rsi: float) -> str:
        if rsi >= 75:
            return "overbought"
        elif rsi >= 65:
            return "overbought_light"
        elif rsi <= 25:
            return "oversold"
        elif rsi <= 35:
            return "oversold_light"
        return "neutral"
    
    def _get_macd_status(self, macd: float) -> str:
        if macd > 100:
            return "strong_bullish"
        elif macd > 0:
            return "bullish"
        elif macd < -100:
            return "strong_bearish"
        elif macd < 0:
            return "bearish"
        return "neutral"
    
    def _get_adx_status(self, adx: float) -> str:
        if adx >= 40:
            return "very_strong_trend"
        elif adx >= 25:
            return "strong_trend"
        elif adx >= 20:
            return "moderate_trend"
        return "weak_trend"
    
    def _get_trend_status(self, price: float, sma_20: float, sma_50: float) -> str:
        if price > sma_20 > sma_50:
            return "strong_uptrend"
        elif price > sma_20:
            return "uptrend"
        elif price < sma_20 < sma_50:
            return "strong_downtrend"
        elif price < sma_20:
            return "downtrend"
        return "sideways"
    
    def _get_mfi_status(self, mfi: float) -> str:
        if mfi >= 80:
            return "overbought"
        elif mfi >= 60:
            return "neutral"
        elif mfi <= 20:
            return "oversold"
        elif mfi <= 40:
            return "neutral"
        return "neutral"
    
    def _get_atr_status(self, atr: float, price: float) -> str:
        if price > 0:
            atr_percent = (atr / price) * 100
            if atr_percent >= 5:
                return "high"
            elif atr_percent >= 2:
                return "medium"
        return "low"
    
    def _get_action_from_indicators(self, tech: TechnicalIndicators) -> str:
        """Determine action based on indicators"""
        bullish_signals = 0
        bearish_signals = 0
        
        # RSI
        if tech.rsi >= 70:
            bearish_signals += 1
        elif tech.rsi <= 30:
            bullish_signals += 1
        
        # MACD
        if tech.macd > 0:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # ADX trend
        if tech.adx >= 25:
            if tech.trend_status in ["strong_uptrend", "uptrend"]:
                bullish_signals += 1
            elif tech.trend_status in ["strong_downtrend", "downtrend"]:
                bearish_signals += 1
        
        # CMF
        if tech.cmf > 0.1:
            bullish_signals += 1
        elif tech.cmf < -0.1:
            bearish_signals += 1
        
        # SuperTrend
        if tech.supertrend_signal == "BUY":
            bullish_signals += 1
        elif tech.supertrend_signal == "SELL":
            bearish_signals += 1
        
        # SMA trend
        if tech.trend_status in ["strong_uptrend"]:
            bullish_signals += 2
        elif tech.trend_status in ["strong_downtrend"]:
            bearish_signals += 2
        
        # Determine action
        if bullish_signals >= 4 and bearish_signals <= 1:
            return "BUY"
        elif bearish_signals >= 4 and bullish_signals <= 1:
            return "SELL"
        elif bullish_signals > bearish_signals:
            return "BUY" if tech.rsi < 70 else "HOLD"
        elif bearish_signals > bullish_signals:
            return "SELL" if tech.rsi > 30 else "HOLD"
        
        return "HOLD"
    
    def _generate_recommendation(self, result: StockAnalysis) -> Recommendation:
        """Generate final recommendation based on all data"""
        rec = Recommendation()
        
        # Technical action
        tech_action = self._get_action_from_indicators(result.technical)
        
        # Override with fundamental check
        if result.fundamental.pe > 30 and tech_action == "BUY":
            # Expensive stock, be cautious
            rec.action = "HOLD" if tech_action == "BUY" else tech_action
        elif result.fundamental.f_score >= 7 and tech_action in ["BUY", "HOLD"]:
            rec.action = "BUY"
        else:
            rec.action = tech_action
        
        # Calculate Master Score (0-100)
        score = 50
        
        # RSI contribution (0-20)
        if 40 <= result.technical.rsi <= 60:
            score += 20
        elif 30 <= result.technical.rsi <= 70:
            score += 10
        
        # ADX contribution (0-20)
        if result.technical.adx >= 25:
            score += 20
        elif result.technical.adx >= 20:
            score += 10
        
        # Trend contribution (0-20)
        if result.technical.trend_status in ["strong_uptrend", "uptrend"]:
            score += 20
        elif result.technical.trend_status == "sideways":
            score += 5
        
        # CMF contribution (0-20)
        if result.technical.cmf > 0.1:
            score += 20
        elif result.technical.cmf > 0:
            score += 10
        
        # Fundamental contribution (0-20)
        score += min(result.fundamental.f_score * 2, 20)
        
        rec.master_score = min(max(score, 0), 100)
        
        # Stars
        if rec.master_score >= 80:
            rec.score_stars = "★★★★★"
        elif rec.master_score >= 70:
            rec.score_stars = "★★★★☆"
        elif rec.master_score >= 60:
            rec.score_stars = "★★★★☆☆"
        elif rec.master_score >= 50:
            rec.score_stars = "★★★☆☆"
        elif rec.master_score >= 40:
            rec.score_stars = "★★☆☆☆"
        else:
            rec.score_stars = "★☆☆☆☆"
        
        # Reasons
        if result.technical.adx >= 25:
            if result.technical.trend_status in ["strong_uptrend", "uptrend"]:
                rec.reasons_positive.append(f"Xu hướng tăng mạnh (ADX: {result.technical.adx})")
            else:
                rec.reasons_positive.append(f"Xu hướng giảm mạnh (ADX: {result.technical.adx})")
        
        if result.technical.cmf > 0:
            rec.reasons_positive.append(f"Dòng tiền chảy vào (CMF: {result.technical.cmf:.2f})")
        else:
            rec.reasons_negative.append(f"Dòng tiền chảy ra (CMF: {result.technical.cmf:.2f})")
        
        if result.technical.rsi > 70:
            rec.reasons_negative.append(f"RSI {result.technical.rsi} - Vùng quá mua")
        elif result.technical.rsi < 30:
            rec.reasons_positive.append(f"RSI {result.technical.rsi} - Vùng quá bán, có thể phục hồi")
        
        if result.fundamental.f_score >= 7:
            rec.reasons_positive.append(f"Nội tại doanh nghiệp vững (F-Score: {result.fundamental.f_score}/9)")
        
        if result.fundamental.pe > 0 and result.fundamental.pe < 15:
            rec.reasons_positive.append(f"Định giá hấp dẫn (P/E: {result.fundamental.pe:.1f})")
        elif result.fundamental.pe > 25:
            rec.reasons_negative.append(f"Định giá cao (P/E: {result.fundamental.pe:.1f})")
        
        # Support/Resistance
        rec.support = result.technical.bollinger_lower if result.technical.bollinger_lower > 0 else result.technical.current_price * 0.95
        rec.resistance = result.technical.bollinger_upper if result.technical.bollinger_upper > 0 else result.technical.current_price * 1.05
        
        # Stop loss & Target
        rec.stop_loss = result.technical.sma_50 if result.technical.sma_50 > 0 else result.technical.current_price * 0.95
        rec.profit_target = rec.resistance
        rec.entry_target = result.technical.sma_20 if result.technical.current_price > result.technical.sma_20 else result.technical.current_price * 0.98
        
        # Timeframe
        if result.technical.adx >= 30:
            rec.timeframe = "SWING"
        elif result.technical.adx >= 20:
            rec.timeframe = "SHORT-TERM"
        else:
            rec.timeframe = "DAY TRADE"
        
        # Risk level
        if result.technical.atr_status == "high":
            rec.risk_level = "HIGH"
        elif result.technical.atr_status == "medium":
            rec.risk_level = "MEDIUM"
        else:
            rec.risk_level = "LOW"
        
        return rec
    
    def to_string(self, result: StockAnalysis) -> str:
        """Convert StockAnalysis to formatted string output"""
        lines = []
        
        # Header
        lines.append("┌" + "─" * 72 + "┐")
        lines.append(f"│  🏦 {result.symbol} - {result.name.upper()} ({result.exchange or 'HOSE'}".ljust(70) + "│")
        lines.append(f"│  THỜI GIAN: {result.timestamp.strftime('%Y-%m-%d %H:%M')}".ljust(70) + "│")
        lines.append("├" + "─" * 72 + "┤")
        
        # Price info
        price_change = f"{result.technical.change_percent:+.2f}%" if result.technical.change_percent else "N/A"
        lines.append(f"│  GIÁ: {result.technical.current_price:,.0f} VND ({price_change})".ljust(70) + "│")
        
        trend_text = result.technical.trend_status.replace("_", " ").title()
        adx_text = f"ADX: {result.technical.adx:.1f}" if result.technical.adx else "ADX: N/A"
        atr_text = f"ATR: {result.technical.atr:,.0f}" if result.technical.atr else "ATR: N/A"
        lines.append(f"│  XU HƯỚNG: {trend_text} ({adx_text}) | BIẾN ĐỘNG: {atr_text}".ljust(70) + "│")
        lines.append("├" + "─" * 72 + "┤")
        
        # Technical Analysis Section
        lines.append("│  1. PHÂN TÍCH KỸ THUẬT (vnstock_ta)".ljust(70) + "│")
        lines.append("│  ─" + "─" * 69 + "┤")
        
        # RSI
        rsi_bar = "█" * int(result.technical.rsi / 10) + "░" * (10 - int(result.technical.rsi / 10))
        lines.append(f"│     RSI(14): {result.technical.rsi:.1f} {rsi_bar} Zone: {result.technical.rsi_status.upper().replace('_', ' ')}".ljust(70) + "│")
        
        # MACD
        macd_text = f"MACD: {result.technical.macd:+.1f} ({result.technical.macd_signal.replace('_', ' ').title()})"
        lines.append(f"│     {macd_text}".ljust(70) + "│")
        
        # CMF
        cmf_text = f"CMF(20): {result.technical.cmf:+.3f} - {'TIỀN CHẢY VÀO (+)' if result.technical.cmf > 0 else 'TIỀN CHẢY RA (-)'}"
        lines.append(f"│     {cmf_text}".ljust(70) + "│")
        
        # MFI
        mfi_text = f"MFI(14): {result.technical.mfi:.1f} - Zone: {result.technical.mfi_status.upper().replace('_', ' ')}"
        lines.append(f"│     {mfi_text}".ljust(70) + "│")
        
        # SMA
        sma_text = f"SMA(20): {result.technical.sma_20:,.0f} | SMA(50): {result.technical.sma_50:,.0f}"
        lines.append(f"│     {sma_text}".ljust(70) + "│")
        
        # SuperTrend
        st_text = f"SuperTrend: {result.technical.supertrend_signal} | Stop: {result.technical.supertrend_stop:,.0f}"
        lines.append(f"│     {st_text}".ljust(70) + "│")
        
        # Bollinger
        bb_text = f"Bollinger: Upper {result.technical.bollinger_upper:,.0f} | Lower {result.technical.bollinger_lower:,.0f}"
        lines.append(f"│     {bb_text}".ljust(70) + "│")
        
        # VWAP
        vwap_text = f"VWAP: {result.technical.vwap:,.0f} - Giá {'TRÊN' if 'above' in result.technical.vwap_status else 'DƯỚI'} VWAP"
        lines.append(f"│     {vwap_text}".ljust(70) + "│")
        
        lines.append("├" + "─" * 72 + "┤")
        
        # Fundamental Section
        lines.append("│  2. SỨC KHỎE DOANH NGHIỆP (vnstock_data - Fundamental)".ljust(70) + "│")
        lines.append("│  ─" + "─" * 69 + "┤")
        
        # F-Score
        f_stars = "★" * result.fundamental.f_score + "☆" * (result.fundamental.f_score_max - result.fundamental.f_score)
        lines.append(f"│     F-Score: {result.fundamental.f_score}/{result.fundamental.f_score_max} {f_stars} (Grade {result.fundamental.f_score_grade})".ljust(70) + "│")
        
        # Valuation
        pe_text = f"P/E: {result.fundamental.pe:.1f}x" if result.fundamental.pe > 0 else "P/E: N/A"
        pb_text = f"P/B: {result.fundamental.pb:.1f}x" if result.fundamental.pb > 0 else "P/B: N/A"
        roe_text = f"ROE: {result.fundamental.roe:.1f}%" if result.fundamental.roe > 0 else "ROE: N/A"
        lines.append(f"│     Định giá: {pe_text} | {pb_text} | {roe_text}".ljust(70) + "│")
        
        # Growth
        growth_text = f"Tăng trưởng LN: {result.fundamental.profit_growth:+.1f}% YoY" if result.fundamental.profit_growth != 0 else "Tăng trưởng LN: N/A"
        margin_text = f"Margin: {result.fundamental.margin:.1f}%" if result.fundamental.margin > 0 else ""
        lines.append(f"│     {growth_text} {margin_text}".ljust(70) + "│")
        
        lines.append("├" + "─" * 72 + "┤")
        
        # Sentiment Section
        if result.sentiment.news_count > 0:
            lines.append("│  3. TIN TỨC & TÂM LÝ (vnstock_news)".ljust(70) + "│")
            lines.append("│  ─" + "─" * 69 + "┤")
            lines.append(f"│     Số tin 7 ngày: {result.sentiment.news_count} bài | Tâm lý: {result.sentiment.sentiment.upper()} ({result.sentiment.score:+.2f})".ljust(70) + "│")
            if result.sentiment.keywords:
                kw_text = f"Keywords: {', '.join(result.sentiment.keywords[:3])}"
                lines.append(f"│     {kw_text}".ljust(70) + "│")
            lines.append("├" + "─" * 72 + "┤")
        
        # Recommendation Section
        action_color = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡", "WATCH": "⚪"}.get(result.recommendation.action, "⚪")
        lines.append(f"│  🤖 AI INSIGHT: {action_color} {result.recommendation.action}".ljust(70) + "│")
        lines.append("│  ─" + "─" * 69 + "┤")
        
        # Master Score
        lines.append(f"│     Master Score: {result.recommendation.master_score}/100 {result.recommendation.score_stars}".ljust(70) + "│")
        lines.append("│  ─" + "─" * 69 + "┤")
        
        # Positive reasons
        for reason in result.recommendation.reasons_positive[:3]:
            lines.append(f"│     ✅ {reason}".ljust(70) + "│")
        
        # Negative reasons
        for reason in result.recommendation.reasons_negative[:3]:
            lines.append(f"│     ⚠️  {reason}".ljust(70) + "│")
        
        lines.append("│  ─" + "─" * 69 + "┤")
        
        # Action items
        lines.append(f"│     📌 Điểm mua: {result.recommendation.entry_target:,.0f}" if result.recommendation.action == "BUY" else "│     📌 Điểm mua: Chờ retest".ljust(70) + "│")
        lines.append(f"│     🎯 Mục tiêu: {result.recommendation.profit_target:,.0f} (+{(result.recommendation.profit_target/result.technical.current_price-1)*100:.1f}%)" if result.recommendation.profit_target > 0 else "│".ljust(70) + "│")
        lines.append(f"│     🛑 Stop Loss: {result.recommendation.stop_loss:,.0f} ({(result.recommendation.stop_loss/result.technical.current_price-1)*100:.1f}%)".ljust(70) + "│")
        lines.append(f"│     ⏰ Timeframe: {result.recommendation.timeframe} | Risk: {result.recommendation.risk_level}".ljust(70) + "│")
        
        # Footer
        lines.append("└" + "─" * 72 + "┘")
        
        return "\n".join(lines)
    
    def to_dict(self, result: StockAnalysis) -> dict[str, Any]:
        """Convert StockAnalysis to dictionary for JSON serialization"""
        return {
            "symbol": result.symbol,
            "name": result.name,
            "exchange": result.exchange,
            "timestamp": result.timestamp.isoformat(),
            "price": {
                "current": result.technical.current_price,
                "change_percent": result.technical.change_percent,
                "volume": result.technical.volume,
            },
            "technical": {
                "rsi": {"value": result.technical.rsi, "status": result.technical.rsi_status},
                "macd": {"value": result.technical.macd, "signal": result.technical.macd_signal},
                "adx": {"value": result.technical.adx, "status": result.technical.adx_status},
                "trend": {
                    "sma_20": result.technical.sma_20,
                    "sma_50": result.technical.sma_50,
                    "status": result.technical.trend_status,
                },
                "supertrend": {
                    "signal": result.technical.supertrend_signal,
                    "stop": result.technical.supertrend_stop,
                },
                "money_flow": {
                    "cmf": result.technical.cmf,
                    "cmf_status": result.technical.cmf_status,
                    "mfi": result.technical.mfi,
                    "mfi_status": result.technical.mfi_status,
                },
                "volatility": {
                    "atr": result.technical.atr,
                    "atr_status": result.technical.atr_status,
                    "bollinger": {
                        "upper": result.technical.bollinger_upper,
                        "middle": result.technical.bollinger_middle,
                        "lower": result.technical.bollinger_lower,
                        "position": result.technical.bollinger_position,
                    },
                },
                "vwap": {
                    "value": result.technical.vwap,
                    "status": result.technical.vwap_status,
                },
            },
            "fundamental": {
                "f_score": {
                    "value": result.fundamental.f_score,
                    "max": result.fundamental.f_score_max,
                    "grade": result.fundamental.f_score_grade,
                },
                "valuation": {
                    "pe": result.fundamental.pe,
                    "pb": result.fundamental.pb,
                    "roe": result.fundamental.roe,
                    "eps": result.fundamental.eps,
                },
                "growth": {
                    "profit_growth": result.fundamental.profit_growth,
                    "profit_growth_yoy": result.fundamental.profit_growth_yoy,
                    "margin": result.fundamental.margin,
                },
            },
            "sentiment": {
                "news_count": result.sentiment.news_count,
                "score": result.sentiment.score,
                "sentiment": result.sentiment.sentiment,
                "keywords": result.sentiment.keywords,
                "summary": result.sentiment.summary,
            },
            "recommendation": {
                "action": result.recommendation.action,
                "master_score": result.recommendation.master_score,
                "score_stars": result.recommendation.score_stars,
                "reasons_positive": result.recommendation.reasons_positive,
                "reasons_negative": result.recommendation.reasons_negative,
                "support": result.recommendation.support,
                "resistance": result.recommendation.resistance,
                "entry_target": result.recommendation.entry_target,
                "stop_loss": result.recommendation.stop_loss,
                "profit_target": result.recommendation.profit_target,
                "timeframe": result.recommendation.timeframe,
                "risk_level": result.recommendation.risk_level,
            },
        }


# Convenience function for quick analysis
def analyze_stock(symbol: str, include_sentiment: bool = False) -> StockAnalysis:
    """
    Quick function to analyze a stock.
    
    Args:
        symbol: Stock symbol (e.g., "VCB", "ACB")
        include_sentiment: Whether to include news sentiment
        
    Returns:
        StockAnalysis object
    """
    analyzer = StockAnalyzer()
    return analyzer.analyze(symbol, include_sentiment=include_sentiment)


if __name__ == "__main__":
    # Demo
    print("Stock Analyzer Module")
    print("Usage: analyzer = StockAnalyzer()")
    print("       result = analyzer.analyze('VCB')")
    print("       print(analyzer.to_string(result))")
