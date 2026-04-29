"""
Strategy Lab Simulator - Kết nối với Logic V4

Hàm chính: simulate_trade()
- Nhận: symbol + override params (price, cmf, rsi, adx, market_rsi, f_score, roe)
- Trả về: Master Score + Veto Status + R:R Ratio + Entry/Stop/Target
- Logic y hệt analyzer.py V4 nhưng cho phép override parameters
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class SimParams:
    """Parameters có thể override trong simulation"""
    # Technical (override)
    price: Optional[float] = None
    cmf: Optional[float] = None
    rsi: Optional[float] = None
    adx: Optional[float] = None
    atr: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    vwap: Optional[float] = None
    volume_ratio: Optional[float] = None
    
    # Fundamental (override)
    f_score: Optional[int] = None
    roe: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    
    # Market (override)
    market_rsi: Optional[float] = None
    
    # Price adjustment (-20% to +20%)
    price_adj_pct: float = 0.0  # Ví dụ: -10 = giảm 10%, +15 = tăng 15%


@dataclass
class SimResult:
    """Kết quả simulation - đầy đủ như analyzer V4"""
    symbol: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Base values (từ DB)
    base_price: float = 0.0
    base_cmf: float = 0.0
    base_rsi: float = 50.0
    base_adx: float = 25.0
    
    # Simulated values (sau khi override)
    sim_price: float = 0.0
    sim_cmf: float = 0.0
    sim_rsi: float = 50.0
    sim_adx: float = 25.0
    sim_sma50: float = 0.0
    
    # Scores
    master_score: int = 50
    tech_score: int = 50
    fund_score: int = 50
    market_weight: int = 0
    
    # Veto
    is_vetoed: bool = False
    veto_reason: str = ""
    veto_checks: list = field(default_factory=list)
    
    # Trading levels
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    support_price: float = 0.0
    risk_reward_ratio: float = 2.0
    
    # Signal
    signal: str = "HOLD"
    est_days: int = 7
    upside_pct: float = 5.0
    
    # Detail
    reasons_positive: list = field(default_factory=list)
    reasons_negative: list = field(default_factory=list)


def simulate_trade(
    symbol: str,
    base_data: dict,
    params: SimParams
) -> SimResult:
    """
    Hàm chính - Tính Master Score với override parameters.
    
    Logic y hệt analyzer V4 nhưng cho phép override bất kỳ tham số nào.
    Khi slider thay đổi -> gọi hàm này -> trả về kết quả real-time.
    
    Args:
        symbol: Mã cổ phiếu
        base_data: Dữ liệu gốc từ DB (price, cmf, rsi, adx, sma_50, atr, f_score, roe...)
        params: Các tham số override từ sliders
    
    Returns:
        SimResult với đầy đủ thông tin
    """
    result = SimResult(symbol=symbol)
    
    # === LẤY BASE VALUES ===
    result.base_price = base_data.get("price", 0)
    result.base_cmf = base_data.get("cmf", 0)
    result.base_rsi = base_data.get("rsi", 50)
    result.base_adx = base_data.get("adx", 25)
    
    # === ÁP DỤNG OVERRIDES ===
    # Price với adjustment %
    if params.price is not None:
        result.sim_price = params.price
    elif params.price_adj_pct != 0:
        base_p = base_data.get("price", 100)
        result.sim_price = base_p * (1 + params.price_adj_pct / 100)
    else:
        result.sim_price = base_data.get("price", 0)
    
    result.sim_cmf = params.cmf if params.cmf is not None else result.base_cmf
    result.sim_rsi = params.rsi if params.rsi is not None else result.base_rsi
    result.sim_adx = params.adx if params.adx is not None else result.base_adx
    result.sim_sma50 = params.sma_50 if params.sma_50 is not None else base_data.get("sma_50", 0)
    
    # Fundamental overrides
    sim_f_score = params.f_score if params.f_score is not None else base_data.get("f_score", 5)
    sim_roe = params.roe if params.roe is not None else base_data.get("roe", 10)
    sim_pe = params.pe if params.pe is not None else base_data.get("pe", 15)
    sim_pb = params.pb if params.pb is not None else base_data.get("pb", 1.5)
    
    # Market RSI
    sim_market_rsi = params.market_rsi if params.market_rsi is not None else base_data.get("market_rsi", 50)
    
    # ATR
    sim_atr = params.atr if params.atr is not None else base_data.get("atr", result.sim_price * 0.02)
    
    # === VETO CHECKS (Logic V4) ===
    result.veto_checks = []
    
    # Veto 1: CMF âm = Rút tiền
    if result.sim_cmf < 0:
        result.veto_checks.append({
            "check": "CMF (Dòng tiền)",
            "threshold": ">= 0",
            "value": result.sim_cmf,
            "status": "FAIL",
            "points": -15,
            "reason": "CMF âm = Dòng tiền chảy ra"
        })
        result.is_vetoed = True
        result.veto_reason = f"CMF âm ({result.sim_cmf:.2f})"
    else:
        result.veto_checks.append({
            "check": "CMF (Dòng tiền)",
            "threshold": ">= 0",
            "value": result.sim_cmf,
            "status": "PASS",
            "points": 8 if result.sim_cmf > 0.1 else 4,
            "reason": "CMF dương = Dòng tiền chảy vào"
        })
    
    # Veto 2: RSI quá cao
    if result.sim_rsi > 80:
        result.veto_checks.append({
            "check": "RSI (Quá mua)",
            "threshold": "< 80",
            "value": result.sim_rsi,
            "status": "FAIL",
            "points": -10,
            "reason": "RSI > 80 = Quá mua, nguy cơ điều chỉnh"
        })
        result.is_vetoed = True
        result.veto_reason = f"RSI quá cao ({result.sim_rsi})"
    elif result.sim_rsi > 70:
        result.veto_checks.append({
            "check": "RSI (Quá mua)",
            "threshold": "< 70",
            "value": result.sim_rsi,
            "status": "WARN",
            "points": -5,
            "reason": "RSI > 70 = Cảnh báo quá mua"
        })
        if not result.is_vetoed:
            result.veto_reason = f"RSI cao ({result.sim_rsi})"
    else:
        result.veto_checks.append({
            "check": "RSI",
            "threshold": "< 70",
            "value": result.sim_rsi,
            "status": "PASS",
            "points": 5,
            "reason": "RSI normal"
        })
    
    # Veto 3: Giá dưới SMA50 (không có hỗ trợ)
    if result.sim_price < result.sim_sma50 and result.sim_sma50 > 0:
        result.veto_checks.append({
            "check": "Price > SMA50",
            "threshold": f"> {result.sim_sma50:.0f}",
            "value": result.sim_price,
            "status": "FAIL",
            "points": -10,
            "reason": "Giá dưới SMA50 = Không có hỗ trợ"
        })
        result.is_vetoed = True
        result.veto_reason = f"Giá dưới SMA50"
    else:
        result.veto_checks.append({
            "check": "Price > SMA50",
            "threshold": f"> {result.sim_sma50:.0f}" if result.sim_sma50 > 0 else "N/A",
            "value": result.sim_price,
            "status": "PASS",
            "points": 5,
            "reason": "Giá trên SMA50 = Có hỗ trợ"
        })
    
    # Veto 4: ADX quá yếu (không có xu hướng)
    if result.sim_adx < 15:
        result.veto_checks.append({
            "check": "ADX (Xu hướng)",
            "threshold": ">= 15",
            "value": result.sim_adx,
            "status": "FAIL",
            "points": -8,
            "reason": "ADX < 15 = Thị trường sideway"
        })
    elif result.sim_adx < 20:
        result.veto_checks.append({
            "check": "ADX (Xu hướng)",
            "threshold": ">= 20",
            "value": result.sim_adx,
            "status": "WARN",
            "points": -3,
            "reason": "ADX < 20 = Xu hướng yếu"
        })
    else:
        result.veto_checks.append({
            "check": "ADX (Xu hướng)",
            "threshold": ">= 20",
            "value": result.sim_adx,
            "status": "PASS",
            "points": 7 if result.sim_adx >= 25 else 4,
            "reason": "ADX tốt"
        })
    
    # Veto 5: Thị trường quá nguy hiểm
    if sim_market_rsi > 85:
        result.veto_checks.append({
            "check": "Market RSI (Danger)",
            "threshold": "< 85",
            "value": sim_market_rsi,
            "status": "FAIL",
            "points": -20,
            "reason": "VNIndex RSI > 85 = Thị trường quá nóng"
        })
        result.is_vetoed = True
        result.veto_reason = f"Thị trường quá nguy hiểm (RSI {sim_market_rsi})"
    elif sim_market_rsi > 75:
        result.veto_checks.append({
            "check": "Market RSI (Danger)",
            "threshold": "< 75",
            "value": sim_market_rsi,
            "status": "WARN",
            "points": -10,
            "reason": "VNIndex RSI > 75 = Thị trường hưng phấn"
        })
    elif sim_market_rsi < 30:
        result.veto_checks.append({
            "check": "Market RSI (Oversold)",
            "threshold": ">= 30",
            "value": sim_market_rsi,
            "status": "WARN",
            "points": 10,
            "reason": "VNIndex RSI < 30 = Quá bán, có thể rebound"
        })
    else:
        result.veto_checks.append({
            "check": "Market RSI",
            "threshold": "30-75",
            "value": sim_market_rsi,
            "status": "PASS",
            "points": 5,
            "reason": "Thị trường ổn định"
        })
    
    # === TÍNH ĐIỂM ===
    result.tech_score = 50
    result.fund_score = 50
    
    if not result.is_vetoed:
        # Technical Score
        # RSI contribution (50-65 là vùng tốt)
        if 50 <= result.sim_rsi <= 65:
            result.tech_score += 10
            result.reasons_positive.append(f"RSI {result.sim_rsi:.0f} vùng tốt")
        elif 40 <= result.sim_rsi < 50:
            result.tech_score += 5
        elif result.sim_rsi > 70:
            result.tech_score -= 5
        
        # CMF contribution
        if result.sim_cmf > 0.15:
            result.tech_score += 10
            result.reasons_positive.append(f"CMF mạnh ({result.sim_cmf:.2f})")
        elif result.sim_cmf > 0.05:
            result.tech_score += 6
            result.reasons_positive.append(f"CMF dương ({result.sim_cmf:.2f})")
        
        # ADX contribution
        if result.sim_adx >= 30:
            result.tech_score += 12
            result.reasons_positive.append(f"ADX mạnh ({result.sim_adx:.0f})")
        elif result.sim_adx >= 25:
            result.tech_score += 8
            result.reasons_positive.append(f"ADX khá ({result.sim_adx:.0f})")
        elif result.sim_adx >= 20:
            result.tech_score += 4
        
        # Fundamental Score
        if sim_f_score >= 7:
            result.fund_score += 15
            result.reasons_positive.append(f"F-Score tốt ({sim_f_score}/9)")
        elif sim_f_score >= 5:
            result.fund_score += 8
        
        if sim_roe >= 15:
            result.fund_score += 10
            result.reasons_positive.append(f"ROE cao ({sim_roe:.1f}%)")
        elif sim_roe >= 10:
            result.fund_score += 5
        
        # P/E hợp lý
        if 5 <= sim_pe <= 20:
            result.fund_score += 5
    else:
        result.tech_score = max(20, result.tech_score - 15)
        result.fund_score = max(20, result.fund_score - 10)
        result.reasons_negative.append(f"Bị Veto: {result.veto_reason}")
    
    # Market Weight
    result.market_weight = 0
    if sim_market_rsi < 30:
        result.market_weight = 12
        result.reasons_positive.append(f"Thị trường quá bán - Cơ hội mua")
    elif sim_market_rsi < 40:
        result.market_weight = 8
    elif sim_market_rsi > 70:
        result.market_weight = -8
        result.reasons_negative.append(f"Thị trường quá mua")
    elif sim_market_rsi > 80:
        result.market_weight = -15
        result.reasons_negative.append(f"Thị trường cực kỳ nguy hiểm")
    
    # Master Score
    result.master_score = round((result.tech_score * 0.6 + result.fund_score * 0.4) + result.market_weight)
    result.master_score = max(0, min(100, result.master_score))
    
    # === TÍNH MỨC GIAO DỊCH ===
    result.entry_price = result.sim_price
    result.support_price = result.sim_sma50 if result.sim_sma50 > 0 else result.sim_price * 0.97
    result.stop_loss = result.support_price
    
    # Take profit = Entry + (Risk * R:R)
    hard_risk = result.entry_price - result.support_price
    hard_risk_pct = (hard_risk / result.entry_price) * 100 if result.entry_price > 0 else 3
    
    # R:R mặc định = 3:1
    result.risk_reward_ratio = 3.0 if hard_risk_pct >= 2 else (3.0 * 2 / hard_risk_pct)
    
    result.take_profit = result.entry_price + (hard_risk * result.risk_reward_ratio)
    result.upside_pct = ((result.take_profit - result.entry_price) / result.entry_price) * 100
    
    # Est days dựa trên ATR
    atr_pct = (sim_atr / result.entry_price) * 100 if result.entry_price > 0 else 2
    result.est_days = max(3, min(15, int(atr_pct * 2)))
    
    # === SIGNAL ===
    if result.is_vetoed:
        result.signal = "VETO"
    elif result.master_score >= 70:
        result.signal = "BUY"
    elif result.master_score >= 60:
        result.signal = "WATCH"
    elif result.master_score >= 50:
        result.signal = "HOLD"
    else:
        result.signal = "SELL"
    
    return result


def result_to_dict(result: SimResult) -> dict:
    """Convert SimResult to dict for JSON response"""
    return {
        "symbol": result.symbol,
        "timestamp": result.timestamp.isoformat(),
        
        # Base vs Sim
        "base_params": {
            "price": result.base_price,
            "cmf": result.base_cmf,
            "rsi": result.base_rsi,
            "adx": result.base_adx,
        },
        "sim_params": {
            "price": round(result.sim_price, 2),
            "cmf": round(result.sim_cmf, 4),
            "rsi": round(result.sim_rsi, 1),
            "adx": round(result.sim_adx, 1),
            "sma50": round(result.sim_sma50, 2),
        },
        
        # Scores
        "master_score": result.master_score,
        "tech_score": result.tech_score,
        "fund_score": result.fund_score,
        "market_weight": result.market_weight,
        
        # Veto
        "is_vetoed": result.is_vetoed,
        "veto_reason": result.veto_reason,
        "veto_checks": result.veto_checks,
        
        # Trading levels
        "entry_price": round(result.entry_price, 2),
        "stop_loss": round(result.stop_loss, 2),
        "take_profit": round(result.take_profit, 2),
        "support_price": round(result.support_price, 2),
        "risk_reward_ratio": round(result.risk_reward_ratio, 2),
        "upside_pct": round(result.upside_pct, 2),
        "est_days": result.est_days,
        
        # Signal
        "signal": result.signal,
        
        # Reasons
        "reasons_positive": result.reasons_positive,
        "reasons_negative": result.reasons_negative,
    }
