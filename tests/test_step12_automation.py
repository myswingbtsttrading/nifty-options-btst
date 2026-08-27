from datetime import date

import main


class FakeSignal:
    decision = "BUY"
    direction = "CE"
    expiry = date(2026, 8, 27)
    strike = 25000.0
    option_type = "CE"
    nifty_price = 25020.0
    entry_price = 125.0
    stop_loss = 106.25
    target = 162.50
    lots = 1
    quantity = 65
    capital_required = 8125.0
    planned_risk = 1218.75
    risk_reward_ratio = 2.0
    confidence = 75.0

    def to_json(self):
        return '{"decision":"BUY"}'


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


def test_run_3pm_sends_telegram_for_buy(
    monkeypatch,
    tmp_path,
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
        "send_alert",
        lambda message: calls.append(message),
    )

    monkeypatch.setattr(
        main,
        "DATA_DIR",
        tmp_path,
    )

    monkeypatch.setattr(
        main,
        "STATE_FILE",
        tmp_path / "live_btst_signal.json",
    )

    main.run_3pm()

    assert len(calls) == 1
    assert "NIFTY BTST BUY ALERT" in calls[0]
    assert "BUY CE" in calls[0]
    assert "₹25,020.00" in calls[0]

    state_file = (
        tmp_path
        / "live_btst_signal.json"
    )

    assert state_file.exists()
    assert state_file.read_text(
        encoding="utf-8"
    ) == '{"decision":"BUY"}'


def test_run_3pm_does_not_send_telegram_for_no_trade(
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

    assert calls == []


def test_historical_loader_requires_at_least_50_rows(
    monkeypatch,
):
    monkeypatch.setattr(
        main,
        "load_nifty_history",
        lambda days: [
            {
                "timestamp": index,
                "close": 25000.0,
            }
            for index in range(49)
        ],
    )

    try:
        main._load_historical_nifty_rows()
    except Exception as exc:
        assert "Fewer than 50" in str(exc)
    else:
        raise AssertionError(
            "Expected historical-data validation to fail."
        )