import pytest

from option_chain_confirmation import (
    OptionChainSnapshot,
    analyze_option_chain,
)
from option_strategy import generate_signal


def bullish_chain() -> OptionChainSnapshot:
    return OptionChainSnapshot(
        ce_oi=100000,
        pe_oi=130000,
        ce_oi_change=10000,
        pe_oi_change=25000,
        ce_volume=50000,
        pe_volume=80000,
    )


def bearish_chain() -> OptionChainSnapshot:
    return OptionChainSnapshot(
        ce_oi=140000,
        pe_oi=100000,
        ce_oi_change=30000,
        pe_oi_change=10000,
        ce_volume=90000,
        pe_volume=50000,
    )


def neutral_chain() -> OptionChainSnapshot:
    return OptionChainSnapshot(
        ce_oi=100000,
        pe_oi=100000,
        ce_oi_change=10000,
        pe_oi_change=10000,
        ce_volume=50000,
        pe_volume=50000,
    )


def test_bullish_signal_without_option_chain():
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
    assert signal.option_chain_confirmed is False


def test_bearish_signal_without_option_chain():
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
    assert signal.option_chain_confirmed is False


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


def test_bullish_option_chain_confirmation():
    confirmation = analyze_option_chain(
        bullish_chain()
    )

    assert confirmation.direction == "CE"
    assert confirmation.confirmed is True
    assert confirmation.score >= 2
    assert confirmation.pcr > 1.0


def test_bearish_option_chain_confirmation():
    confirmation = analyze_option_chain(
        bearish_chain()
    )

    assert confirmation.direction == "PE"
    assert confirmation.confirmed is True
    assert confirmation.score >= 2
    assert confirmation.pcr < 1.0


def test_neutral_option_chain_has_no_confirmation():
    confirmation = analyze_option_chain(
        neutral_chain()
    )

    assert confirmation.direction == "NONE"
    assert confirmation.confirmed is False


def test_bullish_nifty_and_bullish_chain_produce_ce():
    signal = generate_signal(
        nifty_price=25000,
        ema20=24800,
        ema50=24500,
        rsi=60,
        previous_close=24900,
        option_chain=bullish_chain(),
    )

    assert signal.decision == "BUY"
    assert signal.direction == "CE"
    assert signal.option_chain_confirmed is True
    assert signal.option_chain_pcr is not None
    assert signal.option_chain_pcr > 1.0


def test_bearish_nifty_and_bearish_chain_produce_pe():
    signal = generate_signal(
        nifty_price=24000,
        ema20=24200,
        ema50=24500,
        rsi=40,
        previous_close=24100,
        option_chain=bearish_chain(),
    )

    assert signal.decision == "BUY"
    assert signal.direction == "PE"
    assert signal.option_chain_confirmed is True
    assert signal.option_chain_pcr is not None
    assert signal.option_chain_pcr < 1.0


def test_bullish_nifty_bearish_chain_is_rejected():
    signal = generate_signal(
        nifty_price=25000,
        ema20=24800,
        ema50=24500,
        rsi=60,
        previous_close=24900,
        option_chain=bearish_chain(),
    )

    assert signal.decision == "NO TRADE"
    assert signal.direction == "NONE"
    assert signal.option_chain_confirmed is False


def test_bearish_nifty_bullish_chain_is_rejected():
    signal = generate_signal(
        nifty_price=24000,
        ema20=24200,
        ema50=24500,
        rsi=40,
        previous_close=24100,
        option_chain=bullish_chain(),
    )

    assert signal.decision == "NO TRADE"
    assert signal.direction == "NONE"
    assert signal.option_chain_confirmed is False


def test_weak_option_chain_rejects_trade():
    signal = generate_signal(
        nifty_price=25000,
        ema20=24800,
        ema50=24500,
        rsi=60,
        previous_close=24900,
        option_chain=neutral_chain(),
    )

    assert signal.decision == "NO TRADE"
    assert signal.direction == "NONE"
    assert signal.option_chain_confirmed is False


def test_option_chain_requires_positive_ce_oi():
    with pytest.raises(ValueError):
        OptionChainSnapshot(
            ce_oi=0,
            pe_oi=100000,
            ce_oi_change=10000,
            pe_oi_change=20000,
            ce_volume=50000,
            pe_volume=70000,
        )


def test_option_chain_rejects_negative_values():
    with pytest.raises(ValueError):
        OptionChainSnapshot(
            ce_oi=100000,
            pe_oi=-100000,
            ce_oi_change=10000,
            pe_oi_change=20000,
            ce_volume=50000,
            pe_volume=70000,
        )


def test_option_chain_rejects_negative_oi_change():
    with pytest.raises(ValueError):
        OptionChainSnapshot(
            ce_oi=100000,
            pe_oi=100000,
            ce_oi_change=-1,
            pe_oi_change=20000,
            ce_volume=50000,
            pe_volume=70000,
        )


def test_option_chain_rejects_negative_volume():
    with pytest.raises(ValueError):
        OptionChainSnapshot(
            ce_oi=100000,
            pe_oi=100000,
            ce_oi_change=10000,
            pe_oi_change=20000,
            ce_volume=-1,
            pe_volume=70000,
        )


def test_adx_and_vwap_still_work_with_option_chain():
    signal = generate_signal(
        nifty_price=25000,
        ema20=24800,
        ema50=24500,
        rsi=60,
        previous_close=24900,
        adx=30,
        vwap=24900,
        option_chain=bullish_chain(),
    )

    assert signal.decision == "BUY"
    assert signal.direction == "CE"
    assert signal.regime == "TRENDING"
    assert signal.option_chain_confirmed is True