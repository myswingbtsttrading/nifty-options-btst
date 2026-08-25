from datetime import date, datetime

import pytest

from btst_signal_runner import (
    BTSTRunnerConfig,
    MarketSnapshot,
    OptionQuote,
    build_signal_from_quote,
    generate_directional_signal,
    run_3pm_signal,
    select_btst_contract,
)


def _snapshot(
    nifty_price: float = 25020.0,
    ema20: float = 24900.0,
    ema50: float = 24700.0,
    rsi: float = 60.0,
    previous_close: float = 24900.0,
    adx: float = 30.0,
    vwap: float = 24950.0,
) -> MarketSnapshot:
    return MarketSnapshot(
        timestamp=datetime(
            2026,
            8,
            25,
            15,
            0,
        ),
        nifty_price=nifty_price,
        ema20=ema20,
        ema50=ema50,
        rsi=rsi,
        previous_close=previous_close,
        adx=adx,
        vwap=vwap,
    )


def _quote(
    option_type: str = "CE",
    strike: float = 25000,
    price: float = 100.0,
) -> OptionQuote:
    return OptionQuote(
        expiry=date(
            2026,
            8,
            27,
        ),
        strike=strike,
        option_type=option_type,
        price=price,
    )


def test_generate_directional_signal():
    signal = generate_directional_signal(
        _snapshot()
    )

    assert signal.decision == "BUY"
    assert signal.direction == "CE"
    assert signal.confidence >= 65.0


def test_select_btst_contract():
    contract = select_btst_contract(
        snapshot=_snapshot(),
        expiry=date(
            2026,
            8,
            27,
        ),
    )

    assert contract.option_type == "CE"
    assert contract.strike == 25000
    assert contract.expiry == date(
        2026,
        8,
        27,
    )
    assert contract.selection_mode == "ATM"


def test_build_signal_from_quote():
    result = build_signal_from_quote(
        snapshot=_snapshot(),
        option_quote=_quote(),
        config=BTSTRunnerConfig(
            capital=100000.0,
            lot_size=65,
            stop_loss_pct=0.10,
            target_pct=0.20,
            risk_per_trade_pct=0.02,
            max_allocation_pct=0.20,
            minimum_confidence=65.0,
        ),
    )

    assert result.decision == "BUY"
    assert result.option_type == "CE"
    assert result.strike == 25000
    assert result.entry_price == 100.0
    assert result.stop_loss == 90.0
    assert result.target == 120.0
    assert result.lots == 3
    assert result.quantity == 195
    assert result.is_trade is True


def test_run_3pm_signal():
    requested = []

    def loader(contract):
        requested.append(contract)

        return _quote(
            option_type=contract.option_type,
            strike=contract.strike,
        )

    result = run_3pm_signal(
        snapshot=_snapshot(),
        expiry=date(
            2026,
            8,
            27,
        ),
        option_quote_loader=loader,
        config=BTSTRunnerConfig(
            capital=100000.0,
            lot_size=65,
            stop_loss_pct=0.10,
            target_pct=0.20,
            risk_per_trade_pct=0.02,
            max_allocation_pct=0.20,
        ),
    )

    assert result.is_trade is True
    assert result.decision == "BUY"
    assert result.direction == "CE"

    assert len(requested) == 1
    assert requested[0].option_type == "CE"
    assert requested[0].strike == 25000


def test_pe_signal_selects_pe():
    snapshot = _snapshot(
        nifty_price=24700.0,
        ema20=24800.0,
        ema50=24900.0,
        rsi=40.0,
        previous_close=24800.0,
        adx=30.0,
        vwap=24800.0,
    )

    signal = generate_directional_signal(
        snapshot
    )

    assert signal.decision == "BUY"
    assert signal.direction == "PE"

    contract = select_btst_contract(
        snapshot=snapshot,
        expiry=date(
            2026,
            8,
            27,
        ),
    )

    assert contract.option_type == "PE"
    assert contract.strike == 24700


def test_no_trade_does_not_request_option_quote():
    snapshot = _snapshot(
        nifty_price=25000.0,
        ema20=25000.0,
        ema50=25000.0,
        rsi=50.0,
        previous_close=25000.0,
        adx=10.0,
        vwap=25000.0,
    )

    requested = []

    def loader(contract):
        requested.append(contract)
        return _quote()

    result = run_3pm_signal(
        snapshot=snapshot,
        expiry=date(
            2026,
            8,
            27,
        ),
        option_quote_loader=loader,
    )

    assert result.is_trade is False
    assert result.decision in {
        "NO TRADE",
        "WAIT",
    }

    assert requested == []


def test_invalid_snapshot_is_rejected():
    with pytest.raises(ValueError):
        generate_directional_signal(
            _snapshot(
                nifty_price=0.0,
            )
        )


def test_invalid_quote_price_is_rejected():
    with pytest.raises(ValueError):
        run_3pm_signal(
            snapshot=_snapshot(),
            expiry=date(
                2026,
                8,
                27,
            ),
            option_quote_loader=lambda contract: _quote(
                option_type=contract.option_type,
                strike=contract.strike,
                price=0.0,
            ),
        )


def test_mismatched_quote_strike_is_rejected():
    with pytest.raises(ValueError):
        run_3pm_signal(
            snapshot=_snapshot(),
            expiry=date(
                2026,
                8,
                27,
            ),
            option_quote_loader=lambda contract: _quote(
                option_type=contract.option_type,
                strike=contract.strike + 50,
                price=100.0,
            ),
        )


def test_mismatched_quote_type_is_rejected():
    with pytest.raises(ValueError):
        run_3pm_signal(
            snapshot=_snapshot(),
            expiry=date(
                2026,
                8,
                27,
            ),
            option_quote_loader=lambda contract: _quote(
                option_type="PE",
                strike=contract.strike,
                price=100.0,
            ),
        )


def test_mismatched_quote_expiry_is_rejected():
    with pytest.raises(ValueError):
        run_3pm_signal(
            snapshot=_snapshot(),
            expiry=date(
                2026,
                8,
                27,
            ),
            option_quote_loader=lambda contract: OptionQuote(
                expiry=date(
                    2026,
                    9,
                    3,
                ),
                strike=contract.strike,
                option_type=contract.option_type,
                price=100.0,
            ),
        )


def test_custom_itm_selection():
    contract = select_btst_contract(
        snapshot=_snapshot(),
        expiry=date(
            2026,
            8,
            27,
        ),
        selection_mode="ITM",
    )

    assert contract.option_type == "CE"
    assert contract.strike == 24950


def test_custom_otm_selection():
    contract = select_btst_contract(
        snapshot=_snapshot(),
        expiry=date(
            2026,
            8,
            27,
        ),
        selection_mode="OTM",
    )

    assert contract.option_type == "CE"
    assert contract.strike == 25050


def test_build_signal_rejects_invalid_option_price():
    with pytest.raises(ValueError):
        build_signal_from_quote(
            snapshot=_snapshot(),
            option_quote=_quote(
                price=0.0,
            ),
        )