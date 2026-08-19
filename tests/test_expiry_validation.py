from datetime import date, datetime

import pytest

from expiry_validation import (
    extract_contract_expiries,
    expiry_is_usable_for_overnight_trade,
    validate_contract_expiry,
    validate_expected_expiry,
    validate_trade_contract,
)


def test_extract_date_expiries():

    rows = [
        {
            "expiry": date(
                2017,
                1,
                26,
            )
        },
        {
            "expiry": datetime(
                2017,
                2,
                23,
                0,
                0,
            )
        },
        {
            "expiry": "2017-03-30"
        },
    ]

    result = extract_contract_expiries(
        rows
    )

    assert result == {
        date(2017, 1, 26),
        date(2017, 2, 23),
        date(2017, 3, 30),
    }


def test_extract_ignores_invalid_expiry():

    rows = [
        {
            "expiry": "not-a-date"
        },
        {
            "expiry": None
        },
    ]

    result = extract_contract_expiries(
        rows
    )

    assert result == set()


def test_expected_expiry_exists():

    result = validate_expected_expiry(
        date(
            2017,
            1,
            20,
        ),
        {
            date(
                2017,
                1,
                26,
            )
        },
    )

    assert result == date(
        2017,
        1,
        26,
    )


def test_expected_expiry_missing():

    with pytest.raises(
        ValueError,
        match="not present",
    ):
        validate_expected_expiry(
            date(
                2017,
                1,
                20,
            ),
            {
                date(
                    2017,
                    2,
                    23,
                )
            },
        )


def test_valid_contract_expiry():

    assert validate_contract_expiry(
        date(
            2017,
            1,
            20,
        ),
        date(
            2017,
            1,
            26,
        ),
    )


def test_expired_contract_is_invalid():

    assert not validate_contract_expiry(
        date(
            2017,
            1,
            27,
        ),
        date(
            2017,
            1,
            26,
        ),
    )


def test_valid_ce_contract():

    validate_trade_contract(
        date(
            2017,
            1,
            20,
        ),
        date(
            2017,
            1,
            26,
        ),
        "CE",
        8250,
    )


def test_valid_pe_contract():

    validate_trade_contract(
        date(
            2017,
            1,
            20,
        ),
        date(
            2017,
            1,
            26,
        ),
        "PE",
        8250,
    )


def test_invalid_option_type():

    with pytest.raises(
        ValueError,
        match="CE or PE",
    ):
        validate_trade_contract(
            date(
                2017,
                1,
                20,
            ),
            date(
                2017,
                1,
                26,
            ),
            "CALL",
            8250,
        )


def test_invalid_strike():

    with pytest.raises(
        ValueError,
        match="positive",
    ):
        validate_trade_contract(
            date(
                2017,
                1,
                20,
            ),
            date(
                2017,
                1,
                26,
            ),
            "CE",
            0,
        )


def test_expiry_before_trade_date_is_rejected():

    with pytest.raises(
        ValueError,
        match="before",
    ):
        validate_trade_contract(
            date(
                2017,
                1,
                27,
            ),
            date(
                2017,
                1,
                26,
            ),
            "CE",
            8250,
        )


def test_overnight_contract_is_valid():

    assert expiry_is_usable_for_overnight_trade(
        date(
            2017,
            1,
            24,
        ),
        date(
            2017,
            1,
            25,
        ),
        date(
            2017,
            1,
            26,
        ),
    )


def test_overnight_contract_expiring_next_day_is_valid():

    assert expiry_is_usable_for_overnight_trade(
        date(
            2017,
            1,
            25,
        ),
        date(
            2017,
            1,
            26,
        ),
        date(
            2017,
            1,
            26,
        ),
    )


def test_overnight_contract_expiring_on_entry_day_is_invalid():

    assert not expiry_is_usable_for_overnight_trade(
        date(
            2017,
            1,
            26,
        ),
        date(
            2017,
            1,
            27,
        ),
        date(
            2017,
            1,
            26,
        ),
    )


def test_next_trading_date_must_be_after_entry():

    assert not expiry_is_usable_for_overnight_trade(
        date(
            2017,
            1,
            25,
        ),
        date(
            2017,
            1,
            25,
        ),
        date(
            2017,
            1,
            26,
        ),
    )