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
    assert signal.bullish_score > signal.bearish_score
    assert signal.is_trade is True


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
    assert signal.bearish_score > signal.bullish_score
    assert signal.is_trade is True


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
    assert signal.is_trade is False


def test_balanced_signal_is_no_trade():
    signal = generate_signal(
        nifty_price=25000,
        ema20=24900,
        ema50=24800,
        rsi=50,
        previous_close=25000,
    )

    assert signal.decision == "NO TRADE"
    assert signal.direction == "NONE"


def test_bullish_signal_with_adx_and_vwap():
    signal = generate_signal(
        nifty_price=25000,
        ema20=24800,
        ema50=24500,
        rsi=60,
        previous_close=24900,
        adx=30,
        vwap=24900,
    )

    assert signal.decision == "BUY"
    assert signal.direction == "CE"
    assert signal.regime == "TRENDING"
    assert signal.bullish_score > signal.bearish_score
    assert signal.confidence >= 65


def test_bearish_signal_with_adx_and_vwap():
    signal = generate_signal(
        nifty_price=24000,
        ema20=24200,
        ema50=24500,
        rsi=40,
        previous_close=24100,
        adx=30,
        vwap=24100,
    )

    assert signal.decision == "BUY"
    assert signal.direction == "PE"
    assert signal.regime == "TRENDING"
    assert signal.bearish_score > signal.bullish_score


def test_low_adx_is_ranging():
    signal = generate_signal(
        nifty_price=25000,
        ema20=24800,
        ema50=24500,
        rsi=60,
        previous_close=24900,
        adx=18,
    )

    assert signal.regime == "RANGING"


def test_invalid_price():
    with pytest.raises(ValueError):
        generate_signal(
            nifty_price=0,
            ema20=24000,
            ema50=23500,
            rsi=60,
            previous_close=23900,
        )


def test_invalid_ema20():
    with pytest.raises(ValueError):
        generate_signal(
            nifty_price=25000,
            ema20=0,
            ema50=24500,
            rsi=60,
            previous_close=24900,
        )


def test_invalid_ema50():
    with pytest.raises(ValueError):
        generate_signal(
            nifty_price=25000,
            ema20=24800,
            ema50=0,
            rsi=60,
            previous_close=24900,
        )


def test_invalid_previous_close():
    with pytest.raises(ValueError):
        generate_signal(
            nifty_price=25000,
            ema20=24800,
            ema50=24500,
            rsi=60,
            previous_close=0,
        )


def test_invalid_rsi_high():
    with pytest.raises(ValueError):
        generate_signal(
            nifty_price=25000,
            ema20=24800,
            ema50=24500,
            rsi=101,
            previous_close=24900,
        )


def test_invalid_rsi_low():
    with pytest.raises(ValueError):
        generate_signal(
            nifty_price=25000,
            ema20=24800,
            ema50=24500,
            rsi=-1,
            previous_close=24900,
        )


def test_invalid_adx():
    with pytest.raises(ValueError):
        generate_signal(
            nifty_price=25000,
            ema20=24800,
            ema50=24500,
            rsi=60,
            previous_close=24900,
            adx=-1,
        )


def test_invalid_vwap():
    with pytest.raises(ValueError):
        generate_signal(
            nifty_price=25000,
            ema20=24800,
            ema50=24500,
            rsi=60,
            previous_close=24900,
            vwap=0,
        )