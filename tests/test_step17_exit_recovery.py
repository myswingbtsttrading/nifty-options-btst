import json
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


class FakeOptionQuote:
    price = 120.0
    timestamp = datetime(
        2026,
        8,
        28,
        9,
        30,
    )


def _configure_successful_exit(monkeypatch):
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
        lambda message: None,
    )


def test_930_persists_complete_exit_record_before_cleanup(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    state_file.write_text(
        json.dumps(_position()),
        encoding="utf-8",
    )

    _configure_successful_exit(monkeypatch)

    main.run_930()

    assert not state_file.exists()
    assert exit_file.exists()

    payload = json.loads(
        exit_file.read_text(
            encoding="utf-8",
        )
    )

    assert payload["status"] == "CLOSED"
    assert payload["direction"] == "BULLISH"
    assert payload["option_type"] == "CE"
    assert payload["strike"] == 25000
    assert payload["expiry"] == "2026-09-03"
    assert payload["entry_price"] == 100.0
    assert payload["exit_price"] == 120.0
    assert payload["quantity"] == 65
    assert payload["lots"] == 1
    assert payload["pnl"] == 1300.0
    assert payload["pnl_pct"] == 20.0


def test_930_telegram_failure_keeps_both_records(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    state_file.write_text(
        json.dumps(_position()),
        encoding="utf-8",
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
    assert exit_file.exists()

    exit_payload = json.loads(
        exit_file.read_text(
            encoding="utf-8",
        )
    )

    assert exit_payload["status"] == "CLOSED"
    assert exit_payload["exit_price"] == 120.0
    assert exit_payload["pnl"] == 1300.0


def test_930_matching_completed_exit_is_idempotent(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    position = _position()

    state_file.write_text(
        json.dumps(position),
        encoding="utf-8",
    )

    exit_payload = {
        "status": "CLOSED",
        "closed_at": "2026-08-28T09:30:00+00:00",
        "entry_timestamp": position["timestamp"],
        "exit_timestamp": "2026-08-28T09:30:00",
        "direction": position["direction"],
        "option_type": position["option_type"],
        "strike": position["strike"],
        "expiry": position["expiry"],
        "entry_price": position["entry_price"],
        "exit_price": 120.0,
        "quantity": position["quantity"],
        "lots": position["lots"],
        "pnl": 1300.0,
        "pnl_pct": 20.0,
    }

    exit_file.write_text(
        json.dumps(exit_payload),
        encoding="utf-8",
    )

    chain_called = False
    alert_called = False

    def unexpected_chain():
        nonlocal chain_called
        chain_called = True
        raise AssertionError(
            "Option chain must not be fetched for an already completed exit"
        )

    def unexpected_alert(message):
        nonlocal alert_called
        alert_called = True
        raise AssertionError(
            "Telegram must not be sent for an already completed exit"
        )

    monkeypatch.setattr(
        main,
        "fetch_nifty_option_chain",
        unexpected_chain,
    )

    monkeypatch.setattr(
        main,
        "send_alert",
        unexpected_alert,
    )

    main.run_930()

    assert not state_file.exists()
    assert exit_file.exists()
    assert chain_called is False
    assert alert_called is False


def test_930_does_not_treat_different_exit_as_completed(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    position = _position()

    state_file.write_text(
        json.dumps(position),
        encoding="utf-8",
    )

    different_exit = {
        "status": "CLOSED",
        "closed_at": "2026-08-28T09:30:00+00:00",
        "entry_timestamp": position["timestamp"],
        "exit_timestamp": "2026-08-28T09:30:00",
        "direction": position["direction"],
        "option_type": position["option_type"],
        "strike": 25100,
        "expiry": position["expiry"],
        "entry_price": position["entry_price"],
        "exit_price": 120.0,
        "quantity": position["quantity"],
        "lots": position["lots"],
        "pnl": 1300.0,
        "pnl_pct": 20.0,
    }

    exit_file.write_text(
        json.dumps(different_exit),
        encoding="utf-8",
    )

    _configure_successful_exit(monkeypatch)

    main.run_930()

    assert not state_file.exists()

    payload = json.loads(
        exit_file.read_text(
            encoding="utf-8",
        )
    )

    assert payload["strike"] == 25000
    assert payload["exit_price"] == 120.0


def test_930_invalid_exit_price_keeps_active_state(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    state_file.write_text(
        json.dumps(_position()),
        encoding="utf-8",
    )

    class InvalidQuote:
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
        lambda **kwargs: InvalidQuote(),
    )

    alert_called = False

    def unexpected_alert(message):
        nonlocal alert_called
        alert_called = True

    monkeypatch.setattr(
        main,
        "send_alert",
        unexpected_alert,
    )

    with pytest.raises(Exception):
        main.run_930()

    assert state_file.exists()
    assert not exit_file.exists()
    assert alert_called is False


def test_930_missing_state_does_not_create_exit_record(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    assert not state_file.exists()

    with pytest.raises(Exception):
        main.run_930()

    assert not state_file.exists()
    assert not exit_file.exists()


def test_exit_record_matching_is_case_insensitive():
    position = _position()

    exit_payload = {
        "status": "CLOSED",
        "direction": "bullish",
        "option_type": "ce",
        "strike": 25000.0,
        "expiry": "2026-09-03",
        "entry_price": 100.0,
        "quantity": 65.0,
        "lots": 1.0,
    }

    assert main._exit_record_matches_position(
        position,
        exit_payload,
    )


def test_exit_record_mismatch_in_quantity_is_not_idempotent():
    position = _position()

    exit_payload = {
        "status": "CLOSED",
        "direction": "BULLISH",
        "option_type": "CE",
        "strike": 25000,
        "expiry": "2026-09-03",
        "entry_price": 100.0,
        "quantity": 130,
        "lots": 2,
    }

    assert not main._exit_record_matches_position(
        position,
        exit_payload,
    )