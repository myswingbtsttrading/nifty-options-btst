from datetime import date

from option_selector import (
    OptionContract,
    round_to_strike,
    select_atm_contract,
    select_contract,
)


def test_round_to_strike_remains_backward_compatible():
    assert round_to_strike(
        25020,
        50,
    ) == 25000


def test_select_contract_remains_backward_compatible():
    result = select_contract(
        nifty_price=25020,
        expiry=date(
            2026,
            8,
            27,
        ),
        option_type="CE",
    )

    assert result == OptionContract(
        expiry=date(
            2026,
            8,
            27,
        ),
        strike=25000,
        option_type="CE",
    )


def test_select_contract_matches_atm_contract():
    expected = select_atm_contract(
        nifty_price=25020,
        expiry=date(
            2026,
            8,
            27,
        ),
        option_type="PE",
    )

    actual = select_contract(
        nifty_price=25020,
        expiry=date(
            2026,
            8,
            27,
        ),
        option_type="PE",
    )

    assert actual == expected