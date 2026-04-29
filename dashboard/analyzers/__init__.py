"""
Dashboard Analyzers - Technical & Fundamental Analysis Modules

This module provides comprehensive analysis for various asset types:
- Stock Analysis: vnstock_ta + vnstock_data Fundamental
- Index Analysis: Market Breadth, ADX
- Commodity Analysis: Gold, Precious Metals
- Futures Analysis: VN30F
- ETF/Fund Analysis: E1VFVN30
- Crypto Analysis: BTC, ETH
- CW Analysis: Covered Warrants
- Forex Analysis: EURUSD, USDJPY
"""

# Stock Analysis
from .stock_analyzer import StockAnalyzer, StockAnalysis, analyze_stock

# Signals
from .signals import (
    Signal,
    SignalStrength,
    SignalDirection,
    ThresholdConfig,
    get_rsi_signal,
    get_macd_signal,
    get_adx_signal,
    get_cmf_signal,
    get_mfi_signal,
    get_supertrend_signal,
    get_bollinger_signal,
    get_trend_signal,
    calculate_master_score,
    get_score_stars,
    get_action_from_score,
)

# Index Analysis (Phase 2)
from .index_analyzer import IndexAnalyzer, IndexData, MarketBreadth

# Gold & Futures (Phase 3)
#from .gold_analyzer import GoldAnalyzer, GoldData
#from .futures_analyzer import FuturesAnalyzer, FuturesData

# ETF, Forex, Crypto, CW (Phase 4)
from .fund_analyzer import FundAnalyzer, ETFAnalyzer, FundData
from .forex_analyzer import ForexAnalyzer, ForexData
from .crypto_analyzer import CryptoAnalyzer, CryptoData
from .cw_analyzer import CWAnalyzer, CWData

# Bond (Final Phase)
from .bond_analyzer import BondAnalyzer, BondData, GovBondIndexAnalyzer

__all__ = [
    # Stock
    "StockAnalyzer",
    "StockAnalysis",
    "analyze_stock",
    # Signals
    "Signal",
    "SignalStrength",
    "SignalDirection",
    "ThresholdConfig",
    "get_rsi_signal",
    "get_macd_signal",
    "get_adx_signal",
    "get_cmf_signal",
    "get_mfi_signal",
    "get_supertrend_signal",
    "get_bollinger_signal",
    "get_trend_signal",
    "calculate_master_score",
    "get_score_stars",
    "get_action_from_score",
    # Index
    "IndexAnalyzer",
    "IndexData",
    "MarketBreadth",
    # Gold & Futures
    #"GoldAnalyzer",
    #"GoldData",
    "FuturesAnalyzer",
    "FuturesData",
    # ETF, Forex, Crypto, CW
    "FundAnalyzer",
    "ETFAnalyzer",
    "FundData",
    "ForexAnalyzer",
    "ForexData",
    "CryptoAnalyzer",
    "CryptoData",
    "CWAnalyzer",
    "CWData",
    # Bond
    "BondAnalyzer",
    "BondData",
    "GovBondIndexAnalyzer",
]
