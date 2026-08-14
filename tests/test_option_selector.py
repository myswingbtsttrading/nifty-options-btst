from datetime import date

import pytest

from option_selector import (
    round_to_strike,
    select_atm_contract,
)


def test_rounds_to_nearest_50():
    assert round_to_strike(25023) == 25000
    assert round_to_strike(25026) == 25050


def test_atm_call():
    contract = select_atm_contract(
        nifty_price=25023,
        expiry=date(2026, 8, 18),
        option_type="CE",
    )

    assert contract.strike == 25000
    assert contract.option_type == "CE"
    assert contract.expiry == date(
        2026,
        8,
        18,
    )


def test_atm_put():
    contract = select_atm_contract(
        nifty_price=25026,
        expiry=date(2026, 8, 18),
        option_type="PE",
    )

    assert contract.strike == 25050
    assert contract.option_type == "PE"


def test_invalid_option_type():
    with pytest.raises(ValueError):
        select_atm_contract(
            nifty_price=25000,
            expiry=date(2026, 8, 18),
            option_type="XX",
        )


def test_invalid_price():
    with pytest.raises(ValueError):
        round_to_strike(0)