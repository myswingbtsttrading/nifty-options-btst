from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Optional, Protocol

import requests


class LiveMarketDataError(RuntimeError):
    """Raised when live market data cannot be obtained or validated."""


@dataclass(frozen=True)
class LiveUnderlyingQuote:
    timestamp: datetime
    price: float
    previous_close: float


@dataclass(frozen=True)
class LiveOptionQuote:
    timestamp: datetime
    expiry: date
    strike: float
    option_type: str
    price: float


class MarketDataClient(Protocol):
    def get_underlying(
        self,
    ) -> LiveUnderlyingQuote:
        ...

    def get_option_quote(
        self,
        expiry: date,
        strike: float,
        option_type: str,
    ) -> LiveOptionQuote:
        ...


def _positive_float(
    value: Any,
    field: str,
) -> float:
    try:
        result = float(value)
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise LiveMarketDataError(
            f"Invalid {field}: {value!r}"
        ) from exc

    if result <= 0:
        raise LiveMarketDataError(
            f"{field} must be positive."
        )

    return result


def _parse_datetime(
    value: Any,
) -> datetime:
    if isinstance(value, datetime):
        return value

    if value is None:
        raise LiveMarketDataError(
            "Missing timestamp."
        )

    text = str(value).strip()

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
    )

    for fmt in formats:
        try:
            return datetime.strptime(
                text,
                fmt,
            )
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(
            text.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError as exc:
        raise LiveMarketDataError(
            f"Unsupported timestamp: {text}"
        ) from exc


def _parse_expiry(
    value: Any,
) -> date:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if value is None:
        raise LiveMarketDataError(
            "Missing option expiry."
        )

    text = str(value).strip()

    formats = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
    )

    for fmt in formats:
        try:
            return datetime.strptime(
                text,
                fmt,
            ).date()
        except ValueError:
            continue

    raise LiveMarketDataError(
        f"Unsupported expiry: {text}"
    )


def _first_present(
    payload: Mapping[str, Any],
    names: tuple[str, ...],
) -> Any:
    for name in names:
        if (
            name in payload
            and payload[name] is not None
            and payload[name] != ""
        ):
            return payload[name]

    return None


def normalize_underlying_quote(
    payload: Mapping[str, Any],
) -> LiveUnderlyingQuote:
    timestamp = _first_present(
        payload,
        (
            "timestamp",
            "datetime",
            "date_time",
            "DateTime",
        ),
    )

    price = _first_present(
        payload,
        (
            "price",
            "ltp",
            "last_price",
            "close",
            "Close",
        ),
    )

    previous_close = _first_present(
        payload,
        (
            "previous_close",
            "prev_close",
            "previousClose",
            "prevClose",
        ),
    )

    if timestamp is None:
        raise LiveMarketDataError(
            "Underlying quote has no timestamp."
        )

    if price is None:
        raise LiveMarketDataError(
            "Underlying quote has no price."
        )

    if previous_close is None:
        raise LiveMarketDataError(
            "Underlying quote has no previous close."
        )

    return LiveUnderlyingQuote(
        timestamp=_parse_datetime(
            timestamp
        ),
        price=_positive_float(
            price,
            "underlying price",
        ),
        previous_close=_positive_float(
            previous_close,
            "previous close",
        ),
    )


def normalize_option_quote(
    payload: Mapping[str, Any],
) -> LiveOptionQuote:
    timestamp = _first_present(
        payload,
        (
            "timestamp",
            "datetime",
            "date_time",
            "DateTime",
        ),
    )

    expiry = _first_present(
        payload,
        (
            "expiry",
            "expiry_date",
            "Expiry",
            "ExpiryDate",
        ),
    )

    strike = _first_present(
        payload,
        (
            "strike",
            "strike_price",
            "Strike",
            "StrikePrice",
        ),
    )

    option_type = _first_present(
        payload,
        (
            "option_type",
            "optiontype",
            "type",
            "OptionType",
        ),
    )

    price = _first_present(
        payload,
        (
            "price",
            "ltp",
            "last_price",
            "close",
            "Close",
        ),
    )

    missing = []

    if timestamp is None:
        missing.append("timestamp")

    if expiry is None:
        missing.append("expiry")

    if strike is None:
        missing.append("strike")

    if option_type is None:
        missing.append("option_type")

    if price is None:
        missing.append("price")

    if missing:
        raise LiveMarketDataError(
            "Option quote missing fields: "
            + ", ".join(missing)
        )

    normalized_type = str(
        option_type
    ).strip().upper()

    if normalized_type not in {
        "CE",
        "PE",
    }:
        raise LiveMarketDataError(
            f"Unsupported option type: "
            f"{normalized_type}"
        )

    return LiveOptionQuote(
        timestamp=_parse_datetime(
            timestamp
        ),
        expiry=_parse_expiry(
            expiry
        ),
        strike=_positive_float(
            strike,
            "option strike",
        ),
        option_type=normalized_type,
        price=_positive_float(
            price,
            "option price",
        ),
    )


class HttpMarketDataClient:
    """
    Generic HTTP market-data adapter.

    The actual vendor/API endpoint is intentionally injected
    through callables rather than hard-coded into the strategy.
    """

    def __init__(
        self,
        session: Optional[
            requests.Session
        ] = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be positive."
            )

        self.session = (
            session
            if session is not None
            else requests.Session()
        )

        self.timeout_seconds = (
            timeout_seconds
        )

    def get_json(
        self,
        url: str,
        params: Optional[
            Mapping[str, Any]
        ] = None,
        headers: Optional[
            Mapping[str, str]
        ] = None,
    ) -> Any:
        if not url:
            raise ValueError(
                "url must not be empty."
            )

        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise LiveMarketDataError(
                f"Market-data request failed: {exc}"
            ) from exc

        if response.status_code != 200:
            raise LiveMarketDataError(
                "Market-data request returned "
                f"HTTP {response.status_code}."
            )

        try:
            return response.json()
        except ValueError as exc:
            raise LiveMarketDataError(
                "Market-data response was not valid JSON."
            ) from exc


class MockMarketDataClient:
    """
    Deterministic client for tests and paper validation.

    This is deliberately not connected to a broker.
    """

    def __init__(
        self,
        underlying: LiveUnderlyingQuote,
        options: list[LiveOptionQuote],
    ) -> None:
        self.underlying = underlying
        self.options = list(options)

    def get_underlying(
        self,
    ) -> LiveUnderlyingQuote:
        return self.underlying

    def get_option_quote(
        self,
        expiry: date,
        strike: float,
        option_type: str,
    ) -> LiveOptionQuote:
        normalized_type = option_type.upper()

        matches = [
            quote
            for quote in self.options
            if quote.expiry == expiry
            and quote.strike == strike
            and quote.option_type == normalized_type
        ]

        if not matches:
            raise LiveMarketDataError(
                "Requested option quote was not "
                "available in the market-data snapshot."
            )

        return matches[0]