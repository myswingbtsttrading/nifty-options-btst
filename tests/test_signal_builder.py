from datetime import date, datetime

import pytest

from option_selector import OptionContract
from option_strategy import NiftySignal
from signal_builder import (
    BTSTSignal,
    SignalInput,
    build_btst_signal,
    format_btst_alert,
)


def _input(
    decision: str = "BUY",
    confidence: float = 80.0,
    option_type: str = "CE",
    option_price: float = 100.0,
) -> SignalInput:
    timestamp = datetime(
        2026,
        8,
        24,
        15,
        0,
    )

    signal = NiftySignal(
        decision=decision,
        direction=option_type,
        confidence=confidence,
        reason="Strong bullish BTST setup",
        regime="TRENDING",
        bullish_score=8,
        bearish_score=2,
    )

    contract = OptionContract(
        expiry=date(2026, 8, 27),
        strike=25000,
        option_type=option_type,
    )

    return SignalInput(
        timestamp=timestamp,
        nifty_price=25020.0,
        option_contract=contract,
        option_price=option_price,
        expiry=date(2026, 8, 27),
        signal=signal,
    )


def test_build_buy_signal():
    result = build_btst_signal(
        signal_input=_input(),
        capital=100000.0,
        lot_size=65,
        stop_loss_pct=0.10,
        target_pct=0.20,
        risk_per_trade_pct=0.02,
        max_allocation_pct=0.20,
        minimum_confidence=65.0,
    )

    assert isinstance(result, BTSTSignal)

    assert result.decision == "BUY"
    assert result.direction == "CE"
    assert result.option_type == "CE"

    assert result.nifty_price == 25020.0
    assert result.strike == 25000
    assert result.expiry == date(
        2026,
        8,
        27,
    )

    assert result.entry_price == 100.0
    assert result.stop_loss == 90.0
    assert result.target == 120.0

    assert result.lot_size == 65
    assert result.lots == 3
    assert result.quantity == 195

    assert result.capital_required == 19500.0
    assert result.planned_risk == 1950.0
    assert result.planned_reward == 3900.0

    assert result.risk_reward_ratio == 2.0

    assert result.is_trade is True

    assert (
        result.hold_instruction
        == "BUY AT 3:00 PM → HOLD OVERNIGHT → EXIT NEXT MORNING"
    )


def test_build_buy_signal_with_default_risk():
    result = build_btst_signal(
        signal_input=_input(),
        capital=100000.0,
        lot_size=65,
    )

    assert result.decision == "BUY"
    assert result.entry_price == 100.0

    # Default risk:
    # stop = 15% -> ₹85
    # target = 30% -> ₹130
    assert result.stop_loss == 85.0
    assert result.target == 130.0

    # Risk per option = ₹15.
    # Risk per lot = ₹15 × 65 = ₹975.
    # Risk budget = ₹1,000.
    #
    # Therefore only 1 complete lot fits.
    assert result.lots == 1
    assert result.quantity == 65

    assert result.capital_required == 6500.0
    assert result.planned_risk == 975.0
    assert result.planned_reward == 1950.0

    assert result.risk_reward_ratio == 2.0


def test_buy_signal_below_confidence_becomes_wait():
    result = build_btst_signal(
        signal_input=_input(
            confidence=60.0,
        ),
        capital=100000.0,
        lot_size=65,
        minimum_confidence=65.0,
    )

    assert result.decision == "WAIT"
    assert result.is_trade is False
    assert result.lots == 0
    assert result.quantity == 0
    assert result.capital_required == 0.0


def test_non_buy_signal_does_not_create_trade():
    result = build_btst_signal(
        signal_input=_input(
            decision="WAIT",
            confidence=80.0,
        ),
        capital=100000.0,
        lot_size=65,
    )

    assert result.decision == "WAIT"
    assert result.is_trade is False
    assert result.lots == 0
    assert result.quantity == 0


def test_zero_lot_trade_becomes_wait():
    result = build_btst_signal(
        signal_input=_input(
            option_price=500.0,
        ),
        capital=100000.0,
        lot_size=65,
        stop_loss_pct=0.20,
        target_pct=0.40,
        risk_per_trade_pct=0.01,
        max_allocation_pct=0.20,
    )

    assert result.decision == "WAIT"
    assert result.is_trade is False
    assert result.lots == 0
    assert result.quantity == 0


def test_pe_signal():
    result = build_btst_signal(
        signal_input=_input(
            option_type="PE",
        ),
        capital=100000.0,
        lot_size=65,
    )

    assert result.decision == "BUY"
    assert result.direction == "PE"
    assert result.option_type == "PE"
    assert result.is_trade is True


def test_alert_contains_trade_details():
    result = build_btst_signal(
        signal_input=_input(),
        capital=100000.0,
        lot_size=65,
        stop_loss_pct=0.10,
        target_pct=0.20,
        risk_per_trade_pct=0.02,
        max_allocation_pct=0.20,
    )

    message = format_btst_alert(
        result,
    )

    assert "NIFTY BTST SIGNAL" in message
    assert "Decision: BUY CE" in message
    assert "Confidence: 80.0%" in message
    assert "NIFTY: 25020.00" in message
    assert "Strike: 25000 CE" in message
    assert "Expiry: 2026-08-27" in message
    assert "Entry: ₹100.00" in message
    assert "Stop Loss: ₹90.00" in message
    assert "Target: ₹120.00" in message
    assert "Lots: 3" in message
    assert "Quantity: 195" in message
    assert "Capital: ₹19,500.00" in message
    assert "Risk: ₹1,950.00" in message
    assert "Potential Reward: ₹3,900.00" in message
    assert "Risk/Reward: 1:2.00" in message
    assert "BUY AT 3:00 PM" in message


def test_wait_alert_does_not_show_fake_trade():
    result = build_btst_signal(
        signal_input=_input(
            decision="WAIT",
            confidence=50.0,
        ),
        capital=100000.0,
        lot_size=65,
    )

    message = format_btst_alert(
        result,
    )

    assert "Decision: WAIT" in message
    assert "No actionable BTST trade." in message

    assert "Stop Loss: ₹0.00" not in message
    assert "Target: ₹0.00" not in message
    assert "Lots: 0" not in message


def test_signal_to_dict():
    result = build_btst_signal(
        signal_input=_input(),
        capital=100000.0,
        lot_size=65,
    )

    data = result.to_dict()

    assert data["decision"] == "BUY"
    assert data["direction"] == "CE"
    assert data["confidence"] == 80.0
    assert data["nifty_price"] == 25020.0
    assert data["strike"] == 25000
    assert data["option_type"] == "CE"
    assert data["entry_price"] == 100.0
    assert data["stop_loss"] == 85.0
    assert data["target"] == 130.0

    # Default risk settings allow only one complete lot:
    # ₹1,000 risk budget / ₹975 risk per lot = 1 lot.
    assert data["lots"] == 1
    assert data["quantity"] == 65

    assert data["capital_required"] == 6500.0
    assert data["planned_risk"] == 975.0
    assert data["planned_reward"] == 1950.0


def test_signal_to_dict_custom_risk_settings():
    result = build_btst_signal(
        signal_input=_input(),
        capital=100000.0,
        lot_size=65,
        stop_loss_pct=0.10,
        target_pct=0.20,
        risk_per_trade_pct=0.02,
        max_allocation_pct=0.20,
    )

    data = result.to_dict()

    assert data["lots"] == 3
    assert data["quantity"] == 195
    assert data["capital_required"] == 19500.0
    assert data["planned_risk"] == 1950.0
    assert data["planned_reward"] == 3900.0


def test_invalid_nifty_price():
    signal_input = _input()

    invalid = SignalInput(
        timestamp=signal_input.timestamp,
        nifty_price=0.0,
        option_contract=signal_input.option_contract,
        option_price=signal_input.option_price,
        expiry=signal_input.expiry,
        signal=signal_input.signal,
    )

    with pytest.raises(ValueError):
        build_btst_signal(
            signal_input=invalid,
        )


def test_invalid_option_price():
    signal_input = _input(
        option_price=0.0,
    )

    with pytest.raises(ValueError):
        build_btst_signal(
            signal_input=signal_input,
        )


def test_expired_option_is_rejected():
    signal_input = _input()

    invalid = SignalInput(
        timestamp=signal_input.timestamp,
        nifty_price=signal_input.nifty_price,
        option_contract=signal_input.option_contract,
        option_price=signal_input.option_price,
        expiry=date(2026, 8, 23),
        signal=signal_input.signal,
    )

    with pytest.raises(ValueError):
        build_btst_signal(
            signal_input=invalid,
        )


def test_invalid_option_type_is_rejected():
    signal_input = _input()

    invalid_contract = OptionContract(
        expiry=date(2026, 8, 27),
        strike=25000,
        option_type="XX",
    )

    invalid = SignalInput(
        timestamp=signal_input.timestamp,
        nifty_price=signal_input.nifty_price,
        option_contract=invalid_contract,
        option_price=signal_input.option_price,
        expiry=signal_input.expiry,
        signal=signal_input.signal,
    )

    with pytest.raises(ValueError):
        build_btst_signal(
            signal_input=invalid,
        )


def test_alert_is_deterministic():
    result = build_btst_signal(
        signal_input=_input(),
        capital=100000.0,
        lot_size=65,
    )

    first = format_btst_alert(
        result,
    )

    second = format_btst_alert(
        result,
    )

    assert first == second