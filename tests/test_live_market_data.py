from datetime import date, datetime

import pytest
import requests

from live_market_data import (
    HttpMarketDataClient,
    LiveMarketDataError,
    LiveOptionQuote,
    LiveUnderlyingQuote,
    MockMarketDataClient,
    normalize_option_quote,
    normalize_underlying_quote,
)


def test_normalize_underlying_quote():
    result = normalize_underlying_quote(
        {
            "timestamp": "2026-08-25 15:00:00",
            "ltp": "25020.50",
            "previous_close": "24900.00",
        }
    )

    assert result.timestamp == datetime(
        2026,
        8,
        25,
        15,
        0,
    )

    assert result.price == 25020.50
    assert result.previous_close == 24900.00


def test_normalize_underlying_quote_accepts_iso_timestamp():
    result = normalize_underlying_quote(
        {
            "timestamp": "2026-08-25T15:00:00",
            "price": 25020,
            "prev_close": 24900,
        }
    )

    assert result.price == 25020.0
    assert result.previous_close == 24900.0


def test_normalize_option_quote():
    result = normalize_option_quote(
        {
            "timestamp": "2026-08-25 15:00:00",
            "expiry": "2026-08-27",
            "strike": "25000",
            "option_type": "CE",
            "ltp": "105.50",
        }
    )

    assert result.timestamp == datetime(
        2026,
        8,
        25,
        15,
        0,
    )

    assert result.expiry == date(
        2026,
        8,
        27,
    )

    assert result.strike == 25000.0
    assert result.option_type == "CE"
    assert result.price == 105.50


def test_option_type_is_normalized():
    result = normalize_option_quote(
        {
            "timestamp": "2026-08-25T15:00",
            "expiry": "27-08-2026",
            "strike": 25000,
            "option_type": " pe ",
            "price": 110,
        }
    )

    assert result.option_type == "PE"


def test_underlying_requires_price():
    with pytest.raises(
        LiveMarketDataError,
        match="no price",
    ):
        normalize_underlying_quote(
            {
                "timestamp": "2026-08-25 15:00:00",
                "previous_close": 24900,
            }
        )


def test_underlying_requires_previous_close():
    with pytest.raises(
        LiveMarketDataError,
        match="previous close",
    ):
        normalize_underlying_quote(
            {
                "timestamp": "2026-08-25 15:00:00",
                "price": 25000,
            }
        )


def test_option_requires_all_fields():
    with pytest.raises(
        LiveMarketDataError,
        match="missing fields",
    ):
        normalize_option_quote(
            {
                "timestamp": "2026-08-25 15:00:00",
                "expiry": "2026-08-27",
                "strike": 25000,
            }
        )


def test_invalid_option_type_is_rejected():
    with pytest.raises(
        LiveMarketDataError,
        match="Unsupported option type",
    ):
        normalize_option_quote(
            {
                "timestamp": "2026-08-25 15:00:00",
                "expiry": "2026-08-27",
                "strike": 25000,
                "option_type": "XX",
                "price": 100,
            }
        )


def test_invalid_underlying_price_is_rejected():
    with pytest.raises(
        LiveMarketDataError,
        match="underlying price",
    ):
        normalize_underlying_quote(
            {
                "timestamp": "2026-08-25 15:00:00",
                "price": 0,
                "previous_close": 24900,
            }
        )


def test_invalid_option_price_is_rejected():
    with pytest.raises(
        LiveMarketDataError,
        match="option price",
    ):
        normalize_option_quote(
            {
                "timestamp": "2026-08-25 15:00:00",
                "expiry": "2026-08-27",
                "strike": 25000,
                "option_type": "CE",
                "price": 0,
            }
        )


def test_mock_market_data_client():
    underlying = LiveUnderlyingQuote(
        timestamp=datetime(
            2026,
            8,
            25,
            15,
            0,
        ),
        price=25020.0,
        previous_close=24900.0,
    )

    option = LiveOptionQuote(
        timestamp=datetime(
            2026,
            8,
            25,
            15,
            0,
        ),
        expiry=date(
            2026,
            8,
            27,
        ),
        strike=25000,
        option_type="CE",
        price=105.0,
    )

    client = MockMarketDataClient(
        underlying=underlying,
        options=[option],
    )

    assert client.get_underlying() == underlying

    result = client.get_option_quote(
        expiry=date(
            2026,
            8,
            27,
        ),
        strike=25000,
        option_type="CE",
    )

    assert result == option


def test_mock_client_rejects_missing_option():
    underlying = LiveUnderlyingQuote(
        timestamp=datetime(
            2026,
            8,
            25,
            15,
            0,
        ),
        price=25020.0,
        previous_close=24900.0,
    )

    client = MockMarketDataClient(
        underlying=underlying,
        options=[],
    )

    with pytest.raises(
        LiveMarketDataError,
        match="not available",
    ):
        client.get_option_quote(
            expiry=date(
                2026,
                8,
                27,
            ),
            strike=25000,
            option_type="CE",
        )


def test_http_client_rejects_empty_url():
    client = HttpMarketDataClient()

    with pytest.raises(
        ValueError,
        match="url",
    ):
        client.get_json("")


def test_http_client_rejects_non_200():
    class FakeResponse:
        status_code = 500

        def json(self):
            return {}

    class FakeSession:
        def get(
            self,
            *args,
            **kwargs,
        ):
            return FakeResponse()

    client = HttpMarketDataClient(
        session=FakeSession()
    )

    with pytest.raises(
        LiveMarketDataError,
        match="HTTP 500",
    ):
        client.get_json(
            "https://example.com"
        )


def test_http_client_rejects_invalid_json():
    class FakeResponse:
        status_code = 200

        def json(self):
            raise ValueError("bad json")

    class FakeSession:
        def get(
            self,
            *args,
            **kwargs,
        ):
            return FakeResponse()

    client = HttpMarketDataClient(
        session=FakeSession()
    )

    with pytest.raises(
        LiveMarketDataError,
        match="valid JSON",
    ):
        client.get_json(
            "https://example.com"
        )


def test_http_client_converts_request_error():
    class FakeSession:
        def get(
            self,
            *args,
            **kwargs,
        ):
            raise requests.RequestException(
                "connection failed"
            )

    client = HttpMarketDataClient(
        session=FakeSession()
    )

    with pytest.raises(
        LiveMarketDataError,
        match="request failed",
    ):
        client.get_json(
            "https://example.com"
        )