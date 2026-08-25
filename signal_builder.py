from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from backtest_config import DEFAULT_CONFIG
from option_selector import OptionContract
from option_strategy import NiftySignal
from risk_manager import (
    RiskConfig,
    TradePlan,
    calculate_trade_plan,
)


@dataclass(frozen=True)
class SignalInput:
    """
    Market and option information available at signal time.
    """

    timestamp: datetime

    nifty_price: float

    option_contract: OptionContract
    option_price: float

    expiry: date

    signal: NiftySignal


@dataclass(frozen=True)
class BTSTSignal:
    """
    Final actionable BTST recommendation.

    This object contains everything required by the future
    Telegram notification layer.
    """

    timestamp: datetime

    decision: str
    direction: str
    confidence: float

    nifty_price: float

    expiry: date
    strike: float
    option_type: str

    entry_price: float
    stop_loss: float
    target: float

    lot_size: int
    lots: int
    quantity: int

    capital_required: float
    planned_risk: float
    planned_reward: float

    risk_reward_ratio: float

    reason: str

    @property
    def is_trade(self) -> bool:
        return (
            self.decision == "BUY"
            and self.quantity > 0
            and self.lots > 0
        )

    @property
    def hold_instruction(self) -> str:
        if not self.is_trade:
            return "NO TRADE"

        return "BUY AT 3:00 PM → HOLD OVERNIGHT → EXIT NEXT MORNING"

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "decision": self.decision,
            "direction": self.direction,
            "confidence": self.confidence,
            "nifty_price": self.nifty_price,
            "expiry": self.expiry.isoformat(),
            "strike": self.strike,
            "option_type": self.option_type,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "lot_size": self.lot_size,
            "lots": self.lots,
            "quantity": self.quantity,
            "capital_required": self.capital_required,
            "planned_risk": self.planned_risk,
            "planned_reward": self.planned_reward,
            "risk_reward_ratio": self.risk_reward_ratio,
            "reason": self.reason,
        }


def _validate_signal_input(
    signal_input: SignalInput,
) -> None:
    if signal_input.nifty_price <= 0:
        raise ValueError(
            "NIFTY price must be positive."
        )

    if signal_input.option_price <= 0:
        raise ValueError(
            "Option price must be positive."
        )

    if signal_input.expiry < signal_input.timestamp.date():
        raise ValueError(
            "Option expiry cannot be before signal date."
        )

    if signal_input.option_contract.strike <= 0:
        raise ValueError(
            "Option strike must be positive."
        )

    option_type = (
        signal_input.option_contract.option_type
        .upper()
    )

    if option_type not in {"CE", "PE"}:
        raise ValueError(
            "Option type must be CE or PE."
        )


def build_btst_signal(
    signal_input: SignalInput,
    capital: float = DEFAULT_CONFIG.initial_capital,
    lot_size: int = DEFAULT_CONFIG.lot_size,
    stop_loss_pct: float = DEFAULT_CONFIG.stop_loss_pct,
    target_pct: float = DEFAULT_CONFIG.target_pct,
    risk_per_trade_pct: float = DEFAULT_CONFIG.risk_per_trade_pct,
    max_allocation_pct: float = DEFAULT_CONFIG.max_allocation_pct,
    minimum_confidence: float = DEFAULT_CONFIG.minimum_confidence,
) -> BTSTSignal:
    """
    Convert the directional strategy output and option quote
    into a complete BTST trade recommendation.

    A trade is only considered actionable when:

    - strategy decision is BUY
    - confidence meets minimum threshold
    - option premium is valid
    - at least one complete option lot fits the risk rules
    """

    _validate_signal_input(
        signal_input
    )

    signal = signal_input.signal

    option_type = (
        signal_input.option_contract.option_type
        .upper()
    )

    decision = signal.decision.upper()

    # Never create an executable trade below the configured
    # confidence threshold.
    if (
        decision == "BUY"
        and signal.confidence < minimum_confidence
    ):
        decision = "WAIT"

    risk_config = RiskConfig(
        stop_loss_pct=stop_loss_pct,
        target_pct=target_pct,
        risk_per_trade_pct=risk_per_trade_pct,
        max_allocation_pct=max_allocation_pct,
    )

    plan: Optional[TradePlan] = None

    if decision == "BUY":
        plan = calculate_trade_plan(
            entry_price=signal_input.option_price,
            capital=capital,
            lot_size=lot_size,
            config=risk_config,
        )

        # A signal without enough capital to purchase a
        # complete lot is not actionable.
        if not plan.is_tradeable:
            decision = "WAIT"

    if plan is None:
        return BTSTSignal(
            timestamp=signal_input.timestamp,
            decision=decision,
            direction=option_type,
            confidence=signal.confidence,
            nifty_price=signal_input.nifty_price,
            expiry=signal_input.expiry,
            strike=signal_input.option_contract.strike,
            option_type=option_type,
            entry_price=round(
                signal_input.option_price,
                2,
            ),
            stop_loss=0.0,
            target=0.0,
            lot_size=lot_size,
            lots=0,
            quantity=0,
            capital_required=0.0,
            planned_risk=0.0,
            planned_reward=0.0,
            risk_reward_ratio=0.0,
            reason=signal.reason,
        )

    return BTSTSignal(
        timestamp=signal_input.timestamp,
        decision=decision,
        direction=option_type,
        confidence=signal.confidence,
        nifty_price=signal_input.nifty_price,
        expiry=signal_input.expiry,
        strike=signal_input.option_contract.strike,
        option_type=option_type,
        entry_price=plan.entry_price,
        stop_loss=plan.stop_loss,
        target=plan.target,
        lot_size=plan.lot_size,
        lots=plan.lots,
        quantity=plan.quantity,
        capital_required=plan.capital_required,
        planned_risk=plan.planned_risk,
        planned_reward=plan.planned_reward,
        risk_reward_ratio=plan.risk_reward_ratio,
        reason=signal.reason,
    )


def format_btst_alert(
    signal: BTSTSignal,
) -> str:
    """
    Format the final BTST recommendation for Telegram.

    No broker order is submitted here.
    """

    if not signal.is_trade:
        return (
            "NIFTY BTST SIGNAL\n"
            "\n"
            f"Decision: {signal.decision}\n"
            f"Confidence: "
            f"{signal.confidence:.1f}%\n"
            f"NIFTY: "
            f"{signal.nifty_price:.2f}\n"
            f"Reason: {signal.reason}\n"
            "\n"
            "No actionable BTST trade."
        )

    return (
        "NIFTY BTST SIGNAL\n"
        "\n"
        f"Decision: BUY {signal.option_type}\n"
        f"Confidence: "
        f"{signal.confidence:.1f}%\n"
        f"NIFTY: "
        f"{signal.nifty_price:.2f}\n"
        "\n"
        f"Strike: "
        f"{signal.strike:.0f} {signal.option_type}\n"
        f"Expiry: "
        f"{signal.expiry.isoformat()}\n"
        f"Entry: "
        f"₹{signal.entry_price:.2f}\n"
        f"Stop Loss: "
        f"₹{signal.stop_loss:.2f}\n"
        f"Target: "
        f"₹{signal.target:.2f}\n"
        "\n"
        f"Lots: {signal.lots}\n"
        f"Quantity: {signal.quantity}\n"
        f"Capital: "
        f"₹{signal.capital_required:,.2f}\n"
        f"Risk: "
        f"₹{signal.planned_risk:,.2f}\n"
        f"Potential Reward: "
        f"₹{signal.planned_reward:,.2f}\n"
        f"Risk/Reward: "
        f"1:{signal.risk_reward_ratio:.2f}\n"
        "\n"
        f"Plan: {signal.hold_instruction}\n"
        f"Reason: {signal.reason}"
    )