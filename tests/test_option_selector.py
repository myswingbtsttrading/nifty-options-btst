from datetime import date

import pytest

from option_selector import (
    OptionSelectionError,
    select_atm_contract,
    select_atm_strike,
    select_live_contract,
)


EXPIRY = date(
    2026,
    8,
    27,
)


def _payload():
    return {
        "records": {
            "data": [
                {
                    "strikePrice": 25000,
                    "expiryDate": "27-Aug-2026",
                    "CE": {
                        "lastPrice": 105,
                    },
                    "PE": {
                        "lastPrice": 95,
                    },
                },
                {
                    "strikePrice": 25050,
                    "expiryDate": "27-Aug-2026",
                    "CE": {
                        "lastPrice": 85,
                    },
                    "PE": {
                        "lastPrice": 125,
                    },
                },
                {
                    "strikePrice": 24950,
                    "expiryDate": "27-Aug-2026",
                    "CE": {
                        "lastPrice": 120,
                    },
                    "PE": {
                        "lastPrice": 80,
                    },
                },
            ],
        }
    }


def test_select_atm_strike():
    assert select_atm_strike(
        25020,
        50,
    ) == 25000


def test_select_atm_strike_rounds_up():
    assert select_atm_strike(
        25030,
        50,
    ) == 25050


def test_select_atm_strike_rejects_invalid_price():
    with pytest.raises(
        OptionSelectionError,
        match="positive",
    ):
        select_atm_strike(
            0,
            50,
        )


def test_select_atm_contract_ce():
    result = select_atm_contract(
        nifty_price=25020,
        expiry=EXPIRY,
        option_type="CE",
    )

    assert result.expiry == EXPIRY
    assert result.strike == 25000
    assert result.option_type == "CE"


def test_select_atm_contract_pe():
    result = select_atm_contract(
        nifty_price=25020,
        expiry=EXPIRY,
        option_type="PE",
    )

    assert result.strike == 25000
    assert result.option_type == "PE"


def test_select_atm_contract_rejects_invalid_type():
    with pytest.raises(
        OptionSelectionError,
        match="CE or PE",
    ):
        select_atm_contract(
            nifty_price=25020,
            expiry=EXPIRY,
            option_type="XX",
        )


def test_select_live_contract_ce():
    result = select_live_contract(
        option_chain_payload=_payload(),
        nifty_price=25020,
        expiry=EXPIRY,
        option_type="CE",
    )

    assert result.strike == 25000
    assert result.option_type == "CE"
    assert result.expiry == EXPIRY


def test_select_live_contract_pe():
    result = select_live_contract(
        option_chain_payload=_payload(),
        nifty_price=25020,
        expiry=EXPIRY,
        option_type="PE",
    )

    assert result.strike == 25000
    assert result.option_type == "PE"


def test_select_live_contract_requires_real_contract():
    payload = {
        "records": {
            "data": [
                {
                    "strikePrice": 25000,
                    "expiryDate": "27-Aug-2026",
                    "CE": {
                        "lastPrice": 0,
                    },
                }
            ]
        }
    }

    with pytest.raises(
        OptionSelectionError,
        match="not available",
    ):
        select_live_contract(
            option_chain_payload=payload,
            nifty_price=25020,
            expiry=EXPIRY,
            option_type="CE",
        )


def test_select_live_contract_requires_matching_expiry():
    with pytest.raises(
        OptionSelectionError,
        match="not available",
    ):
        select_live_contract(
            option_chain_payload=_payload(),
            nifty_price=25020,
            expiry=date(
                2026,
                9,
                3,
            ),
            option_type="CE",
        )