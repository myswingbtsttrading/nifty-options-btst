import json
from datetime import datetime

import main


def _position():
    return {
        "timestamp": "2026-08-27T15:00:00",
        "decision": "BUY",
        "direction": "CE",
        "confidence": 75.0,
        "nifty_price": 25020.0,
        "expiry": "2026-09-03",
        "strike": 25000.0,
        "option_type": "CE",
        "entry_price": 100.0,
        "stop_loss": 85.0,
        "target": 130.0,
        "lot_size": 65,
        "lots": 1,
        "quantity": 65,
        "capital_required": 6500.0,
        "planned_risk": 975.0,
        "planned_reward": 1950.0,
        "risk_reward_ratio": 2.0,
        "reason": "Test BUY signal.",
    }


def test_save_and_load_signal_state(
    monkeypatch,
    tmp_path,
):
    state_file = (
        tmp_path
        / "live_btst_signal.json"
    )

    monkeypatch.setattr(
        main,
        "DATA_DIR",
        tmp_path,
    )

    monkeypatch.setattr(
        main,
        "STATE_FILE",
        state_file,
    )

    class Signal:
        def to_dict(self):
            return _position()

    main._save_signal_state(
        Signal()
    )

    assert state_file.exists()

    payload = main._load_signal_state()

    assert payload["decision"] == "BUY"
    assert payload["strike"] == 25000.0
    assert payload["option_type"] == "CE"
    assert payload["entry_price"] == 100.0
    assert payload["quantity"] == 65


def test_sell_message_calculates_profit():
    message = main._format_sell_message(
        position=_position(),
        exit_price=120.0,
        exit_timestamp=datetime(
            2026,
            8,
            28,
            9,
            30,
        ),
    )

    assert "PROFIT" in message
    assert "Entry Premium: ₹100.00" in message
    assert "Exit Premium: ₹120.00" in message
    assert "P/L: ₹1,300.00" in message
    assert "P/L %: +20.00%" in message
    assert "9:30 AM" in message


def test_sell_message_calculates_loss():
    message = main._format_sell_message(
        position=_position(),
        exit_price=90.0,
        exit_timestamp=datetime(
            2026,
            8,
            28,
            9,
            30,
        ),
    )

    assert "LOSS" in message
    assert "P/L: ₹-650.00" in message
    assert "P/L %: -10.00%" in message
    assert "9:30 AM" in message


def test_run_930_fetches_actual_option_premium_and_sends_alert(
    monkeypatch,
    tmp_path,
):
    state_file = (
        tmp_path
        / "live_btst_signal.json"
    )

    state_file.write_text(
        json.dumps(
            _position()
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        main,
        "STATE_FILE",
        state_file,
    )

    class FakeOptionQuote:
        price = 120.0
        timestamp = datetime(
            2026,
            8,
            28,
            9,
            30,
        )

    class FakeChain:
        pass

    calls = []

    monkeypatch.setattr(
        main,
        "fetch_nifty_option_chain",
        lambda: FakeChain(),
    )

    monkeypatch.setattr(
        main,
        "find_option_quote",
        lambda **kwargs: FakeOptionQuote(),
    )

    monkeypatch.setattr(
        main,
        "send_alert",
        lambda message: calls.append(message),
    )

    main.run_930()

    assert len(calls) == 1
    assert "NIFTY BTST SELL ALERT" in calls[0]
    assert "Exit Premium: ₹120.00" in calls[0]
    assert "P/L: ₹1,300.00" in calls[0]

    assert not state_file.exists()


def test_run_930_requires_position_state(
    monkeypatch,
    tmp_path,
):
    state_file = (
        tmp_path
        / "missing.json"
    )

    monkeypatch.setattr(
        main,
        "STATE_FILE",
        state_file,
    )

    try:
        main.run_930()
    except Exception as exc:
        assert (
            "No BTST position state found"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected missing BTST position state to fail."
        )


def test_run_915_remains_backward_compatible(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        main,
        "run_930",
        lambda: calls.append(True),
    )

    main.run_915()

    assert calls == [True]