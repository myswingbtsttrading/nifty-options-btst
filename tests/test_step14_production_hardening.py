import json
from datetime import datetime
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


def _write_state(state_file):
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


class FakeChain:
    pass


def test_state_write_is_compact_and_valid(
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

    raw = state_file.read_text(
        encoding="utf-8"
    )

    assert "\n" not in raw
    assert raw.startswith("{")
    assert json.loads(raw)["decision"] == "BUY"


def test_state_write_is_atomic_on_success(
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

    temporary = state_file.with_name(
        f".{state_file.name}.tmp"
    )

    assert not temporary.exists()


def test_3pm_refuses_duplicate_active_position(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    _write_state(state_file)

    monkeypatch.setattr(
        main,
        "_load_historical_nifty_rows",
        lambda: [],
    )

    class FakeSignal:
        decision = "BUY"

    class FakeResult:
        signal = FakeSignal()

    monkeypatch.setattr(
        main,
        "build_live_signal",
        lambda **kwargs: FakeResult(),
    )

    with pytest.raises(
        main.LiveMarketDataError,
        match="already exists",
    ):
        main.run_3pm()


def test_3pm_rolls_back_state_when_telegram_fails(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    class FakeSignal:
        decision = "BUY"
        direction = "CE"
        expiry = "2026-09-03"
        strike = 25000.0
        option_type = "CE"
        nifty_price = 25020.0
        entry_price = 100.0
        stop_loss = 85.0
        target = 130.0
        lots = 1
        quantity = 65
        capital_required = 6500.0
        planned_risk = 975.0
        risk_reward_ratio = 2.0
        confidence = 75.0

        def to_dict(self):
            return _position()

    class FakeIndicators:
        ema20 = 24900.0
        ema50 = 24750.0
        rsi = 62.0

    class FakeNiftySignal:
        reason = "Test."

    class FakeResult:
        signal = FakeSignal()
        indicators = FakeIndicators()
        nifty_signal = FakeNiftySignal()

    monkeypatch.setattr(
        main,
        "_load_historical_nifty_rows",
        lambda: [{"close": 25000.0}]
        * 60,
    )

    monkeypatch.setattr(
        main,
        "build_live_signal",
        lambda **kwargs: FakeResult(),
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
        main.run_3pm()

    assert not state_file.exists()


def test_930_persists_exit_before_removing_state(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    _write_state(state_file)

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
    assert not state_file.exists()
    assert exit_file.exists()

    payload = json.loads(
        exit_file.read_text(
            encoding="utf-8"
        )
    )

    assert payload["status"] == "CLOSED"
    assert payload["strike"] == 25000.0
    assert payload["option_type"] == "CE"
    assert payload["entry_price"] == 100.0
    assert payload["exit_price"] == 120.0
    assert payload["quantity"] == 65
    assert payload["lots"] == 1
    assert payload["pnl"] == 1300.0
    assert payload["pnl_pct"] == 20.0


def test_930_does_not_remove_state_when_exit_persistence_fails(
    monkeypatch,
    tmp_path,
):
    state_file, _ = _configure_state(
        monkeypatch,
        tmp_path,
    )

    _write_state(state_file)

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

    def fail_save(*args, **kwargs):
        raise OSError(
            "disk write failed"
        )

    monkeypatch.setattr(
        main,
        "_save_exit_record",
        fail_save,
    )

    calls = []

    monkeypatch.setattr(
        main,
        "send_alert",
        lambda message: calls.append(message),
    )

    with pytest.raises(
        OSError,
        match="disk write failed",
    ):
        main.run_930()

    assert calls == []
    assert state_file.exists()


def test_930_keeps_state_when_telegram_fails(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    _write_state(state_file)

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

    payload = json.loads(
        exit_file.read_text(
            encoding="utf-8"
        )
    )

    assert payload["status"] == "CLOSED"


def test_930_is_idempotent_after_completed_exit(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    _write_state(state_file)

    main._save_exit_record(
        position=_position(),
        exit_price=120.0,
        exit_timestamp=FakeOptionQuote.timestamp,
    )

    calls = []
    chain_calls = []

    monkeypatch.setattr(
        main,
        "fetch_nifty_option_chain",
        lambda: chain_calls.append(True),
    )

    monkeypatch.setattr(
        main,
        "send_alert",
        lambda message: calls.append(message),
    )

    main.run_930()

    assert calls == []
    assert chain_calls == []
    assert not state_file.exists()
    assert exit_file.exists()


def test_930_does_not_treat_different_exit_record_as_same_position(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    _write_state(state_file)

    different_position = _position()
    different_position["strike"] = 25100.0

    main._save_exit_record(
        position=different_position,
        exit_price=120.0,
        exit_timestamp=FakeOptionQuote.timestamp,
    )

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
    assert not state_file.exists()


def test_invalid_exit_premium_keeps_state(
    monkeypatch,
    tmp_path,
):
    state_file, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    _write_state(state_file)

    class InvalidQuote:
        price = 0.0
        timestamp = FakeOptionQuote.timestamp

    monkeypatch.setattr(
        main,
        "fetch_nifty_option_chain",
        lambda: FakeChain(),
    )

    monkeypatch.setattr(
        main,
        "find_option_quote",
        lambda **kwargs: InvalidQuote(),
    )

    calls = []

    monkeypatch.setattr(
        main,
        "send_alert",
        lambda message: calls.append(message),
    )

    with pytest.raises(
        main.LiveMarketDataError,
        match="positive",
    ):
        main.run_930()

    assert calls == []
    assert state_file.exists()
    assert not exit_file.exists()


def test_exit_record_contains_audit_timestamp(
    monkeypatch,
    tmp_path,
):
    _, exit_file = _configure_state(
        monkeypatch,
        tmp_path,
    )

    main._save_exit_record(
        position=_position(),
        exit_price=120.0,
        exit_timestamp=FakeOptionQuote.timestamp,
    )

    payload = json.loads(
        exit_file.read_text(
            encoding="utf-8"
        )
    )

    assert payload["status"] == "CLOSED"
    assert payload["closed_at"]

    datetime.fromisoformat(
        payload["closed_at"]
    )


def test_production_workflow_contains_expected_modes():
    workflow_3pm = Path(
        ".github/workflows/btst_3pm.yml"
    ).read_text(
        encoding="utf-8"
    )

    workflow_930 = Path(
        ".github/workflows/btst_915.yml"
    ).read_text(
        encoding="utf-8"
    )

    assert "python main.py --mode 3pm" in workflow_3pm
    assert "python main.py --mode 930" in workflow_930
    assert 'cron: "30 9 * * 1-5"' in workflow_3pm
    assert 'cron: "0 4 * * 1-5"' in workflow_930
    assert "TELEGRAM_TOKEN" in workflow_3pm
    assert "TELEGRAM_CHAT_ID" in workflow_3pm
    assert "TELEGRAM_TOKEN" in workflow_930
    assert "TELEGRAM_CHAT_ID" in workflow_930