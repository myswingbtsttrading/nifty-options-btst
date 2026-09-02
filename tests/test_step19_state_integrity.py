import json
from pathlib import Path

import pytest

import main


ROOT = Path(__file__).resolve().parents[1]


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


def test_state_file_is_valid_json(tmp_path):
    state_file = tmp_path / "live_btst_signal.json"

    state_file.write_text(
        json.dumps(_position()),
        encoding="utf-8",
    )

    payload = json.loads(
        state_file.read_text(
            encoding="utf-8",
        )
    )

    assert isinstance(payload, dict)
    assert payload["decision"] == "BUY"


def test_state_loader_rejects_missing_required_fields(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    payload = _position()
    del payload["quantity"]

    state_file.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        main._load_signal_state()


def test_state_loader_rejects_non_buy_decision(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    payload = _position()
    payload["decision"] = "SELL"

    state_file.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        main._load_signal_state()


def test_state_loader_rejects_invalid_option_type(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    payload = _position()
    payload["option_type"] = "XX"

    state_file.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        main._load_signal_state()


def test_state_loader_rejects_zero_entry_price(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    payload = _position()
    payload["entry_price"] = 0

    state_file.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        main._load_signal_state()


def test_state_loader_rejects_negative_quantity(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    payload = _position()
    payload["quantity"] = -65

    state_file.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        main._load_signal_state()


def test_state_loader_rejects_zero_lots(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    payload = _position()
    payload["lots"] = 0

    state_file.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        main._load_signal_state()


def test_state_loader_rejects_invalid_expiry(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    payload = _position()
    payload["expiry"] = "not-a-date"

    state_file.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        main._load_signal_state()


def test_exit_record_requires_closed_status():
    position = _position()

    exit_payload = {
        "status": "OPEN",
        "direction": position["direction"],
        "option_type": position["option_type"],
        "strike": position["strike"],
        "expiry": position["expiry"],
        "entry_price": position["entry_price"],
        "quantity": position["quantity"],
        "lots": position["lots"],
    }

    assert not main._exit_record_matches_position(
        position,
        exit_payload,
    )


def test_exit_record_requires_matching_contract():
    position = _position()

    exit_payload = {
        "status": "CLOSED",
        "direction": position["direction"],
        "option_type": "PE",
        "strike": position["strike"],
        "expiry": position["expiry"],
        "entry_price": position["entry_price"],
        "quantity": position["quantity"],
        "lots": position["lots"],
    }

    assert not main._exit_record_matches_position(
        position,
        exit_payload,
    )


def test_exit_record_requires_matching_expiry():
    position = _position()

    exit_payload = {
        "status": "CLOSED",
        "direction": position["direction"],
        "option_type": position["option_type"],
        "strike": position["strike"],
        "expiry": "2026-09-10",
        "entry_price": position["entry_price"],
        "quantity": position["quantity"],
        "lots": position["lots"],
    }

    assert not main._exit_record_matches_position(
        position,
        exit_payload,
    )


def test_exit_record_requires_matching_entry_price():
    position = _position()

    exit_payload = {
        "status": "CLOSED",
        "direction": position["direction"],
        "option_type": position["option_type"],
        "strike": position["strike"],
        "expiry": position["expiry"],
        "entry_price": 101.0,
        "quantity": position["quantity"],
        "lots": position["lots"],
    }

    assert not main._exit_record_matches_position(
        position,
        exit_payload,
    )


def test_exit_record_requires_matching_strike():
    position = _position()

    exit_payload = {
        "status": "CLOSED",
        "direction": position["direction"],
        "option_type": position["option_type"],
        "strike": 25100,
        "expiry": position["expiry"],
        "entry_price": position["entry_price"],
        "quantity": position["quantity"],
        "lots": position["lots"],
    }

    assert not main._exit_record_matches_position(
        position,
        exit_payload,
    )


def test_atomic_write_leaves_no_temp_file(
    tmp_path,
):
    path = tmp_path / "state.json"

    main._atomic_write_json(
        path,
        _position(),
    )

    assert path.exists()

    temp_path = path.with_name(
        f".{path.name}.tmp"
    )

    assert not temp_path.exists()

    payload = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    assert payload["decision"] == "BUY"


def test_atomic_write_replaces_existing_file(
    tmp_path,
):
    path = tmp_path / "state.json"

    main._atomic_write_json(
        path,
        {"version": 1},
    )

    main._atomic_write_json(
        path,
        {"version": 2},
    )

    payload = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    assert payload == {"version": 2}


def test_remove_active_state_is_safe_when_missing(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    assert not state_file.exists()

    main._remove_active_state()

    assert not state_file.exists()


def test_remove_active_state_deletes_only_active_state(
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

    exit_file.write_text(
        json.dumps(
            {
                "status": "CLOSED",
            }
        ),
        encoding="utf-8",
    )

    main._remove_active_state()

    assert not state_file.exists()
    assert exit_file.exists()


def test_pnl_calculation_profit():
    pnl, pnl_pct = main._calculate_pnl(
        100.0,
        120.0,
        65,
    )

    assert pnl == 1300.0
    assert pnl_pct == 20.0


def test_pnl_calculation_loss():
    pnl, pnl_pct = main._calculate_pnl(
        100.0,
        80.0,
        65,
    )

    assert pnl == -1300.0
    assert pnl_pct == -20.0


def test_pnl_calculation_breakeven():
    pnl, pnl_pct = main._calculate_pnl(
        100.0,
        100.0,
        65,
    )

    assert pnl == 0.0
    assert pnl_pct == 0.0