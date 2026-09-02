import json
from datetime import date, datetime
from pathlib import Path

import pytest

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


def _configure_state(
    monkeypatch,
    tmp_path,
):
    state_file = (
        tmp_path
        / "live_btst_signal.json"
    )

    exit_file = (
        tmp_path
        / "last_btst_exit.json"
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

    monkeypatch.setattr(
        main,
        "EXIT_FILE",
        exit_file,
    )

    return state_file, exit_file


def test_save_and_load_signal_state(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
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


def test_run_930_fetches_exact_live_option_and_closes_state(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    state_file.write_text(
        json.dumps(
            _position()
        ),
        encoding="utf-8",
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

    calls = []

    monkeypatch.setattr(
        main,
        "fetch_nifty_option_chain",
        lambda: {"fake": "chain"},
    )

    def fake_find_option_quote(
        **kwargs,
    ):
        calls.append(kwargs)
        return FakeOptionQuote()

    monkeypatch.setattr(
        main,
        "find_option_quote",
        fake_find_option_quote,
    )

    monkeypatch.setattr(
        main,
        "send_alert",
        lambda message: calls.append(
            {
                "message": message
            }
        ),
    )

    main.run_930()

    quote_call = calls[0]

    assert quote_call["expiry"] == date(
        2026,
        9,
        3,
    )

    assert quote_call["strike"] == 25000.0
    assert quote_call["option_type"] == "CE"

    alert = calls[1]["message"]

    assert "NIFTY BTST SELL ALERT" in alert
    assert "Exit Premium: ₹120.00" in alert
    assert "P/L: ₹1,300.00" in alert

    assert not state_file.exists()

    assert exit_file.exists()

    exit_payload = json.loads(
        exit_file.read_text(
            encoding="utf-8"
        )
    )

    assert exit_payload["status"] == "CLOSED"
    assert exit_payload["exit_price"] == 120.0
    assert exit_payload["pnl"] == 1300.0
    assert exit_payload["pnl_pct"] == 20.0


def test_run_915_remains_backward_compatible(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    state_file.write_text(
        json.dumps(
            _position()
        ),
        encoding="utf-8",
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

    calls = []

    monkeypatch.setattr(
        main,
        "fetch_nifty_option_chain",
        lambda: {"fake": "chain"},
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

    main.run_915()

    assert len(calls) == 1
    assert "SELL ALERT" in calls[0]
    assert not state_file.exists()
    assert exit_file.exists()


def test_run_930_requires_position_state(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    with pytest.raises(
        Exception,
        match="No BTST position state found",
    ):
        main.run_930()

    assert not state_file.exists()


def test_run_930_keeps_state_when_telegram_fails(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    state_file.write_text(
        json.dumps(
            _position()
        ),
        encoding="utf-8",
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

    monkeypatch.setattr(
        main,
        "fetch_nifty_option_chain",
        lambda: {"fake": "chain"},
    )

    monkeypatch.setattr(
        main,
        "find_option_quote",
        lambda **kwargs: FakeOptionQuote(),
    )

    def fail_alert(message):
        raise RuntimeError(
            "Telegram unavailable"
        )

    monkeypatch.setattr(
        main,
        "send_alert",
        fail_alert,
    )

    with pytest.raises(
        RuntimeError,
        match="Telegram unavailable",
    ):
        main.run_930()

    assert state_file.exists()
    assert not exit_file.exists()


def test_run_930_keeps_state_when_live_premium_is_invalid(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    state_file.write_text(
        json.dumps(
            _position()
        ),
        encoding="utf-8",
    )

    class FakeOptionQuote:
        price = 0.0
        timestamp = datetime(
            2026,
            8,
            28,
            9,
            30,
        )

    monkeypatch.setattr(
        main,
        "fetch_nifty_option_chain",
        lambda: {"fake": "chain"},
    )

    monkeypatch.setattr(
        main,
        "find_option_quote",
        lambda **kwargs: FakeOptionQuote(),
    )

    with pytest.raises(
        Exception,
        match="positive",
    ):
        main.run_930()

    assert state_file.exists()
    assert not exit_file.exists()


def test_load_state_rejects_invalid_option_type(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    position = _position()
    position["option_type"] = "XX"

    state_file.write_text(
        json.dumps(position),
        encoding="utf-8",
    )

    with pytest.raises(
        Exception,
        match="option_type must be CE or PE",
    ):
        main._load_signal_state()


def test_load_state_rejects_non_positive_entry(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    position = _position()
    position["entry_price"] = 0

    state_file.write_text(
        json.dumps(position),
        encoding="utf-8",
    )

    with pytest.raises(
        Exception,
        match="entry premium must be positive",
    ):
        main._load_signal_state()


def test_main_supports_930_mode():
    parser_source = Path(
        "main.py"
    ).read_text(
        encoding="utf-8"
    )

    assert '"930"' in parser_source
    assert 'args.mode in {' in parser_source