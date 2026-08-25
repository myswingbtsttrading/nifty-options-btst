from dataclasses import dataclass
from typing import Optional

from option_chain_confirmation import (
    OptionChainSnapshot,
    analyze_option_chain,
)


@dataclass(frozen=True)
class NiftySignal:
    decision: str
    direction: str
    confidence: float
    reason: str
    regime: str = "UNKNOWN"
    bullish_score: int = 0
    bearish_score: int = 0
    option_chain_confirmed: bool = False
    option_chain_pcr: Optional[float] = None

    @property
    def is_trade(self) -> bool:
        return self.decision == "BUY"


def _validate_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive.")


def generate_signal(
    nifty_price: float,
    ema20: float,
    ema50: float,
    rsi: float,
    previous_close: float,
    adx: Optional[float] = None,
    vwap: Optional[float] = None,
    option_chain: Optional[OptionChainSnapshot] = None,
) -> NiftySignal:
    """
    Generate the NIFTY 3 PM directional BTST signal.

    Step 1:
        NIFTY trend/momentum analysis.

    Step 2:
        Optional option-chain confirmation.

    When option_chain is supplied, a CE/PE signal is allowed
    only when the option chain independently confirms the same
    direction.

    Contract selection is intentionally handled separately.
    """

    _validate_positive("NIFTY price", nifty_price)
    _validate_positive("EMA20", ema20)
    _validate_positive("EMA50", ema50)
    _validate_positive("previous_close", previous_close)

    if not 0 <= rsi <= 100:
        raise ValueError("RSI must be between 0 and 100.")

    if adx is not None and adx < 0:
        raise ValueError("ADX cannot be negative.")

    if vwap is not None:
        _validate_positive("VWAP", vwap)

    bullish_score = 0
    bearish_score = 0

    bullish_reasons = []
    bearish_reasons = []

    # ---------------------------------------------------------
    # 1. PRIMARY TREND
    # ---------------------------------------------------------
    if nifty_price > ema20 > ema50:
        bullish_score += 3
        bullish_reasons.append(
            "NIFTY above EMA20 above EMA50"
        )

    elif nifty_price < ema20 < ema50:
        bearish_score += 3
        bearish_reasons.append(
            "NIFTY below EMA20 below EMA50"
        )

    elif nifty_price > ema20 and ema20 <= ema50:
        bullish_score += 1
        bullish_reasons.append(
            "NIFTY above EMA20"
        )

    elif nifty_price < ema20 and ema20 >= ema50:
        bearish_score += 1
        bearish_reasons.append(
            "NIFTY below EMA20"
        )

    # ---------------------------------------------------------
    # 2. RSI MOMENTUM
    # ---------------------------------------------------------
    if rsi >= 55:
        bullish_score += 2
        bullish_reasons.append(
            f"positive RSI momentum ({rsi:.1f})"
        )

    elif rsi <= 45:
        bearish_score += 2
        bearish_reasons.append(
            f"negative RSI momentum ({rsi:.1f})"
        )

    # ---------------------------------------------------------
    # 3. DAILY PRICE CONFIRMATION
    # ---------------------------------------------------------
    if nifty_price > previous_close:
        bullish_score += 1
        bullish_reasons.append(
            "NIFTY above previous close"
        )

    elif nifty_price < previous_close:
        bearish_score += 1
        bearish_reasons.append(
            "NIFTY below previous close"
        )

    # ---------------------------------------------------------
    # 4. OPTIONAL VWAP CONFIRMATION
    # ---------------------------------------------------------
    if vwap is not None:
        if nifty_price > vwap:
            bullish_score += 1
            bullish_reasons.append(
                "NIFTY above VWAP"
            )

        elif nifty_price < vwap:
            bearish_score += 1
            bearish_reasons.append(
                "NIFTY below VWAP"
            )

    # ---------------------------------------------------------
    # 5. OPTIONAL ADX CONFIRMATION
    # ---------------------------------------------------------
    if adx is not None:
        if adx >= 25:
            if bullish_score > bearish_score:
                bullish_score += 1
                bullish_reasons.append(
                    f"strong trend (ADX {adx:.1f})"
                )

            elif bearish_score > bullish_score:
                bearish_score += 1
                bearish_reasons.append(
                    f"strong trend (ADX {adx:.1f})"
                )

    # ---------------------------------------------------------
    # MARKET REGIME
    # ---------------------------------------------------------
    if adx is None:
        regime = "UNKNOWN"
    elif adx >= 25:
        regime = "TRENDING"
    else:
        regime = "RANGING"

    # ---------------------------------------------------------
    # NO-TRADE: INSUFFICIENT PRICE SIGNAL
    # ---------------------------------------------------------
    total_score = max(
        bullish_score,
        bearish_score,
    )

    if total_score < 4:
        return NiftySignal(
            decision="NO TRADE",
            direction="NONE",
            confidence=50.0,
            reason=(
                "Directional confirmation is insufficient."
            ),
            regime=regime,
            bullish_score=bullish_score,
            bearish_score=bearish_score,
        )

    # ---------------------------------------------------------
    # NO-TRADE: CONFLICTING PRICE SIGNAL
    # ---------------------------------------------------------
    if bullish_score == bearish_score:
        return NiftySignal(
            decision="NO TRADE",
            direction="NONE",
            confidence=50.0,
            reason=(
                "Bullish and bearish signals are balanced."
            ),
            regime=regime,
            bullish_score=bullish_score,
            bearish_score=bearish_score,
        )

    if bullish_score > bearish_score:
        dominant_score = bullish_score
        opposing_score = bearish_score
        direction = "CE"
        reasons = bullish_reasons

    else:
        dominant_score = bearish_score
        opposing_score = bullish_score
        direction = "PE"
        reasons = bearish_reasons

    score_gap = dominant_score - opposing_score

    confidence = min(
        95.0,
        55.0
        + (dominant_score * 5.0)
        + (score_gap * 5.0),
    )

    # ---------------------------------------------------------
    # STEP 2 — OPTION-CHAIN CONFIRMATION
    # ---------------------------------------------------------
    if option_chain is not None:
        chain_confirmation = analyze_option_chain(
            option_chain
        )

        if not chain_confirmation.confirmed:
            return NiftySignal(
                decision="NO TRADE",
                direction="NONE",
                confidence=round(
                    min(confidence, 64.0),
                    2,
                ),
                reason=(
                    "NIFTY directional signal was not "
                    "confirmed by the option chain. "
                    f"{chain_confirmation.reason}"
                ),
                regime=regime,
                bullish_score=bullish_score,
                bearish_score=bearish_score,
                option_chain_confirmed=False,
                option_chain_pcr=chain_confirmation.pcr,
            )

        if chain_confirmation.direction != direction:
            return NiftySignal(
                decision="NO TRADE",
                direction="NONE",
                confidence=round(
                    min(confidence, 64.0),
                    2,
                ),
                reason=(
                    "NIFTY direction conflicts with "
                    "option-chain direction. "
                    f"NIFTY={direction}, "
                    f"Chain={chain_confirmation.direction}."
                ),
                regime=regime,
                bullish_score=bullish_score,
                bearish_score=bearish_score,
                option_chain_confirmed=False,
                option_chain_pcr=chain_confirmation.pcr,
            )

        reasons = reasons + [
            "option-chain confirmation: "
            + chain_confirmation.reason
        ]

        confidence = min(
            95.0,
            confidence + 5.0,
        )

        return NiftySignal(
            decision="BUY",
            direction=direction,
            confidence=round(confidence, 2),
            reason="; ".join(reasons),
            regime=regime,
            bullish_score=bullish_score,
            bearish_score=bearish_score,
            option_chain_confirmed=True,
            option_chain_pcr=chain_confirmation.pcr,
        )

    # ---------------------------------------------------------
    # STEP 1 COMPATIBILITY MODE
    # ---------------------------------------------------------
    if confidence < 65.0:
        return NiftySignal(
            decision="NO TRADE",
            direction="NONE",
            confidence=round(confidence, 2),
            reason=(
                "Signal strength is below the "
                "BTST confidence threshold."
            ),
            regime=regime,
            bullish_score=bullish_score,
            bearish_score=bearish_score,
        )

    return NiftySignal(
        decision="BUY",
        direction=direction,
        confidence=round(confidence, 2),
        reason="; ".join(reasons),
        regime=regime,
        bullish_score=bullish_score,
        bearish_score=bearish_score,
    )