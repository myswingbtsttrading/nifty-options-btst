from datetime import date

from option_selector import (
    select_contract,
)


EXPIRY = date(
    2026,
    8,
    27,
)


def test_ce_atm():
    contract = select_contract(
        nifty_price=25020,
        expiry=EXPIRY,
        option_type="CE",
        selection_mode="ATM",
    )

    assert contract.strike == 25000


def test_ce_itm():
    contract = select_contract(
        nifty_price=25020,
        expiry=EXPIRY,
        option_type="CE",
        selection_mode="ITM",
    )

    assert contract.strike == 24950


def test_ce_otm():
    contract = select_contract(
        nifty_price=25020,
        expiry=EXPIRY,
        option_type="CE",
        selection_mode="OTM",
    )

    assert contract.strike == 25050


def test_pe_atm():
    contract = select_contract(
        nifty_price=25020,
        expiry=EXPIRY,
        option_type="PE",
        selection_mode="ATM",
    )

    assert contract.strike == 25000


def test_pe_itm():
    contract = select_contract(
        nifty_price=25020,
        expiry=EXPIRY,
        option_type="PE",
        selection_mode="ITM",
    )

    assert contract.strike == 25050


def test_pe_otm():
    contract = select_contract(
        nifty_price=25020,
        expiry=EXPIRY,
        option_type="PE",
        selection_mode="OTM",
    )

    assert contract.strike == 24950