from datetime import datetime
from pathlib import Path

import pytest

import main


def _position():
    return {
        "timestamp": "2026-08-27T15:00:00",
        "decision": "BUY",
        "direction": "BULLISH",
        "expiry": "2026-09-03",
        "strike": 25000,
        "option_type": "CE",
        "entry_price": 100.0,
        "stop_loss": 90.0,
        "target": 120.0,
        "lots": 1,
        "quantity": 65,
        "capital": 100000.0,
    }


def _configure_state(monkeypatch, tmp_path):
    state_file = tmp_path / "live_btst_signal.json"
    exit_file = tmp_path / "last_btst_exit.json"

    monkeypatch.setattr(main, "STATE_FILE", state_file)
    monkeypatch.setattr(main, "EXIT_FILE", exit_file)

    return state_file, exit_file


def test_930_uses_exact_stored_contract(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    position = _position()

    state_file.write_text(
        __import__("json").dumps(position),
        encoding="utf-8",
    )

    captured = {}

    class FakeQuote:
        price = 115.0
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
        lambda: {"chain": True},
    )

    def fake_find_option_quote(**kwargs):
        captured.update(kwargs)
        return FakeQuote()

    monkeypatch.setattr(
        main,
        "find_option_quote",
        fake_find_option_quote,
    )

    monkeypatch.setattr(
        main,
        "send_alert",
        lambda message: None,
    )

    main.run_930()

    assert captured["expiry"].isoformat() == "2026-09-03"
    assert captured["strike"] == 25000.0
    assert captured["option_type"] == "CE"


def test_930_does_not_change_stored_position_before_exit(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    position = _position()

    state_file.write_text(
        __import__("json").dumps(position),
        encoding="utf-8",
    )

    class FakeQuote:
        price = 115.0
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
        lambda: {"chain": True},
    )

    monkeypatch.setattr(
        main,
        "find_option_quote",
        lambda **kwargs: FakeQuote(),
    )

    monkeypatch.setattr(
        main,
        "send_alert",
        lambda message: None,
    )

    main.run_930()

    assert not state_file.exists()
    assert exit_file.exists()

    exit_payload = __import__("json").loads(
        exit_file.read_text(
            encoding="utf-8",
        )
    )

    assert exit_payload["strike"] == 25000.0
    assert exit_payload["option_type"] == "CE"
    assert exit_payload["expiry"] == "2026-09-03"
    assert exit_payload["entry_price"] == 100.0
    assert exit_payload["exit_price"] == 115.0
    assert exit_payload["quantity"] == 65
    assert exit_payload["lots"] == 1


def test_930_rejects_missing_option_quote(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    state_file.write_text(
        __import__("json").dumps(_position()),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        main,
        "fetch_nifty_option_chain",
        lambda: {"chain": True},
    )

    monkeypatch.setattr(
        main,
        "find_option_quote",
        lambda **kwargs: None,
    )

    alert_called = False

    def fake_alert(message):
        nonlocal alert_called
        alert_called = True

    monkeypatch.setattr(
        main,
        "send_alert",
        fake_alert,
    )

    with pytest.raises(Exception):
        main.run_930()

    assert state_file.exists()
    assert not exit_file.exists()
    assert alert_called is False


def test_930_rejects_invalid_option_quote_object(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    state_file.write_text(
        __import__("json").dumps(_position()),
        encoding="utf-8",
    )

    class BrokenQuote:
        price = None
        timestamp = None

    monkeypatch.setattr(
        main,
        "fetch_nifty_option_chain",
        lambda: {"chain": True},
    )

    monkeypatch.setattr(
        main,
        "find_option_quote",
        lambda **kwargs: BrokenQuote(),
    )

    monkeypatch.setattr(
        main,
        "send_alert",
        lambda message: None,
    )

    with pytest.raises(Exception):
        main.run_930()

    assert state_file.exists()
    assert not exit_file.exists()


def test_930_does_not_send_alert_when_quote_lookup_fails(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    state_file.write_text(
        __import__("json").dumps(_position()),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        main,
        "fetch_nifty_option_chain",
        lambda: {"chain": True},
    )

    def fail_lookup(**kwargs):
        raise RuntimeError(
            "Exact contract not found"
        )

    monkeypatch.setattr(
        main,
        "find_option_quote",
        fail_lookup,
    )

    alert_called = False

    def fake_alert(message):
        nonlocal alert_called
        alert_called = True

    monkeypatch.setattr(
        main,
        "send_alert",
        fake_alert,
    )

    with pytest.raises(
        RuntimeError,
        match="Exact contract not found",
    ):
        main.run_930()

    assert state_file.exists()
    assert not exit_file.exists()
    assert alert_called is False


def test_930_rejects_invalid_expiry_before_quote_lookup(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    position = _position()
    position["expiry"] = "invalid"

    state_file.write_text(
        __import__("json").dumps(position),
        encoding="utf-8",
    )

    lookup_called = False

    monkeypatch.setattr(
        main,
        "fetch_nifty_option_chain",
        lambda: {"chain": True},
    )

    def fake_lookup(**kwargs):
        nonlocal lookup_called
        lookup_called = True
        return None

    monkeypatch.setattr(
        main,
        "find_option_quote",
        fake_lookup,
    )

    with pytest.raises(Exception):
        main.run_930()

    assert lookup_called is False
    assert state_file.exists()
    assert not exit_file.exists()


def test_930_rejects_invalid_option_type_before_quote_lookup(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    position = _position()
    position["option_type"] = "XX"

    state_file.write_text(
        __import__("json").dumps(position),
        encoding="utf-8",
    )

    lookup_called = False

    monkeypatch.setattr(
        main,
        "fetch_nifty_option_chain",
        lambda: {"chain": True},
    )

    def fake_lookup(**kwargs):
        nonlocal lookup_called
        lookup_called = True
        return None

    monkeypatch.setattr(
        main,
        "find_option_quote",
        fake_lookup,
    )

    with pytest.raises(Exception):
        main.run_930()

    assert lookup_called is False
    assert state_file.exists()
    assert not exit_file.exists()


def test_930_rejects_zero_strike_before_quote_lookup(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    position = _position()
    position["strike"] = 0

    state_file.write_text(
        __import__("json").dumps(position),
        encoding="utf-8",
    )

    lookup_called = False

    monkeypatch.setattr(
        main,
        "fetch_nifty_option_chain",
        lambda: {"chain": True},
    )

    def fake_lookup(**kwargs):
        nonlocal lookup_called
        lookup_called = True
        return None

    monkeypatch.setattr(
        main,
        "find_option_quote",
        fake_lookup,
    )

    with pytest.raises(Exception):
        main.run_930()

    assert lookup_called is False
    assert state_file.exists()
    assert not exit_file.exists()


def test_930_success_removes_active_state_only_after_alert(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    state_file.write_text(
        __import__("json").dumps(_position()),
        encoding="utf-8",
    )

    class FakeQuote:
        price = 110.0
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
        lambda: {"chain": True},
    )

    monkeypatch.setattr(
        main,
        "find_option_quote",
        lambda **kwargs: FakeQuote(),
    )

    observed = {}

    def fake_alert(message):
        observed["state_exists"] = state_file.exists()
        observed["exit_exists"] = exit_file.exists()

    monkeypatch.setattr(
        main,
        "send_alert",
        fake_alert,
    )

    main.run_930()

    assert observed["state_exists"] is True
    assert observed["exit_exists"] is True

    assert not state_file.exists()
    assert exit_file.exists()