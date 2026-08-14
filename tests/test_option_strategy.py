import pytest

from option_strategy import generate_signal


def test_bullish_signal():
    signal = generate_signal(
        nifty_price=25000,
        ema20=24800,
        ema50=24500,
        rsi=60,
        previous_close=24900,
    )

    assert signal.decision == "BUY"
    assert signal.direction == "CE"
    assert signal.confidence >= 65


def test_bearish_signal():
    signal = generate_signal(
        nifty_price=24000,
        ema20=24200,
        ema50=24500,
        rsi=40,
        previous_close=24100,
    )

    assert signal.decision == "BUY"
    assert signal.direction == "PE"
    assert signal.confidence >= 65


def test_weak_signal_is_no_trade():
    signal = generate_signal(
        nifty_price=25000,
        ema20=24950,
        ema50=24800,
        rsi=50,
        previous_close=25000,
    )

    assert signal.decision == "NO TRADE"
    assert signal.direction == "NONE"


def test_invalid_price():
    with pytest.raises(ValueError):
        generate_signal(
            nifty_price=0,
            ema20=24000,
            ema50=23500,
            rsi=60,
            previous_close=23900,
        )


def test_invalid_rsi():
    with pytest.raises(ValueError):
        generate_signal(
            nifty_price=25000,
            ema20=24800,
            ema50=24500,
            rsi=101,
            previous_close=24900,
        )