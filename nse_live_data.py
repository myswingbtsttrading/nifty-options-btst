from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import requests

from live_market_data import (
    LiveMarketDataError,
    normalize_option_quote,
)


NSE_BASE_URL = "https://www.nseindia.com"

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,"
        "image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://www.nseindia.com/option-chain",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "DNT": "1",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "X-Requested-With": "XMLHttpRequest",
}

YAHOO_CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI"
)

YAHOO_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; K) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass(frozen=True)
class NiftyQuote:
    timestamp: datetime
    price: float
    previous_close: float


@dataclass(frozen=True)
class OptionChainSnapshot:
    ce_oi: float
    pe_oi: float
    ce_oi_change: float
    pe_oi_change: float
    ce_volume: float
    pe_volume: float


@dataclass(frozen=True)
class NiftyOptionChain:
    timestamp: datetime
    underlying_value: float
    expiry_dates: tuple[date, ...]
    records: tuple[dict[str, Any], ...]


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update(NSE_HEADERS)

    try:
        session.get(
            NSE_BASE_URL,
            timeout=20,
        )
    except requests.RequestException:
        pass

    try:
        session.get(
            f"{NSE_BASE_URL}/option-chain",
            params={
                "symbol": "NIFTY",
            },
            timeout=20,
        )
    except requests.RequestException:
        pass

    return session


def _get_json(
    session: requests.Session,
    url: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        response = session.get(
            url,
            params=params,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise LiveMarketDataError(
            f"NSE request failed: {exc}"
        ) from exc

    if response.status_code != 200:
        raise LiveMarketDataError(
            f"NSE request returned HTTP "
            f"{response.status_code}."
        )

    content_type = (
        response.headers.get(
            "Content-Type",
            "",
        )
        .lower()
    )

    if (
        content_type
        and "json" not in content_type
    ):
        raise LiveMarketDataError(
            "NSE returned a non-JSON response."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise LiveMarketDataError(
            "NSE returned invalid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise LiveMarketDataError(
            "NSE returned an unexpected response."
        )

    return payload


def _first_float(
    *values: Any,
) -> float | None:
    for value in values:
        if value is None:
            continue

        try:
            return float(value)
        except (
            TypeError,
            ValueError,
        ):
            continue

    return None


def _parse_nse_datetime(
    value: Any,
) -> datetime:
    if isinstance(value, datetime):
        return value

    if value is None:
        return datetime.now()

    text = str(value).strip()

    formats = (
        "%d-%b-%Y %H:%M:%S",
        "%d-%b-%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
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
    except ValueError:
        return datetime.now()


def _parse_expiry(
    value: Any,
) -> date | None:
    if isinstance(
        value,
        datetime,
    ):
        return value.date()

    if isinstance(
        value,
        date,
    ):
        return value

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    formats = (
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
    )

    for fmt in formats:
        try:
            return datetime.strptime(
                text,
                fmt,
            ).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(
            text.replace(
                "Z",
                "+00:00",
            )
        ).date()
    except ValueError:
        return None


def nearest_nifty_expiry(
    chain: (
        NiftyOptionChain
        | dict[str, Any]
    ),
    today: date | None = None,
) -> date:
    if isinstance(
        chain,
        NiftyOptionChain,
    ):
        expiry_dates = tuple(
            chain.expiry_dates
        )

        current_date = (
            today
            if today is not None
            else chain.timestamp.date()
        )
    else:
        expiry_dates = tuple(
            available_nifty_expiries(
                chain
            )
        )

        current_date = (
            today
            if today is not None
            else date.today()
        )

    future_expiries = [
        expiry
        for expiry in expiry_dates
        if expiry >= current_date
    ]

    if not future_expiries:
        raise LiveMarketDataError(
            "NSE option chain contains no future NIFTY expiry."
        )

    return min(future_expiries)


def _extract_quote_from_nse_payload(
    payload: dict[str, Any],
) -> NiftyQuote:
    data = payload.get("data")

    if isinstance(data, dict):
        info = data.get(
            "info",
            data,
        )

        price = _first_float(
            info.get("lastPrice"),
            info.get("last"),
            info.get("ltp"),
        )

        previous_close = _first_float(
            info.get("previousClose"),
            info.get("prevClose"),
            info.get("previous_close"),
        )

        timestamp = (
            data.get("timestamp")
            or info.get("timestamp")
            or payload.get("timestamp")
        )
    else:
        info = payload

        price = _first_float(
            info.get("lastPrice"),
            info.get("last"),
            info.get("ltp"),
        )

        previous_close = _first_float(
            info.get("previousClose"),
            info.get("prevClose"),
            info.get("previous_close"),
        )

        timestamp = payload.get("timestamp")

    if price is None:
        raise LiveMarketDataError(
            "NSE NIFTY quote did not contain a valid price."
        )

    if price <= 0:
        raise LiveMarketDataError(
            "NSE NIFTY quote price must be positive."
        )

    if previous_close is None:
        previous_close = price

    return NiftyQuote(
        timestamp=_parse_nse_datetime(timestamp),
        price=price,
        previous_close=previous_close,
    )


def _fetch_nifty_quote_from_yahoo() -> NiftyQuote:
    now = datetime.now()

    start = (
        now.timestamp()
        - 3 * 24 * 60 * 60
    )

    end = (
        now.timestamp()
        + 60
    )

    try:
        response = requests.get(
            YAHOO_CHART_URL,
            params={
                "period1": int(start),
                "period2": int(end),
                "interval": "1m",
                "events": "history",
                "includePrePost": "false",
            },
            headers=YAHOO_HEADERS,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise LiveMarketDataError(
            f"Yahoo NIFTY quote request failed: {exc}"
        ) from exc

    if response.status_code != 200:
        raise LiveMarketDataError(
            "Yahoo NIFTY quote returned HTTP "
            f"{response.status_code}."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise LiveMarketDataError(
            "Yahoo NIFTY quote returned invalid JSON."
        ) from exc

    chart = payload.get(
        "chart",
        {},
    )

    results = chart.get(
        "result"
    )

    if (
        not isinstance(results, list)
        or not results
    ):
        raise LiveMarketDataError(
            "Yahoo NIFTY quote returned no chart data."
        )

    result = results[0]

    meta = result.get(
        "meta",
        {},
    )

    timestamps = result.get(
        "timestamp",
        [],
    )

    quote_rows = (
        result.get(
            "indicators",
            {},
        )
        .get(
            "quote",
            [],
        )
    )

    if (
        not isinstance(
            quote_rows,
            list,
        )
        or not quote_rows
    ):
        raise LiveMarketDataError(
            "Yahoo NIFTY quote returned no price rows."
        )

    closes = quote_rows[0].get(
        "close",
        [],
    )

    observations: list[
        tuple[int, float]
    ] = []

    for timestamp, close in zip(
        timestamps,
        closes,
    ):
        if close is None:
            continue

        try:
            observations.append(
                (
                    int(timestamp),
                    float(close),
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

    if not observations:
        raise LiveMarketDataError(
            "Yahoo NIFTY quote contained no valid prices."
        )

    timestamp_value, price = observations[-1]

    if price <= 0:
        raise LiveMarketDataError(
            "Yahoo NIFTY quote price must be positive."
        )

    previous_close = _first_float(
        meta.get("previousClose"),
        meta.get("chartPreviousClose"),
    )

    if previous_close is None:
        previous_close = price

    return NiftyQuote(
        timestamp=datetime.fromtimestamp(
            timestamp_value
        ),
        price=price,
        previous_close=previous_close,
    )


def fetch_nifty_quote(
    session: requests.Session | None = None,
) -> NiftyQuote:
    """
    Fetch NIFTY 50.

    Provider order:
        1. NSE equity-stockIndices
        2. NSE allIndices
        3. Yahoo Finance fallback
    """

    active_session = (
        session
        if session is not None
        else _session()
    )

    urls = (
        (
            f"{NSE_BASE_URL}/api/equity-stockIndices",
            {
                "index": "NIFTY 50",
            },
        ),
        (
            f"{NSE_BASE_URL}/api/allIndices",
            None,
        ),
    )

    errors: list[str] = []

    for url, params in urls:
        try:
            payload = _get_json(
                active_session,
                url,
                params=params,
            )

            if "allIndices" in payload:
                indices = payload.get(
                    "data",
                    [],
                )

                if not isinstance(
                    indices,
                    list,
                ):
                    errors.append(
                        "NSE allIndices returned invalid data."
                    )
                    continue

                match = None

                for item in indices:
                    if not isinstance(
                        item,
                        dict,
                    ):
                        continue

                    name = str(
                        item.get("index")
                        or item.get("indexSymbol")
                        or ""
                    ).strip().upper()

                    if name in {
                        "NIFTY 50",
                        "NIFTY",
                    }:
                        match = item
                        break

                if match is None:
                    errors.append(
                        "NSE allIndices did not contain NIFTY 50."
                    )
                    continue

                price = _first_float(
                    match.get("last"),
                    match.get("lastPrice"),
                    match.get("ltp"),
                )

                previous_close = _first_float(
                    match.get("previousClose"),
                    match.get("prevClose"),
                )

                if price is None:
                    errors.append(
                        "NSE allIndices contained no NIFTY price."
                    )
                    continue

                if price <= 0:
                    errors.append(
                        "NSE allIndices contained a non-positive NIFTY price."
                    )
                    continue

                if previous_close is None:
                    previous_close = price

                return NiftyQuote(
                    timestamp=_parse_nse_datetime(
                        match.get("timeVal")
                        or match.get("timestamp")
                    ),
                    price=price,
                    previous_close=previous_close,
                )

            return _extract_quote_from_nse_payload(
                payload
            )

        except LiveMarketDataError as exc:
            errors.append(str(exc))

    try:
        yahoo_quote = _fetch_nifty_quote_from_yahoo()

        print(
            "WARNING: NSE NIFTY quote unavailable; "
            "using Yahoo Finance fallback."
        )

        return yahoo_quote

    except LiveMarketDataError as exc:
        errors.append(str(exc))

    details = " | ".join(errors)

    raise LiveMarketDataError(
        "Unable to fetch NIFTY 50 quote from NSE "
        "or Yahoo Finance. "
        f"Provider errors: {details}"
    )


def _normalise_chain_records(
    payload: dict[str, Any] | NiftyOptionChain,
) -> tuple[
    float,
    tuple[date, ...],
    tuple[dict[str, Any], ...],
]:
    if isinstance(payload, NiftyOptionChain):
        if not payload.records:
            raise LiveMarketDataError(
                "NSE returned no NIFTY option-chain records."
            )

        return (
            float(payload.underlying_value),
            tuple(payload.expiry_dates),
            tuple(payload.records),
        )

    if not isinstance(
        payload,
        dict,
    ):
        raise LiveMarketDataError(
            "NSE option-chain payload is invalid."
        )

    records_payload = payload.get("records")

    if not isinstance(
        records_payload,
        dict,
    ):
        records_payload = {}

    filtered_payload = payload.get("filtered")

    if not isinstance(
        filtered_payload,
        dict,
    ):
        filtered_payload = {}

    raw_data = records_payload.get("data")

    if not isinstance(
        raw_data,
        list,
    ):
        raw_data = filtered_payload.get("data")

    if not isinstance(
        raw_data,
        list,
    ):
        raw_data = payload.get("data")

    if not isinstance(
        raw_data,
        list,
    ):
        raw_data = []

    underlying = _first_float(
        records_payload.get("underlyingValue"),
        records_payload.get("underlying_value"),
        payload.get("underlyingValue"),
        payload.get("underlying_value"),
    )

    if underlying is None:
        for item in raw_data:
            if not isinstance(item, dict):
                continue

            ce = item.get("CE")
            pe = item.get("PE")

            if isinstance(ce, dict):
                underlying = _first_float(
                    ce.get("underlyingValue"),
                    ce.get("underlying_value"),
                )

            if underlying is None and isinstance(pe, dict):
                underlying = _first_float(
                    pe.get("underlyingValue"),
                    pe.get("underlying_value"),
                )

            if underlying is not None:
                break

    if underlying is None:
        underlying = 0.0

    raw_expiries = records_payload.get(
        "expiryDates",
        payload.get(
            "expiryDates",
            [],
        ),
    )

    expiries: list[date] = []

    if isinstance(
        raw_expiries,
        list,
    ):
        for value in raw_expiries:
            parsed = _parse_expiry(value)

            if parsed is not None:
                expiries.append(parsed)

    records: list[
        dict[str, Any]
    ] = []

    for item in raw_data:
        if not isinstance(
            item,
            dict,
        ):
            continue

        strike = _first_float(
            item.get("strikePrice"),
            item.get("strike"),
        )

        if strike is None:
            continue

        ce = item.get("CE")
        pe = item.get("PE")

        if not isinstance(
            ce,
            dict,
        ):
            ce = None

        if not isinstance(
            pe,
            dict,
        ):
            pe = None

        expiry = _parse_expiry(
            item.get("expiryDate")
            or item.get("expiry")
        )

        if expiry is None and ce is not None:
            expiry = _parse_expiry(
                ce.get("expiryDate")
                or ce.get("expiry")
            )

        if expiry is None and pe is not None:
            expiry = _parse_expiry(
                pe.get("expiryDate")
                or pe.get("expiry")
            )

        if expiry is None:
            row_expiry = item.get(
                "expiryDates"
            )

            if isinstance(
                row_expiry,
                list,
            ):
                for value in row_expiry:
                    parsed = _parse_expiry(value)

                    if parsed is not None:
                        expiry = parsed
                        break
            else:
                expiry = _parse_expiry(
                    row_expiry
                )

        if expiry is None:
            continue

        records.append(
            {
                "strike": strike,
                "expiry": expiry,
                "CE": ce,
                "PE": pe,
            }
        )

        if expiry not in expiries:
            expiries.append(expiry)

    return (
        underlying,
        tuple(
            sorted(
                set(expiries)
            )
        ),
        tuple(records),
    )


def _fetch_nifty_option_chain_v3(
    session: requests.Session,
) -> dict[str, Any]:
    """
    Fetch the nearest NIFTY expiry from NSE contract-info
    and then request the current option chain through v3.
    """

    contract_info = _get_json(
        session,
        (
            f"{NSE_BASE_URL}"
            "/api/option-chain-contract-info"
        ),
        params={
            "symbol": "NIFTY",
        },
    )

    raw_expiries = contract_info.get(
        "expiryDates",
        [],
    )

    if not isinstance(
        raw_expiries,
        list,
    ):
        raise LiveMarketDataError(
            "NSE contract-info returned invalid expiry data."
        )

    valid_expiries: list[
        tuple[date, Any]
    ] = []

    for value in raw_expiries:
        parsed = _parse_expiry(value)

        if parsed is not None:
            valid_expiries.append(
                (
                    parsed,
                    value,
                )
            )

    if not valid_expiries:
        raise LiveMarketDataError(
            "NSE contract-info returned no NIFTY expiries."
        )

    today = date.today()

    future_expiries = [
        item
        for item in valid_expiries
        if item[0] >= today
    ]

    selected_expiry = (
        min(
            future_expiries,
            key=lambda item: item[0],
        )
        if future_expiries
        else min(
            valid_expiries,
            key=lambda item: item[0],
        )
    )

    expiry_value = selected_expiry[1]

    return _get_json(
        session,
        (
            f"{NSE_BASE_URL}"
            "/api/option-chain-v3"
        ),
        params={
            "type": "Indices",
            "symbol": "NIFTY",
            "expiry": expiry_value,
        },
    )


def _build_option_chain(
    payload: dict[str, Any],
) -> NiftyOptionChain:
    (
        underlying,
        expiries,
        records,
    ) = _normalise_chain_records(
        payload
    )

    if not records:
        raise LiveMarketDataError(
            "NSE returned no NIFTY option-chain records."
        )

    return NiftyOptionChain(
        timestamp=datetime.now(),
        underlying_value=underlying,
        expiry_dates=expiries,
        records=records,
    )


def fetch_nifty_option_chain(
    session: requests.Session | None = None,
) -> NiftyOptionChain:
    """
    Fetch the live NIFTY option chain.

    Provider order:

        1. NSE option-chain-v3 with contract-info.
        2. Retry v3 with a completely fresh NSE session.
        3. NSE legacy option-chain-indices endpoint.

    A fresh session is deliberately created for the retry so
    stale cookies cannot poison the second attempt.

    The normalized NiftyOptionChain structure is unchanged.
    """

    errors: list[str] = []

    first_session = (
        session
        if session is not None
        else _session()
    )

    try:
        payload = _fetch_nifty_option_chain_v3(
            first_session
        )

        return _build_option_chain(
            payload
        )

    except LiveMarketDataError as exc:
        errors.append(
            f"v3 attempt 1: {exc}"
        )

    second_session = _session()

    try:
        payload = _fetch_nifty_option_chain_v3(
            second_session
        )

        return _build_option_chain(
            payload
        )

    except LiveMarketDataError as exc:
        errors.append(
            f"v3 attempt 2: {exc}"
        )

    legacy_session = _session()

    try:
        payload = _get_json(
            legacy_session,
            (
                f"{NSE_BASE_URL}"
                "/api/option-chain-indices"
            ),
            params={
                "symbol": "NIFTY",
            },
        )

        return _build_option_chain(
            payload
        )

    except LiveMarketDataError as exc:
        errors.append(
            f"legacy endpoint: {exc}"
        )

    raise LiveMarketDataError(
        "Unable to fetch NIFTY option chain from NSE. "
        + " | ".join(errors)
    )


def available_nifty_expiries(
    payload_or_chain: (
        dict[str, Any]
        | NiftyOptionChain
    ),
) -> list[date]:
    """
    Return expiries as a list for backward compatibility.
    """

    if isinstance(
        payload_or_chain,
        NiftyOptionChain,
    ):
        return list(
            payload_or_chain.expiry_dates
        )

    (
        _underlying,
        expiries,
        _records,
    ) = _normalise_chain_records(
        payload_or_chain
    )

    return list(expiries)


def nearest_nifty_expiry(
    chain: (
        NiftyOptionChain
        | dict[str, Any]
    ),
    today: date | None = None,
) -> date:
    """
    Accept either the normalized dataclass or
    the raw NSE payload.
    """

    if isinstance(
        chain,
        NiftyOptionChain,
    ):
        expiry_dates = chain.expiry_dates
    else:
        expiry_dates = tuple(
            available_nifty_expiries(
                chain
            )
        )

    current_date = (
        today
        if today is not None
        else date.today()
    )

    future_expiries = [
        expiry
        for expiry in expiry_dates
        if expiry >= current_date
    ]

    if not future_expiries:
        raise LiveMarketDataError(
            "NSE option chain contains no future NIFTY expiry."
        )

    return min(
        future_expiries
    )


def build_option_chain_snapshot(
    payload: dict[str, Any] | NiftyOptionChain | None = None,
    nifty_price: float = 0.0,
    expiry: date | None = None,
    strikes_each_side: int = 2,
    option_chain_payload: dict[str, Any] | NiftyOptionChain | None = None,
) -> OptionChainSnapshot:
    """
    Build aggregated option-chain statistics.

    Supports both parameter names:

        payload=
        option_chain_payload=

    This preserves compatibility with older callers while
    supporting the newer live-signal-engine interface.
    """

    if option_chain_payload is not None:
        payload = option_chain_payload

    if payload is None:
        raise LiveMarketDataError(
            "Option-chain payload is required."
        )

    if expiry is None:
        raise LiveMarketDataError(
            "Option-chain expiry is required."
        )

    if nifty_price <= 0:
        raise ValueError(
            "nifty_price must be positive."
        )

    if strikes_each_side < 0:
        raise ValueError(
            "strikes_each_side cannot be negative."
        )

    (
        underlying,
        _expiries,
        records,
    ) = _normalise_chain_records(
        payload
    )

    reference_price = (
        nifty_price
        if nifty_price > 0
        else underlying
    )

    strikes = sorted(
        {
            float(record["strike"])
            for record in records
            if record["expiry"] == expiry
        }
    )

    if not strikes:
        raise LiveMarketDataError(
            "No option-chain rows found "
            "for requested expiry."
        )

    atm_index = min(
        range(len(strikes)),
        key=lambda index: abs(
            strikes[index]
            - reference_price
        ),
    )

    low = max(
        0,
        atm_index - strikes_each_side,
    )

    high = min(
        len(strikes),
        atm_index
        + strikes_each_side
        + 1,
    )

    selected = set(
        strikes[low:high]
    )

    ce_oi = 0.0
    pe_oi = 0.0
    ce_oi_change = 0.0
    pe_oi_change = 0.0
    ce_volume = 0.0
    pe_volume = 0.0

    for record in records:
        if (
            record["expiry"] != expiry
            or float(record["strike"])
            not in selected
        ):
            continue

        ce = record.get("CE") or {}
        pe = record.get("PE") or {}

        if isinstance(
            ce,
            dict,
        ):
            ce_oi += _first_float(
                ce.get("openInterest")
            ) or 0.0

            ce_oi_change += _first_float(
                ce.get("changeinOpenInterest"),
                ce.get("changeInOpenInterest"),
            ) or 0.0

            ce_volume += _first_float(
                ce.get("totalTradedVolume"),
                ce.get("volume"),
            ) or 0.0

        if isinstance(
            pe,
            dict,
        ):
            pe_oi += _first_float(
                pe.get("openInterest")
            ) or 0.0

            pe_oi_change += _first_float(
                pe.get("changeinOpenInterest"),
                pe.get("changeInOpenInterest"),
            ) or 0.0

            pe_volume += _first_float(
                pe.get("totalTradedVolume"),
                pe.get("volume"),
            ) or 0.0

    return OptionChainSnapshot(
        ce_oi=ce_oi,
        pe_oi=pe_oi,
        ce_oi_change=ce_oi_change,
        pe_oi_change=pe_oi_change,
        ce_volume=ce_volume,
        pe_volume=pe_volume,
    )


def find_option_quote(
    payload: dict[str, Any] | NiftyOptionChain,
    expiry: date,
    strike: float,
    option_type: str,
):
    option_type = option_type.upper()

    if option_type not in {
        "CE",
        "PE",
    }:
        raise ValueError(
            "option_type must be CE or PE."
        )

    (
        _underlying,
        _expiries,
        records,
    ) = _normalise_chain_records(
        payload
    )

    for record in records:
        if record["expiry"] != expiry:
            continue

        if float(record["strike"]) != float(strike):
            continue

        raw_quote = record.get(
            option_type
        )

        if not isinstance(
            raw_quote,
            dict,
        ):
            raise LiveMarketDataError(
                f"{option_type} quote not found."
            )

        quote = dict(
            raw_quote
        )

        quote["timestamp"] = (
            quote.get("timestamp")
            or quote.get("lastUpdateTime")
            or datetime.now().isoformat()
        )

        quote["strike"] = strike
        quote["expiry"] = expiry

        quote["option_type"] = option_type
        quote["optionType"] = option_type

        return normalize_option_quote(
            quote
        )

    raise LiveMarketDataError(
        f"{option_type} quote not found "
        f"for {strike} / {expiry}."
    )