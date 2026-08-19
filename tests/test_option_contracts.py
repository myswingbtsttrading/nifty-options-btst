from datetime import date, datetime

import pytest

from option_contracts import (
    available_strikes,
    contracts_for_date,
    contracts_for_expiry,
    discover_contracts,
    find_contract,
    find_monthly_contract,
    get_row_contract_key,
    normalize_expiry,
    normalize_option_type,
    normalize_strike,
    has_contract,
)


def make_row(
    trading_date=date(2017, 1, 20),
    expiry=date(2017, 1, 26),
    option_type="CE",
    strike=8250,
):
    return {
        "timestamp": datetime(
            trading_date.year,
            trading_date.month,
            trading_date.day,
            15,
            0,
        ),
        "expiry": expiry,
        "option_type": option_type,
        "strike": strike,
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.5,
        "volume": 100,
    }


def test_normalize_ce():

    assert normalize_option_type("ce") == "CE"


def test_normalize_pe():

    assert normalize_option_type(" PE ") == "PE"


def test_invalid_option_type():

    with pytest.raises(ValueError):
        normalize_option_type("CALL")


def test_normalize_strike():

    assert normalize_strike("8250") == 8250.0


def test_invalid_strike():

    with pytest.raises(ValueError):
        normalize_strike(0)


def test_normalize_expiry_date():

    assert normalize_expiry(
        date(2017, 1, 26)
    ) == date(2017, 1, 26)


def test_normalize_expiry_datetime():

    value = normalize_expiry(
        datetime(
            2017,
            1,
            26,
            15,
            0,
        )
    )

    assert value == date(
        2017,
        1,
        26,
    )


def test_normalize_expiry_string():

    assert normalize_expiry(
        "2017-01-26"
    ) == date(
        2017,
        1,
        26,
    )


def test_invalid_expiry_returns_none():

    assert normalize_expiry(
        "invalid"
    ) is None


def test_row_contract_key():

    row = make_row()

    assert get_row_contract_key(
        row
    ) == (
        date(2017, 1, 20),
        date(2017, 1, 26),
        "CE",
        8250.0,
    )


def test_discover_contracts():

    rows = [
        make_row(
            option_type="CE",
            strike=8250,
        ),
        make_row(
            option_type="PE",
            strike=8250,
        ),
        make_row(
            option_type="CE",
            strike=8300,
        ),
    ]

    result = discover_contracts(
        rows
    )

    assert len(result) == 3


def test_contracts_for_date():

    rows = [
        make_row(
            trading_date=date(
                2017,
                1,
                20,
            )
        ),
        make_row(
            trading_date=date(
                2017,
                1,
                23,
            )
        ),
    ]

    result = contracts_for_date(
        rows,
        date(
            2017,
            1,
            20,
        ),
    )

    assert len(result) == 1


def test_contracts_for_expiry():

    rows = [
        make_row(
            expiry=date(
                2017,
                1,
                26,
            )
        ),
        make_row(
            expiry=date(
                2017,
                2,
                23,
            )
        ),
    ]

    result = contracts_for_expiry(
        rows,
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

    assert len(result) == 1
    assert result[0][1] == date(
        2017,
        1,
        26,
    )


def test_find_contract():

    rows = [
        make_row()
    ]

    result = find_contract(
        rows,
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

    assert result == (
        date(2017, 1, 20),
        date(2017, 1, 26),
        "CE",
        8250.0,
    )


def test_find_missing_contract():

    rows = [
        make_row()
    ]

    result = find_contract(
        rows,
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
        9000,
    )

    assert result is None


def test_find_monthly_contract():

    rows = [
        make_row()
    ]

    result = find_monthly_contract(
        rows,
        date(
            2017,
            1,
            20,
        ),
        "CE",
        8250,
    )

    assert result is not None
    assert result[1] == date(
        2017,
        1,
        26,
    )


def test_available_strikes():

    rows = [
        make_row(
            strike=8200
        ),
        make_row(
            strike=8250
        ),
        make_row(
            strike=8300
        ),
        make_row(
            option_type="PE",
            strike=8250,
        ),
    ]

    result = available_strikes(
        rows,
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
    )

    assert result == [
        8200.0,
        8250.0,
        8300.0,
    ]


def test_has_contract_true():

    rows = [
        make_row()
    ]

    assert has_contract(
        rows,
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


def test_has_contract_false():

    rows = [
        make_row()
    ]

    assert not has_contract(
        rows,
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
        9000,
    )