from datetime import date, datetime

import pytest

import nse_live_data
from live_market_data import LiveMarketDataError


def _valid_option_payload():
    return {
        "records": {
            "underlyingValue": 25000,
            "expiryDates": [
                "04-Sep-2026",
                "11-Sep-2026",
            ],
            "data": [
                {
                    "strikePrice": 25000,
                    "expiryDate": "04-Sep-2026",
                    "CE": {
                        "lastPrice": 150,
                        "openInterest": 1000,
                        "changeinOpenInterest": 100,
                        "totalTradedVolume": 500,
                    },
                    "PE": {
                        "lastPrice": 140,
                        "openInterest": 1200,
                        "changeinOpenInterest": 200,
                        "totalTradedVolume": 600,
                    },
                }
            ],
        }
    }


def test_nifty_quote_requires_positive_price():
    payload = {
        "data": {
            "info": {
                "lastPrice": 0,
                "previousClose": 24900,
            }
        }
    }

    with pytest.raises(LiveMarketDataError):
        nse_live_data._extract_quote_from_nse_payload(payload)


def test_nifty_quote_rejects_missing_price():
    payload = {
        "data": {
            "info": {
                "previousClose": 24900,
            }
        }
    }

    with pytest.raises(LiveMarketDataError):
        nse_live_data._extract_quote_from_nse_payload(payload)


def test_nifty_quote_accepts_valid_nse_payload():
    payload = {
        "data": {
            "info": {
                "lastPrice": 25000,
                "previousClose": 24900,
            },
            "timestamp": "02-Sep-2026 15:00:00",
        }
    }

    quote = nse_live_data._extract_quote_from_nse_payload(payload)

    assert quote.price == 25000
    assert quote.previous_close == 24900
    assert isinstance(quote.timestamp, datetime)


def test_nifty_quote_falls_back_to_yahoo(monkeypatch):
    class FakeSession:
        pass

    def fail_nse(*args, **kwargs):
        raise LiveMarketDataError("NSE unavailable")

    expected = nse_live_data.NiftyQuote(
        timestamp=datetime(2026, 9, 2, 15, 0),
        price=25000,
        previous_close=24900,
    )

    monkeypatch.setattr(
        nse_live_data,
        "_get_json",
        fail_nse,
    )
    monkeypatch.setattr(
        nse_live_data,
        "_fetch_nifty_quote_from_yahoo",
        lambda: expected,
    )

    quote = nse_live_data.fetch_nifty_quote(
        session=FakeSession()
    )

    assert quote == expected


def test_nifty_quote_fails_when_all_providers_fail(monkeypatch):
    class FakeSession:
        pass

    def fail_nse(*args, **kwargs):
        raise LiveMarketDataError("NSE unavailable")

    def fail_yahoo():
        raise LiveMarketDataError("Yahoo unavailable")

    monkeypatch.setattr(
        nse_live_data,
        "_get_json",
        fail_nse,
    )
    monkeypatch.setattr(
        nse_live_data,
        "_fetch_nifty_quote_from_yahoo",
        fail_yahoo,
    )

    with pytest.raises(LiveMarketDataError) as exc:
        nse_live_data.fetch_nifty_quote(
            session=FakeSession()
        )

    assert "NSE" in str(exc.value)
    assert "Yahoo" in str(exc.value)


def test_option_chain_normalization_rejects_invalid_payload():
    with pytest.raises(LiveMarketDataError):
        nse_live_data._build_option_chain(
            {"records": {"data": []}}
        )


def test_option_chain_normalization_requires_valid_strike():
    payload = {
        "records": {
            "underlyingValue": 25000,
            "expiryDates": ["04-Sep-2026"],
            "data": [
                {
                    "strikePrice": "invalid",
                    "expiryDate": "04-Sep-2026",
                    "CE": {"lastPrice": 100},
                    "PE": {"lastPrice": 100},
                }
            ],
        }
    }

    with pytest.raises(LiveMarketDataError):
        nse_live_data._build_option_chain(payload)


def test_option_chain_normalization_preserves_expiry():
    chain = nse_live_data._build_option_chain(
        _valid_option_payload()
    )

    assert date(2026, 9, 4) in chain.expiry_dates
    assert chain.records[0]["expiry"] == date(2026, 9, 4)


def test_option_chain_normalization_preserves_strike():
    chain = nse_live_data._build_option_chain(
        _valid_option_payload()
    )

    assert chain.records[0]["strike"] == 25000


def test_option_chain_normalization_preserves_ce_and_pe():
    chain = nse_live_data._build_option_chain(
        _valid_option_payload()
    )

    record = chain.records[0]

    assert record["CE"]["lastPrice"] == 150
    assert record["PE"]["lastPrice"] == 140


def test_available_expiries_are_sorted():
    payload = {
        "records": {
            "underlyingValue": 25000,
            "expiryDates": [
                "11-Sep-2026",
                "04-Sep-2026",
            ],
            "data": [
                {
                    "strikePrice": 25000,
                    "expiryDate": "11-Sep-2026",
                    "CE": {},
                    "PE": {},
                },
                {
                    "strikePrice": 25000,
                    "expiryDate": "04-Sep-2026",
                    "CE": {},
                    "PE": {},
                },
            ],
        }
    }

    expiries = nse_live_data.available_nifty_expiries(
        payload
    )

    assert expiries == [
        date(2026, 9, 4),
        date(2026, 9, 11),
    ]


def test_nearest_expiry_ignores_past_expiry():
    payload = {
        "records": {
            "underlyingValue": 25000,
            "expiryDates": [
                "28-Aug-2026",
                "04-Sep-2026",
                "11-Sep-2026",
            ],
            "data": [
                {
                    "strikePrice": 25000,
                    "expiryDate": "28-Aug-2026",
                    "CE": {},
                    "PE": {},
                },
                {
                    "strikePrice": 25000,
                    "expiryDate": "04-Sep-2026",
                    "CE": {},
                    "PE": {},
                },
                {
                    "strikePrice": 25000,
                    "expiryDate": "11-Sep-2026",
                    "CE": {},
                    "PE": {},
                },
            ],
        }
    }

    expiry = nse_live_data.nearest_nifty_expiry(
        payload,
        today=date(2026, 9, 2),
    )

    assert expiry == date(2026, 9, 4)


def test_nearest_expiry_fails_without_future_expiry():
    payload = {
        "records": {
            "underlyingValue": 25000,
            "expiryDates": [
                "28-Aug-2026",
            ],
            "data": [
                {
                    "strikePrice": 25000,
                    "expiryDate": "28-Aug-2026",
                    "CE": {},
                    "PE": {},
                }
            ],
        }
    }

    with pytest.raises(LiveMarketDataError):
        nse_live_data.nearest_nifty_expiry(
            payload,
            today=date(2026, 9, 2),
        )


def test_option_chain_builder_requires_records():
    payload = {
        "records": {
            "underlyingValue": 25000,
            "expiryDates": ["04-Sep-2026"],
            "data": [],
        }
    }

    with pytest.raises(LiveMarketDataError):
        nse_live_data._build_option_chain(payload)


def test_option_chain_snapshot_rejects_missing_expiry():
    with pytest.raises(LiveMarketDataError):
        nse_live_data.build_option_chain_snapshot(
            payload=_valid_option_payload(),
            nifty_price=25000,
            expiry=None,
        )


def test_option_chain_snapshot_rejects_non_positive_nifty():
    with pytest.raises(ValueError):
        nse_live_data.build_option_chain_snapshot(
            payload=_valid_option_payload(),
            nifty_price=0,
            expiry=date(2026, 9, 4),
        )


def test_option_chain_snapshot_rejects_negative_window():
    with pytest.raises(ValueError):
        nse_live_data.build_option_chain_snapshot(
            payload=_valid_option_payload(),
            nifty_price=25000,
            expiry=date(2026, 9, 4),
            strikes_each_side=-1,
        )


def test_option_chain_snapshot_builds_valid_statistics():
    snapshot = nse_live_data.build_option_chain_snapshot(
        payload=_valid_option_payload(),
        nifty_price=25000,
        expiry=date(2026, 9, 4),
        strikes_each_side=0,
    )

    assert snapshot.ce_oi == 1000
    assert snapshot.pe_oi == 1200
    assert snapshot.ce_volume == 500
    assert snapshot.pe_volume == 600