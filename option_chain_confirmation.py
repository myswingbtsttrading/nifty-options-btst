from dataclasses import dataclass


@dataclass(frozen=True)
class OptionChainSnapshot:
    """
    Aggregated NIFTY option-chain data around ATM.

    All OI and volume values should use the same unit/source
    and cover the same set of strikes.
    """

    ce_oi: float
    pe_oi: float

    ce_oi_change: float
    pe_oi_change: float

    ce_volume: float
    pe_volume: float

    def __post_init__(self) -> None:
        values = {
            "ce_oi": self.ce_oi,
            "pe_oi": self.pe_oi,
            "ce_oi_change": self.ce_oi_change,
            "pe_oi_change": self.pe_oi_change,
            "ce_volume": self.ce_volume,
            "pe_volume": self.pe_volume,
        }

        for name, value in values.items():
            if value < 0:
                raise ValueError(f"{name} cannot be negative.")

        if self.ce_oi == 0:
            raise ValueError("ce_oi must be greater than zero.")


@dataclass(frozen=True)
class OptionChainConfirmation:
    """
    Directional confirmation from the NIFTY option chain.
    """

    direction: str
    confirmed: bool
    score: int
    pcr: float
    reason: str

    @property
    def is_bullish(self) -> bool:
        return self.direction == "CE"

    @property
    def is_bearish(self) -> bool:
        return self.direction == "PE"


def analyze_option_chain(
    snapshot: OptionChainSnapshot,
) -> OptionChainConfirmation:
    """
    Analyse the option chain for directional BTST confirmation.

    The model deliberately uses three independent components:

    1. Put/Call OI ratio (PCR)
    2. Relative OI change
    3. Relative volume

    Interpretation:

        PCR >= 1.10 -> bullish
        PCR <= 0.90 -> bearish

        PE OI change > CE OI change -> bullish
        CE OI change > PE OI change -> bearish

        PE volume > CE volume -> bullish
        CE volume > PE volume -> bearish

    A direction is confirmed when at least two of the three
    components agree.

    This is a confirmation layer, not the primary NIFTY signal.
    """

    pcr = snapshot.pe_oi / snapshot.ce_oi

    bullish_score = 0
    bearish_score = 0

    bullish_reasons = []
    bearish_reasons = []

    # ---------------------------------------------------------
    # 1. PUT/CALL OI RATIO
    # ---------------------------------------------------------
    if pcr >= 1.10:
        bullish_score += 1
        bullish_reasons.append(f"bullish PCR ({pcr:.2f})")

    elif pcr <= 0.90:
        bearish_score += 1
        bearish_reasons.append(f"bearish PCR ({pcr:.2f})")

    # ---------------------------------------------------------
    # 2. OI CHANGE
    #
    # Higher PE OI change is treated as bullish relative
    # positioning; higher CE OI change is treated as bearish.
    # ---------------------------------------------------------
    if snapshot.pe_oi_change > snapshot.ce_oi_change:
        bullish_score += 1
        bullish_reasons.append("PE OI change stronger than CE OI change")

    elif snapshot.ce_oi_change > snapshot.pe_oi_change:
        bearish_score += 1
        bearish_reasons.append("CE OI change stronger than PE OI change")

    # ---------------------------------------------------------
    # 3. VOLUME
    # ---------------------------------------------------------
    if snapshot.pe_volume > snapshot.ce_volume:
        bullish_score += 1
        bullish_reasons.append("PE volume stronger than CE volume")

    elif snapshot.ce_volume > snapshot.pe_volume:
        bearish_score += 1
        bearish_reasons.append("CE volume stronger than PE volume")

    # ---------------------------------------------------------
    # FINAL CONFIRMATION
    # ---------------------------------------------------------
    if bullish_score >= 2 and bullish_score > bearish_score:
        return OptionChainConfirmation(
            direction="CE",
            confirmed=True,
            score=bullish_score,
            pcr=round(pcr, 4),
            reason="; ".join(bullish_reasons),
        )

    if bearish_score >= 2 and bearish_score > bullish_score:
        return OptionChainConfirmation(
            direction="PE",
            confirmed=True,
            score=bearish_score,
            pcr=round(pcr, 4),
            reason="; ".join(bearish_reasons),
        )

    return OptionChainConfirmation(
        direction="NONE",
        confirmed=False,
        score=max(bullish_score, bearish_score),
        pcr=round(pcr, 4),
        reason="Option-chain confirmation is insufficient.",
    )