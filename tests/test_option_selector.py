from datetime import date

import pytest

from option_selector import (
    OptionContract,
    round_to_strike,
    select_atm_contract,
    select_contract,
    select_itm_contract,
    select_otm_contract,
)


EXPIRY = date(2026, 8, 27)


def test_rounds_to_nearest_50():
    assert round_to_strike(25023) == 25000
    assert round_to_strike(25026) == 25050


def test_atm_call():
    contract = select_atm_contract(
        nifty_price=25023,
        expiry=EXPIRY,
        option_type="CE",
    )

    assert contract.strike == 25000
    assert contract.option_type == "CE"
    assert contract.expiry == EXPIRY
    assert contract.selection_mode == "ATM"


def test_atm_put():
    contract = select_atm_contract(
        nifty_price=25026,
        expiry=EXPIRY,
        option_type="PE",
    )

    assert contract.strike == 25050
    assert contract.option_type == "PE"
    assert contract.selection_mode == "ATM"


def test_one_step_itm_call():
    contract = select_itm_contract(
        nifty_price=25023,
        expiry=EXPIRY,
        option_type="CE",
    )

    assert contract.strike == 24950
    assert contract.option_type == "CE"
    assert contract.selection_mode == "ITM"


def test_one_step_itm_put():
    contract = select_itm_contract(
        nifty_price=25023,
        expiry=EXPIRY,
        option_type="PE",
    )

    assert contract.strike == 25050
    assert contract.option_type == "PE"
    assert contract.selection_mode == "ITM"


def test_one_step_otm_call():
    contract = select_otm_contract(
        nifty_price=25023,
        expiry=EXPIRY,
        option_type="CE",
    )

    assert contract.strike == 25050
    assert contract.option_type == "CE"
    assert contract.selection_mode == "OTM"


def test_one_step_otm_put():
    contract = select_otm_contract(
        nifty_price=25023,
        expiry=EXPIRY,
        option_type="PE",
    )

    assert contract.strike == 24950
    assert contract.option_type == "PE"
    assert contract.selection_mode == "OTM"


def test_generic_atm_selection():
    contract = select_contract(
        nifty_price=25023,
        expiry=EXPIRY,
        option_type="CE",
        selection_mode="ATM",
    )

    assert isinstance(contract, OptionContract)
    assert contract.strike == 25000


def test_generic_itm_selection():
    contract = select_contract(
        nifty_price=25023,
        expiry=EXPIRY,
        option_type="CE",
        selection_mode="ITM",
    )

    assert contract.strike == 24950


def test_generic_otm_selection():
    contract = select_contract(
        nifty_price=25023,
        expiry=EXPIRY,
        option_type="CE",
        selection_mode="OTM",
    )

    assert contract.strike == 25050


def test_selection_is_case_insensitive():
    contract = select_contract(
        nifty_price=25023,
        expiry=EXPIRY,
        option_type="ce",
        selection_mode="itm",
    )

    assert contract.option_type == "CE"
    assert contract.selection_mode == "ITM"
    assert contract.strike == 24950


def test_contract_symbol_suffix():
    contract = select_itm_contract(
        nifty_price=25023,
        expiry=EXPIRY,
        option_type="CE",
    )

    assert contract.symbol_suffix == "24950CE"


def test_invalid_option_type():
    with pytest.raises(ValueError):
        select_contract(
            nifty_price=25000,
            expiry=EXPIRY,
            option_type="XX",
        )


def test_invalid_selection_mode():
    with pytest.raises(ValueError):
        select_contract(
            nifty_price=25000,
            expiry=EXPIRY,
            option_type="CE",
            selection_mode="INVALID",
        )


def test_invalid_price():
    with pytest.raises(ValueError):
        round_to_strike(0)


def test_negative_price():
    with pytest.raises(ValueError):
        round_to_strike(-100)


def test_invalid_expiry():
    with pytest.raises(ValueError):
        select_contract(
            nifty_price=25000,
            expiry="2026-08-27",
            option_type="CE",
        )


def test_zero_strike_interval_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "option_selector.STRIKE_INTERVAL",
        0,
    )

    with pytest.raises(ValueError):
        round_to_strike(25000)