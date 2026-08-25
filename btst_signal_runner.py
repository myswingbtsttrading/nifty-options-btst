from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Optional

from option_selector import (
    OptionContract,
    select_contract,
)
from option_strategy import (
    NiftySignal,
    generate_signal,
)
from signal_builder import (
    BTSTSignal,
    SignalInput,
    build_btst_signal,
)


@dataclass(frozen=True)
class MarketSnapshot:
    """
    Market information required to create the 3 PM BTST signal.

    The runner deliberately accepts already-normalized values.
    The live data provider will be connected in a later step.
    """

    timestamp: datetime

    nifty_price: float
    ema20: float
    ema50: float
    rsi: float
    previous_close: float

    adx: Optional[float] = None
    vwap: Optional[float] = None

    option_chain: object | None = None


@dataclass(frozen=True)
class OptionQuote:
    """
    Current quote for the selected NIFTY option.
    """

    expiry: date
    strike: float
    option_type: str
    price: float


@dataclass(frozen=True)
class BTSTRunnerConfig:
    """
    Configuration for the 3 PM BTST signal runner.
    """

    capital: float = 100000.0
    lot_size: int = 65

    stop_loss_pct: float = 0.15
    target_pct: float = 0.30

    risk_per_trade_pct: float = 0.01
    max_allocation_pct: float = 0.20

    minimum_confidence: float = 65.0

    selection_mode: str = "ATM"


def _validate_snapshot(
    snapshot: MarketSnapshot,
) -> None:
    if snapshot.nifty_price <= 0:
        raise ValueError(
            "NIFTY price must be positive."
        )

    if snapshot.ema20 <= 0:
        raise ValueError(
            "EMA20 must be positive."
        )

    if snapshot.ema50 <= 0:
        raise ValueError(
            "EMA50 must be positive."
        )

    if snapshot.previous_close <= 0:
        raise ValueError(
            "Previous close must be positive."
        )

    if not 0 <= snapshot.rsi <= 100:
        raise ValueError(
            "RSI must be between 0 and 100."
        )

    if (
        snapshot.adx is not None
        and snapshot.adx < 0
    ):
        raise ValueError(
            "ADX cannot be negative."
        )

    if snapshot.vwap is not None and snapshot.vwap <= 0:
        raise ValueError(
            "VWAP must be positive."
        )


def generate_directional_signal(
    snapshot: MarketSnapshot,
) -> NiftySignal:
    """
    Generate the NIFTY directional signal from a market snapshot.
    """

    _validate_snapshot(snapshot)

    return generate_signal(
        nifty_price=snapshot.nifty_price,
        ema20=snapshot.ema20,
        ema50=snapshot.ema50,
        rsi=snapshot.rsi,
        previous_close=snapshot.previous_close,
        adx=snapshot.adx,
        vwap=snapshot.vwap,
        option_chain=snapshot.option_chain,
    )


def select_btst_contract(
    snapshot: MarketSnapshot,
    expiry: date,
    selection_mode: str = "ATM",
) -> OptionContract:
    """
    Select the option contract corresponding to the
    directional NIFTY signal.
    """

    signal = generate_directional_signal(
        snapshot
    )

    if signal.direction not in {
        "CE",
        "PE",
    }:
        raise ValueError(
            "Cannot select an option contract "
            "without a CE/PE directional signal."
        )

    return select_contract(
        nifty_price=snapshot.nifty_price,
        expiry=expiry,
        option_type=signal.direction,
        selection_mode=selection_mode,
    )


def build_signal_from_quote(
    snapshot: MarketSnapshot,
    option_quote: OptionQuote,
    config: BTSTRunnerConfig = BTSTRunnerConfig(),
) -> BTSTSignal:
    """
    Build the complete actionable BTST signal.

    This is the main orchestration function used by the
    future 3 PM scheduler.
    """

    _validate_snapshot(snapshot)

    signal = generate_directional_signal(
        snapshot
    )

    contract = OptionContract(
        expiry=option_quote.expiry,
        strike=option_quote.strike,
        option_type=option_quote.option_type.upper(),
    )

    signal_input = SignalInput(
        timestamp=snapshot.timestamp,
        nifty_price=snapshot.nifty_price,
        option_contract=contract,
        option_price=option_quote.price,
        expiry=option_quote.expiry,
        signal=signal,
    )

    return build_btst_signal(
        signal_input=signal_input,
        capital=config.capital,
        lot_size=config.lot_size,
        stop_loss_pct=config.stop_loss_pct,
        target_pct=config.target_pct,
        risk_per_trade_pct=config.risk_per_trade_pct,
        max_allocation_pct=config.max_allocation_pct,
        minimum_confidence=config.minimum_confidence,
    )


def run_3pm_signal(
    snapshot: MarketSnapshot,
    expiry: date,
    option_quote_loader: Callable[
        [OptionContract],
        OptionQuote,
    ],
    config: BTSTRunnerConfig = BTSTRunnerConfig(),
) -> BTSTSignal:
    """
    Complete 3 PM signal-generation pipeline.

    Flow:

        Market snapshot
              ↓
        NIFTY direction
              ↓
        CE / PE
              ↓
        ATM / ITM / OTM contract
              ↓
        option premium
              ↓
        risk manager
              ↓
        final BTST signal
    """

    _validate_snapshot(snapshot)

    signal = generate_directional_signal(
        snapshot
    )

    if signal.direction not in {
        "CE",
        "PE",
    }:
        # Build a safe NO TRADE result without requiring
        # an option quote.
        fallback_contract = OptionContract(
            expiry=expiry,
            strike=round(
                snapshot.nifty_price / 50
            ) * 50,
            option_type="CE",
        )

        signal_input = SignalInput(
            timestamp=snapshot.timestamp,
            nifty_price=snapshot.nifty_price,
            option_contract=fallback_contract,
            option_price=1.0,
            expiry=expiry,
            signal=signal,
        )

        return build_btst_signal(
            signal_input=signal_input,
            capital=config.capital,
            lot_size=config.lot_size,
            stop_loss_pct=config.stop_loss_pct,
            target_pct=config.target_pct,
            risk_per_trade_pct=config.risk_per_trade_pct,
            max_allocation_pct=config.max_allocation_pct,
            minimum_confidence=config.minimum_confidence,
        )

    contract = select_contract(
        nifty_price=snapshot.nifty_price,
        expiry=expiry,
        option_type=signal.direction,
        selection_mode=config.selection_mode,
    )

    option_quote = option_quote_loader(
        contract
    )

    if option_quote.price <= 0:
        raise ValueError(
            "Option quote price must be positive."
        )

    if (
        option_quote.expiry
        != contract.expiry
    ):
        raise ValueError(
            "Option quote expiry does not match "
            "selected contract."
        )

    if (
        option_quote.strike
        != contract.strike
    ):
        raise ValueError(
            "Option quote strike does not match "
            "selected contract."
        )

    if (
        option_quote.option_type.upper()
        != contract.option_type
    ):
        raise ValueError(
            "Option quote type does not match "
            "selected contract."
        )

    return build_signal_from_quote(
        snapshot=snapshot,
        option_quote=option_quote,
        config=config,
    )