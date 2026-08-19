from datetime import date

from expiry_calendar import (
    candidate_monthly_expiries,
    get_monthly_expiry_for_trade,
    get_nearest_expiry,
    last_thursday,
)


def test_last_thursday_january_2017():

    assert last_thursday(
        2017,
        1,
    ) == date(
        2017,
        1,
        26,
    )


def test_last_thursday_february_2017():

    assert last_thursday(
        2017,
        2,
    ) == date(
        2017,
        2,
        23,
    )


def test_last_thursday_march_2017():

    assert last_thursday(
        2017,
        3,
    ) == date(
        2017,
        3,
        30,
    )


def test_nearest_expiry_before_monthly_expiry():

    result = get_nearest_expiry(
        date(
            2017,
            1,
            20,
        )
    )

    assert result == date(
        2017,
        1,
        26,
    )


def test_trade_on_expiry_date():

    result = get_monthly_expiry_for_trade(
        date(
            2017,
            1,
            26,
        )
    )

    assert result == date(
        2017,
        1,
        26,
    )


def test_trade_after_expiry_moves_to_next_month():

    result = get_monthly_expiry_for_trade(
        date(
            2017,
            1,
            27,
        )
    )

    assert result == date(
        2017,
        2,
        23,
    )


def test_december_rolls_into_next_year():

    result = get_monthly_expiry_for_trade(
        date(
            2017,
            12,
            29,
        )
    )

    assert result == date(
        2018,
        1,
        25,
    )


def test_candidate_expiries_are_sorted():

    result = candidate_monthly_expiries(
        date(
            2017,
            6,
            15,
        )
    )

    assert result == sorted(result)

    assert len(result) == 3


def test_expiry_is_not_before_trade_date():

    trading_date = date(
        2017,
        8,
        25,
    )

    expiry = get_monthly_expiry_for_trade(
        trading_date
    )

    assert expiry >= trading_date