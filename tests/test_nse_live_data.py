from datetime import date

import pytest

from live_market_data import LiveMarketDataError
from nse_live_data import (
    available_nifty_expiries,
    build_option_chain_snapshot,
    find_option_quote,
    nearest_nifty_expiry,
)


def _payload():
    return {
        "records": {
            "timestamp": "25-Aug-2026 15:00:00",
            "expiryDates": [
                "27-Aug-2026",
                "03-Sep-2026",
            ],
            "data": [
                {
                    "strikePrice": 24900,
                    "expiryDate": "27-Aug-2026",
                    "CE": {
                        "openInterest": 1000,
                        "changeinOpenInterest": 100,
                        "totalTradedVolume": 500,
                        "lastPrice": 140,
                    },
                    "PE": {
                        "openInterest": 1200,
                        "changeinOpenInterest": 200,
                        "totalTradedVolume": 700,
                        "lastPrice": 90,
                    },
                },
                {
                    "strikePrice": 24950,
                    "expiryDate": "27-Aug-2026",
                    "CE": {
                        "openInterest": 1100,
                        "changeinOpenInterest": 110,
                        "totalTradedVolume": 510,
                        "lastPrice": 120,
                    },
                    "PE": {
                        "openInterest": 1300,
                        "changeinOpenInterest": 210,
                        "totalTradedVolume": 710,
                        "lastPrice": 100,
                    },
                },
                {
                    "strikePrice": 25000,
                    "expiryDate": "27-Aug-2026",
                    "CE": {
                        "openInterest": 1500,
                        "changeinOpenInterest": 150,
                        "totalTradedVolume": 600,
                        "lastPrice": 105,
                    },
                    "PE": {
                        "openInterest": 1800,
                        "changeinOpenInterest": 250,
                        "totalTradedVolume": 800,
                        "lastPrice": 95,
                    },
                },
                {
                    "strikePrice": 25050,
                    "expiryDate": "27-Aug-2026",
                    "CE": {
                        "openInterest": 900,
                        "changeinOpenInterest": 90,
                        "totalTradedVolume": 400,
                        "lastPrice": 85,
                    },
                    "PE": {
                        "openInterest": 1000,
                        "changeinOpenInterest": 190,
                        "totalTradedVolume": 650,
                        "lastPrice": 125,
                    },
                },
                {
                    "strikePrice": 25100,
                    "expiryDate": "27-Aug-2026",
                    "CE": {
                        "openInterest": 800,
                        "changeinOpenInterest": 80,
                        "totalTradedVolume": 300,
                        "lastPrice": 70,
                    },
                    "PE": {
                        "openInterest": 950,
                        "changeinOpenInterest": 180,
                        "totalTradedVolume": 600,
                        "lastPrice": 150,
                    },
                },
            ],
        }
    }


def test_available_expiries():
    result = available_nifty_expiries(
        _payload()
    )

    assert result == [
        date(2026, 8, 27),
        date(2026, 9, 3),
    ]


def test_nearest_expiry():
    result = nearest_nifty_expiry(
        _payload(),
        today=date(2026, 8, 25),
    )

    assert result == date(2026, 8, 27)


def test_nearest_expiry_skips_expired():
    result = nearest_nifty_expiry(
        _payload(),
        today=date(2026, 8, 28),
    )

    assert result == date(2026, 9, 3)


def test_build_option_chain_snapshot():
    result = build_option_chain_snapshot(
        _payload(),
        nifty_price=25000,
        expiry=date(2026, 8, 27),
        strikes_each_side=2,
    )

    assert result.ce_oi == 5300
    assert result.pe_oi == 6250

    assert result.ce_oi_change == 530
    assert result.pe_oi_change == 1030

    assert result.ce_volume == 2310
    assert result.pe_volume == 3460


def test_find_ce_quote():
    result = find_option_quote(
        _payload(),
        expiry=date(2026, 8, 27),
        strike=25000,
        option_type="CE",
    )

    assert result.expiry == date(2026, 8, 27)
    assert result.strike == 25000
    assert result.option_type == "CE"
    assert result.price == 105.0


def test_find_pe_quote():
    result = find_option_quote(
        _payload(),
        expiry=date(2026, 8, 27),
        strike=25000,
        option_type="PE",
    )

    assert result.option_type == "PE"
    assert result.price == 95.0


def test_find_missing_quote_fails():
    with pytest.raises(
        LiveMarketDataError,
        match="not found",
    ):
        find_option_quote(
            _payload(),
            expiry=date(2026, 8, 27),
            strike=25200,
            option_type="CE",
        )


def test_invalid_option_type_fails():
    with pytest.raises(
        ValueError,
        match="CE or PE",
    ):
        find_option_quote(
            _payload(),
            expiry=date(2026, 8, 27),
            strike=25000,
            option_type="XX",
        )


def test_missing_expiry_data_fails():
    with pytest.raises(
        LiveMarketDataError,
        match="No option-chain rows",
    ):
        build_option_chain_snapshot(
            {
                "records": {
                    "data": []
                }
            },
            nifty_price=25000,
            expiry=date(2026, 8, 27),
        )


def test_negative_nifty_price_fails():
    with pytest.raises(
        ValueError,
        match="positive",
    ):
        build_option_chain_snapshot(
            _payload(),
            nifty_price=-1,
            expiry=date(2026, 8, 27),
        )


def test_invalid_strike_window_fails():
    with pytest.raises(
        ValueError,
        match="cannot be negative",
    ):
        build_option_chain_snapshot(
            _payload(),
            nifty_price=25000,
            expiry=date(2026, 8, 27),
            strikes_each_side=-1,
        )