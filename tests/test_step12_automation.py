from pathlib import Path

import main


class FakeSignal:
    decision = "BUY"
    confidence = 80.0
    nifty_price = 25020.0
    direction = "CE"
    expiry = "2026-09-03"
    strike = 25000
    option_type = "CE"
    entry_price = 100.0
    stop_loss = 90.0
    target = 120.0
    lots = 1
    quantity = 65
    capital_required = 6500.0
    planned_risk = 650.0
    risk_reward_ratio = 2.0


class FakeIndicators:
    ema20 = 24900.0
    ema50 = 24750.0
    rsi = 62.0


class FakeNiftySignal:
    reason = "Strong bullish NIFTY setup."


class FakeResult:
    signal = FakeSignal()
    indicators = FakeIndicators()
    nifty_signal = FakeNiftySignal()


def test_main_file_exists():
    assert Path("main.py").exists()


def test_run_3pm_builds_live_signal(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        main,
        "_load_historical_nifty_rows",
        lambda: [
            {
                "timestamp": index,
                "close": 25000.0,
            }
            for index in range(60)
        ],
    )

    monkeypatch.setattr(
        main,
        "build_live_signal",
        lambda **kwargs: (
            calls.append(kwargs)
            or FakeResult()
        ),
    )

    monkeypatch.setattr(
        main,
        "_save_signal_state",
        lambda signal: None,
    )

    monkeypatch.setattr(
        main,
        "send_alert",
        lambda message: None,
    )

    main.run_3pm()

    assert len(calls) == 1
    assert calls[0]["capital"] == 100000.0
    assert calls[0]["lot_size"] == 65


def test_run_3pm_sends_buy_alert(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        main,
        "_load_historical_nifty_rows",
        lambda: [
            {
                "timestamp": index,
                "close": 25000.0,
            }
            for index in range(60)
        ],
    )

    monkeypatch.setattr(
        main,
        "build_live_signal",
        lambda **kwargs: FakeResult(),
    )

    monkeypatch.setattr(
        main,
        "_save_signal_state",
        lambda signal: None,
    )

    monkeypatch.setattr(
        main,
        "send_alert",
        lambda message: calls.append(message),
    )

    main.run_3pm()

    assert len(calls) == 1
    assert "BUY" in calls[0]


def test_run_3pm_sends_telegram_for_no_trade(
    monkeypatch,
):
    calls = []

    class NoTradeSignal(FakeSignal):
        decision = "WAIT"
        confidence = 45.0

    class NoTradeResult:
        signal = NoTradeSignal()
        indicators = FakeIndicators()
        nifty_signal = FakeNiftySignal()

    monkeypatch.setattr(
        main,
        "_load_historical_nifty_rows",
        lambda: [
            {
                "timestamp": index,
                "close": 25000.0,
            }
            for index in range(60)
        ],
    )

    monkeypatch.setattr(
        main,
        "build_live_signal",
        lambda **kwargs: NoTradeResult(),
    )

    monkeypatch.setattr(
        main,
        "send_alert",
        lambda message: calls.append(message),
    )

    main.run_3pm()

    assert len(calls) == 1
    assert "NO TRADE" in calls[0]
    assert "WAIT" in calls[0]


def test_run_3pm_does_not_create_state_for_no_trade(
    monkeypatch,
):
    save_calls = []

    class NoTradeSignal(FakeSignal):
        decision = "WAIT"
        confidence = 45.0

    class NoTradeResult:
        signal = NoTradeSignal()
        indicators = FakeIndicators()
        nifty_signal = FakeNiftySignal()

    monkeypatch.setattr(
        main,
        "_load_historical_nifty_rows",
        lambda: [
            {
                "timestamp": index,
                "close": 25000.0,
            }
            for index in range(60)
        ],
    )

    monkeypatch.setattr(
        main,
        "build_live_signal",
        lambda **kwargs: NoTradeResult(),
    )

    monkeypatch.setattr(
        main,
        "_save_signal_state",
        lambda signal: save_calls.append(signal),
    )

    monkeypatch.setattr(
        main,
        "send_alert",
        lambda message: None,
    )

    main.run_3pm()

    assert save_calls == []


def test_run_3pm_saves_buy_state(
    monkeypatch,
):
    save_calls = []

    monkeypatch.setattr(
        main,
        "_load_historical_nifty_rows",
        lambda: [
            {
                "timestamp": index,
                "close": 25000.0,
            }
            for index in range(60)
        ],
    )

    monkeypatch.setattr(
        main,
        "build_live_signal",
        lambda **kwargs: FakeResult(),
    )

    monkeypatch.setattr(
        main,
        "_save_signal_state",
        lambda signal: save_calls.append(signal),
    )

    monkeypatch.setattr(
        main,
        "send_alert",
        lambda message: None,
    )

    main.run_3pm()

    assert len(save_calls) == 1
    assert save_calls[0].decision == "BUY"


def test_run_3pm_rejects_duplicate_buy_state(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        main,
        "_load_historical_nifty_rows",
        lambda: [
            {
                "timestamp": index,
                "close": 25000.0,
            }
            for index in range(60)
        ],
    )

    monkeypatch.setattr(
        main,
        "build_live_signal",
        lambda **kwargs: FakeResult(),
    )

    state_file = tmp_path / "live_btst_signal.json"
    state_file.write_text(
        '{"decision":"BUY"}',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        main,
        "STATE_FILE",
        state_file,
    )

    try:
        main.run_3pm()
    except Exception as exc:
        assert "active BTST BUY position" in str(exc)
    else:
        raise AssertionError(
            "Expected duplicate BUY position to be rejected."
        )


def test_run_3pm_rolls_back_state_when_telegram_fails(
    monkeypatch,
):
    remove_calls = []

    monkeypatch.setattr(
        main,
        "_load_historical_nifty_rows",
        lambda: [
            {
                "timestamp": index,
                "close": 25000.0,
            }
            for index in range(60)
        ],
    )

    monkeypatch.setattr(
        main,
        "build_live_signal",
        lambda **kwargs: FakeResult(),
    )

    monkeypatch.setattr(
        main,
        "_save_signal_state",
        lambda signal: None,
    )

    monkeypatch.setattr(
        main,
        "_remove_active_state",
        lambda: remove_calls.append(True),
    )

    def failing_alert(message):
        raise RuntimeError("Telegram failed")

    monkeypatch.setattr(
        main,
        "send_alert",
        failing_alert,
    )

    try:
        main.run_3pm()
    except RuntimeError as exc:
        assert "Telegram failed" in str(exc)
    else:
        raise AssertionError(
            "Expected Telegram failure."
        )

    assert remove_calls == [True]


def test_run_3pm_no_trade_telegram_failure_does_not_remove_state(
    monkeypatch,
):
    remove_calls = []

    class NoTradeSignal(FakeSignal):
        decision = "WAIT"
        confidence = 45.0

    class NoTradeResult:
        signal = NoTradeSignal()
        indicators = FakeIndicators()
        nifty_signal = FakeNiftySignal()

    monkeypatch.setattr(
        main,
        "_load_historical_nifty_rows",
        lambda: [
            {
                "timestamp": index,
                "close": 25000.0,
            }
            for index in range(60)
        ],
    )

    monkeypatch.setattr(
        main,
        "build_live_signal",
        lambda **kwargs: NoTradeResult(),
    )

    monkeypatch.setattr(
        main,
        "_remove_active_state",
        lambda: remove_calls.append(True),
    )

    def failing_alert(message):
        raise RuntimeError("Telegram failed")

    monkeypatch.setattr(
        main,
        "send_alert",
        failing_alert,
    )

    try:
        main.run_3pm()
    except RuntimeError as exc:
        assert "Telegram failed" in str(exc)
    else:
        raise AssertionError(
            "Expected Telegram failure."
        )

    assert remove_calls == []