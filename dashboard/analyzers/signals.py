"""
Signal Definitions Module

Contains signal thresholds and definitions for stock analysis.
Used by analyzers to interpret indicator values.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SignalStrength(Enum):
    """Signal strength levels"""
    VERY_WEAK = 1
    WEAK = 2
    NEUTRAL = 3
    STRONG = 4
    VERY_STRONG = 5


class SignalDirection(Enum):
    """Signal direction"""
    BEARISH = -1
    NEUTRAL = 0
    BULLISH = 1


@dataclass
class Signal:
    """Generic signal container"""
    name: str
    value: float
    direction: SignalDirection
    strength: SignalStrength
    status: str
    description: str
    weight: float = 1.0  # Weight in final scoring


@dataclass
class ThresholdConfig:
    """Configuration for indicator thresholds"""
    # RSI thresholds
    RSI_OVERBOUGHT: float = 70.0
    RSI_OVERBOUGHT_LIGHT: float = 65.0
    RSI_OVERSOLD: float = 30.0
    RSI_OVERSOLD_LIGHT: float = 35.0
    
    # ADX thresholds
    ADX_VERY_STRONG: float = 40.0
    ADX_STRONG: float = 25.0
    ADX_MODERATE: float = 20.0
    
    # CMF thresholds
    CMF_STRONG_INFLOW: float = 0.2
    CMF_INFLOW: float = 0.05
    CMF_OUTFLOW: float = -0.05
    CMF_STRONG_OUTFLOW: float = -0.2
    
    # MFI thresholds
    MFI_OVERBOUGHT: float = 80.0
    MFI_OVERSOLD: float = 20.0
    
    # ATR volatility thresholds (% of price)
    ATR_HIGH: float = 5.0
    ATR_MEDIUM: float = 2.0
    
    # Bollinger position thresholds
    BB_UPPER_ZONE: float = 0.8
    BB_LOWER_ZONE: float = 0.2


# Default threshold configuration
DEFAULT_THRESHOLDS = ThresholdConfig()


def get_rsi_signal(value: float, thresholds: Optional[ThresholdConfig] = None) -> Signal:
    """Get RSI signal"""
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS
    
    if value >= thresholds.RSI_OVERBOUGHT:
        return Signal(
            name="RSI",
            value=value,
            direction=SignalDirection.BEARISH,
            strength=SignalStrength.VERY_STRONG if value >= 80 else SignalStrength.STRONG,
            status="overbought",
            description=f"RSI {value:.1f} - Vùng QUÁ MUA mạnh" if value >= 80 else f"RSI {value:.1f} - Vùng QUÁ MUA nhẹ",
            weight=1.5
        )
    elif value >= thresholds.RSI_OVERBOUGHT_LIGHT:
        return Signal(
            name="RSI",
            value=value,
            direction=SignalDirection.BEARISH,
            strength=SignalStrength.MODERATE,
            status="overbought_light",
            description=f"RSI {value:.1f} - Vùng quá mua nhẹ",
            weight=1.0
        )
    elif value <= thresholds.RSI_OVERSOLD:
        return Signal(
            name="RSI",
            value=value,
            direction=SignalDirection.BULLISH,
            strength=SignalStrength.VERY_STRONG if value <= 20 else SignalStrength.STRONG,
            status="oversold",
            description=f"RSI {value:.1f} - Vùng QUÁ BÁN mạnh" if value <= 20 else f"RSI {value:.1f} - Vùng QUÁ BÁN",
            weight=1.5
        )
    elif value <= thresholds.RSI_OVERSOLD_LIGHT:
        return Signal(
            name="RSI",
            value=value,
            direction=SignalDirection.BULLISH,
            strength=SignalStrength.MODERATE,
            status="oversold_light",
            description=f"RSI {value:.1f} - Vùng quá bán nhẹ",
            weight=1.0
        )
    
    return Signal(
        name="RSI",
        value=value,
        direction=SignalDirection.NEUTRAL,
        strength=SignalStrength.NEUTRAL,
        status="neutral",
        description=f"RSI {value:.1f} - Vùng trung lập",
        weight=0.5
    )


def get_macd_signal(value: float, signal_line: float = 0) -> Signal:
    """Get MACD signal"""
    if value > 100:
        direction = SignalDirection.BULLISH
        strength = SignalStrength.VERY_STRONG
        status = "strong_bullish"
        desc = f"MACD +{value:.1f} - Tín hiệu tăng MẠNH"
    elif value > signal_line:
        direction = SignalDirection.BULLISH
        strength = SignalStrength.STRONG
        status = "bullish"
        desc = f"MACD +{value:.1f} - Tín hiệu tăng"
    elif value < -100:
        direction = SignalDirection.BEARISH
        strength = SignalStrength.VERY_STRONG
        status = "strong_bearish"
        desc = f"MACD {value:.1f} - Tín hiệu giảm MẠNH"
    elif value < signal_line:
        direction = SignalDirection.BEARISH
        strength = SignalStrength.STRONG
        status = "bearish"
        desc = f"MACD {value:.1f} - Tín hiệu giảm"
    else:
        direction = SignalDirection.NEUTRAL
        strength = SignalStrength.NEUTRAL
        status = "neutral"
        desc = f"MACD {value:.1f} - Trung lập"
    
    return Signal(
        name="MACD",
        value=value,
        direction=direction,
        strength=strength,
        status=status,
        description=desc,
        weight=1.2
    )


def get_adx_signal(value: float, dmi_plus: float = 0, dmi_minus: float = 0, thresholds: Optional[ThresholdConfig] = None) -> Signal:
    """Get ADX signal with trend direction"""
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS
    
    # Determine trend direction from DMI
    if dmi_plus > dmi_minus:
        direction = SignalDirection.BULLISH
        direction_desc = "tăng"
    elif dmi_minus > dmi_plus:
        direction = SignalDirection.BEARISH
        direction_desc = "giảm"
    else:
        direction = SignalDirection.NEUTRAL
        direction_desc = "yếu"
    
    if value >= thresholds.ADX_VERY_STRONG:
        strength = SignalStrength.VERY_STRONG
        status = "very_strong_trend"
        desc = f"ADX {value:.1f} - Xu hướng {direction_desc} RẤT MẠNH"
        weight = 2.0
    elif value >= thresholds.ADX_STRONG:
        strength = SignalStrength.STRONG
        status = "strong_trend"
        desc = f"ADX {value:.1f} - Xu hướng {direction_desc} MẠNH"
        weight = 1.5
    elif value >= thresholds.ADX_MODERATE:
        strength = SignalStrength.MODERATE
        status = "moderate_trend"
        desc = f"ADX {value:.1f} - Xu hướng {direction_desc} vừa"
        weight = 1.0
    else:
        strength = SignalStrength.WEAK
        status = "weak_trend"
        desc = f"ADX {value:.1f} - Xu hướng {direction_desc} YẾU, dễ sideway"
        weight = 0.5
    
    return Signal(
        name="ADX",
        value=value,
        direction=direction,
        strength=strength,
        status=status,
        description=desc,
        weight=weight
    )


def get_cmf_signal(value: float, thresholds: Optional[ThresholdConfig] = None) -> Signal:
    """Get CMF (Chaikin Money Flow) signal"""
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS
    
    if value >= thresholds.CMF_STRONG_INFLOW:
        return Signal(
            name="CMF",
            value=value,
            direction=SignalDirection.BULLISH,
            strength=SignalStrength.VERY_STRONG,
            status="strong_inflow",
            description=f"CMF +{value:.3f} - TIỀN CHẢY VÀO MẠNH",
            weight=1.5
        )
    elif value >= thresholds.CMF_INFLOW:
        return Signal(
            name="CMF",
            value=value,
            direction=SignalDirection.BULLISH,
            strength=SignalStrength.STRONG,
            status="inflow",
            description=f"CMF +{value:.3f} - TIỀN CHẢY VÀO",
            weight=1.2
        )
    elif value <= thresholds.CMF_STRONG_OUTFLOW:
        return Signal(
            name="CMF",
            value=value,
            direction=SignalDirection.BEARISH,
            strength=SignalStrength.VERY_STRONG,
            status="strong_outflow",
            description=f"CMF {value:.3f} - TIỀN CHẢY RA MẠNH",
            weight=1.5
        )
    elif value <= thresholds.CMF_OUTFLOW:
        return Signal(
            name="CMF",
            value=value,
            direction=SignalDirection.BEARISH,
            strength=SignalStrength.STRONG,
            status="outflow",
            description=f"CMF {value:.3f} - TIỀN CHẢY RA",
            weight=1.2
        )
    
    return Signal(
        name="CMF",
        value=value,
        direction=SignalDirection.NEUTRAL,
        strength=SignalStrength.NEUTRAL,
        status="neutral",
        description=f"CMF {value:.3f} - TIỀN TRUNG LẬP",
        weight=0.5
    )


def get_mfi_signal(value: float, thresholds: Optional[ThresholdConfig] = None) -> Signal:
    """Get MFI (Money Flow Index) signal"""
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS
    
    if value >= thresholds.MFI_OVERBOUGHT:
        return Signal(
            name="MFI",
            value=value,
            direction=SignalDirection.BEARISH,
            strength=SignalStrength.STRONG,
            status="overbought",
            description=f"MFI {value:.1f} - Vùng quá mua",
            weight=1.2
        )
    elif value <= thresholds.MFI_OVERSOLD:
        return Signal(
            name="MFI",
            value=value,
            direction=SignalDirection.BULLISH,
            strength=SignalStrength.STRONG,
            status="oversold",
            description=f"MFI {value:.1f} - Vùng quá bán",
            weight=1.2
        )
    
    return Signal(
        name="MFI",
        value=value,
        direction=SignalDirection.NEUTRAL,
        strength=SignalStrength.NEUTRAL,
        status="neutral",
        description=f"MFI {value:.1f} - Vùng trung lập",
        weight=0.5
    )


def get_supertrend_signal(close: float, stop: float) -> Signal:
    """Get SuperTrend signal"""
    if close > stop:
        return Signal(
            name="SuperTrend",
            value=stop,
            direction=SignalDirection.BULLISH,
            strength=SignalStrength.STRONG,
            status="buy",
            description=f"SuperTrend: BUY | Stop: {stop:,.0f}",
            weight=1.5
        )
    else:
        return Signal(
            name="SuperTrend",
            value=stop,
            direction=SignalDirection.BEARISH,
            strength=SignalStrength.STRONG,
            status="sell",
            description=f"SuperTrend: SELL | Stop: {stop:,.0f}",
            weight=1.5
        )


def get_bollinger_signal(price: float, upper: float, lower: float, middle: float = None) -> Signal:
    """Get Bollinger Bands signal"""
    if middle is None:
        middle = (upper + lower) / 2
    
    position = (price - lower) / (upper - lower) if upper > lower else 0.5
    
    if price >= upper:
        return Signal(
            name="Bollinger",
            value=position,
            direction=SignalDirection.BEARISH,
            strength=SignalStrength.MODERATE,
            status="upper_band",
            description=f"Giá vượt Upper Band - Có thể chỉnh giá",
            weight=1.0
        )
    elif position >= 0.8:
        return Signal(
            name="Bollinger",
            value=position,
            direction=SignalDirection.BEARISH,
            strength=SignalStrength.WEAK,
            status="upper_zone",
            description=f"Giá gần Upper Band ({position*100:.0f}%)",
            weight=0.8
        )
    elif position <= 0.2:
        return Signal(
            name="Bollinger",
            value=position,
            direction=SignalDirection.BULLISH,
            strength=SignalStrength.WEAK,
            status="lower_zone",
            description=f"Giá gần Lower Band ({position*100:.0f}%)",
            weight=0.8
        )
    elif price <= lower:
        return Signal(
            name="Bollinger",
            value=position,
            direction=SignalDirection.BULLISH,
            strength=SignalStrength.MODERATE,
            status="lower_band",
            description=f"Giá dưới Lower Band - Có thể phục hồi",
            weight=1.0
        )
    
    return Signal(
        name="Bollinger",
        value=position,
        direction=SignalDirection.NEUTRAL,
        strength=SignalStrength.NEUTRAL,
        status="middle_zone",
        description=f"Giá ở vùng giữa ({position*100:.0f}%)",
        weight=0.3
    )


def get_trend_signal(price: float, sma_20: float, sma_50: float, sma_200: float = None) -> Signal:
    """Get SMA trend signal"""
    if sma_200 is None:
        sma_200 = sma_50
    
    if price > sma_20 > sma_50 > sma_200:
        return Signal(
            name="Trend",
            value=price,
            direction=SignalDirection.BULLISH,
            strength=SignalStrength.VERY_STRONG,
            status="strong_uptrend",
            description="STRONG BULLISH - Giá > SMA20 > SMA50 > SMA200",
            weight=2.0
        )
    elif price > sma_20 > sma_50:
        return Signal(
            name="Trend",
            value=price,
            direction=SignalDirection.BULLISH,
            strength=SignalStrength.STRONG,
            status="uptrend",
            description="BULLISH - Giá > SMA20 > SMA50",
            weight=1.5
        )
    elif price < sma_20 < sma_50 < sma_200:
        return Signal(
            name="Trend",
            value=price,
            direction=SignalDirection.BEARISH,
            strength=SignalStrength.VERY_STRONG,
            status="strong_downtrend",
            description="STRONG BEARISH - Giá < SMA20 < SMA50 < SMA200",
            weight=2.0
        )
    elif price < sma_20 < sma_50:
        return Signal(
            name="Trend",
            value=price,
            direction=SignalDirection.BEARISH,
            strength=SignalStrength.STRONG,
            status="downtrend",
            description="BEARISH - Giá < SMA20 < SMA50",
            weight=1.5
        )
    
    return Signal(
        name="Trend",
        value=price,
        direction=SignalDirection.NEUTRAL,
        strength=SignalStrength.NEUTRAL,
        status="sideways",
        description="SIDEWAYS - Giá dao động quanh SMA",
        weight=0.5
    )


def calculate_master_score(signals: list[Signal]) -> tuple[int, list[str], list[str]]:
    """
    Calculate master score from signals.
    
    Returns:
        Tuple of (score, positive_reasons, negative_reasons)
    """
    total_score = 50  # Base score
    positive_reasons = []
    negative_reasons = []
    
    for signal in signals:
        # Weight contribution based on direction and strength
        if signal.direction == SignalDirection.BULLISH:
            contribution = signal.strength.value * signal.weight * 5
            total_score += contribution
            
            if signal.strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]:
                positive_reasons.append(f"{signal.name}: {signal.description}")
        elif signal.direction == SignalDirection.BEARISH:
            contribution = -signal.strength.value * signal.weight * 5
            total_score += contribution
            
            if signal.strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]:
                negative_reasons.append(f"{signal.name}: {signal.description}")
    
    # Clamp to 0-100
    final_score = max(0, min(100, int(total_score)))
    
    return final_score, positive_reasons, negative_reasons


def get_score_stars(score: int) -> str:
    """Convert numeric score to star rating"""
    if score >= 90:
        return "★★★★★"
    elif score >= 80:
        return "★★★★☆"
    elif score >= 70:
        return "★★★★☆"
    elif score >= 60:
        return "★★★★☆☆"
    elif score >= 50:
        return "★★★☆☆"
    elif score >= 40:
        return "★★☆☆☆"
    elif score >= 30:
        return "★★☆☆☆"
    elif score >= 20:
        return "★☆☆☆☆"
    else:
        return "★☆☆☆☆"


def get_action_from_score(score: int) -> str:
    """Convert score to action recommendation"""
    if score >= 75:
        return "BUY"
    elif score >= 60:
        return "BUY" if score < 70 else "HOLD"
    elif score >= 40:
        return "HOLD"
    elif score >= 25:
        return "SELL" if score < 35 else "HOLD"
    else:
        return "SELL"
