from dataclasses import dataclass
from typing import Optional


@dataclass
class NiftySignal:
    decision: str
    direction: str
    confidence: float
    reason: str


def generate_signal(
    nifty_price: float,
    ema20: float,
    ema50: float,
    rsi: float,
    previous_close: float,
) -> NiftySignal:
    """
    Initial NIFTY directional signal engine.

    This is deliberately simple in Phase 1.
    We will NOT call this production-ready until
    it has been historically backtested.
    """

    if nifty_price <= 0:
        raise ValueError("NIFTY price must be positive.")

    if ema20 <= 0 or ema50 <= 0:
        raise ValueError("EMA values must be positive.")

    if not 0 <= rsi <= 100:
        raise ValueError("RSI must be between 0 and 100.")

    bullish_score = 0
    bearish_score = 0
    reasons = []

    if nifty_price > ema20 > ema50:
        bullish_score += 2
        reasons.append(
            "NIFTY above EMA20 above EMA50"
        )

    elif nifty_price < ema20 < ema50:
        bearish_score += 2
        reasons.append(
            "NIFTY below EMA20 below EMA50"
        )

    if rsi >= 55:
        bullish_score += 1
        reasons.append("positive RSI momentum")

    elif rsi <= 45:
        bearish_score += 1
        reasons.append("negative RSI momentum")

    if nifty_price > previous_close:
        bullish_score += 1
        reasons.append("positive daily price movement")

    elif nifty_price < previous_close:
        bearish_score += 1
        reasons.append("negative daily price movement")

    total = max(
        bullish_score,
        bearish_score,
    )

    if total < 3:
        return NiftySignal(
            decision="NO TRADE",
            direction="NONE",
            confidence=50.0,
            reason="Directional confirmation is insufficient.",
        )

    confidence = min(
        95.0,
        55.0 + total * 10.0,
    )

    if bullish_score > bearish_score:
        return NiftySignal(
            decision="BUY",
            direction="CE",
            confidence=confidence,
            reason="; ".join(reasons),
        )

    if bearish_score > bullish_score:
        return NiftySignal(
            decision="BUY",
            direction="PE",
            confidence=confidence,
            reason="; ".join(reasons),
        )

    return NiftySignal(
        decision="NO TRADE",
        direction="NONE",
        confidence=50.0,
        reason="Bullish and bearish signals are balanced.",
    )