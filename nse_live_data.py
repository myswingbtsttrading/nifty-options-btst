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
        "Mozilla/5.0 (Linux; Android 10; K) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,"
        "image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
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
    if isinstance(value, date):
        return value

    if value is None:
        return None

    text = str(value).strip()

    formats = (
        "%d-%b-%Y",
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

    return None


def _extract_quote_from_nse_payload(
    payload: dict[str, Any],
) -> NiftyQuote:
    data = payload.get("data")

    if isinstance(data, dict):
        info = data.get("info", data)

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

    if previous_close is None:
        previous_close = price

    return NiftyQuote(
        timestamp=_parse_nse_datetime(
            timestamp
        ),
        price=price,
        previous_close=previous_close,
    )


def fetch_nifty_quote() -> NiftyQuote:
    """
    Fetch the current NIFTY 50 quote.

    Uses NSE's equity index quote endpoint instead of the
    retired/invalid quote endpoint previously used by the runner.
    """

    session = _session()

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

    last_error: Exception | None = None

    for url, params in urls:
        try:
            payload = _get_json(
                session,
                url,
                params=params,
            )

            if "allIndices" in payload:
                indices = payload.get(
                    "data",
                    []
                )

                if not isinstance(
                    indices,
                    list,
                ):
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

        except (
            LiveMarketDataError,
            requests.RequestException,
        ) as exc:
            last_error = exc

    raise LiveMarketDataError(
        "Unable to fetch NIFTY 50 quote from NSE."
        + (
            f" Last error: {last_error}"
            if last_error
            else ""
        )
    )


def _normalise_chain_records(
    payload: dict[str, Any],
) -> tuple[
    float,
    tuple[date, ...],
    tuple[dict[str, Any], ...],
]:
    records: list[dict[str, Any]] = []

    data = payload.get("records", {})

    if not isinstance(data, dict):
        raise LiveMarketDataError(
            "NSE option-chain payload is invalid."
        )

    underlying = _first_float(
        data.get("underlyingValue"),
    )

    if underlying is None:
        underlying = 0.0

    raw_expiries = data.get(
        "expiryDates",
        [],
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

    raw_data = data.get(
        "data",
        [],
    )

    if not isinstance(
        raw_data,
        list,
    ):
        raw_data = []

    for item in raw_data:
        if not isinstance(
            item,
            dict,
        ):
            continue

        strike = _first_float(
            item.get("strikePrice"),
        )

        expiry = _parse_expiry(
            item.get("expiryDate")
        )

        if strike is None or expiry is None:
            continue

        records.append(
            {
                "strike": strike,
                "expiry": expiry,
                "CE": item.get("CE"),
                "PE": item.get("PE"),
            }
        )

    return (
        underlying,
        tuple(sorted(set(expiries))),
        tuple(records),
    )


def fetch_nifty_option_chain() -> NiftyOptionChain:
    session = _session()

    payload = _get_json(
        session,
        f"{NSE_BASE_URL}/api/option-chain-indices",
        params={
            "symbol": "NIFTY",
        },
    )

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


def nearest_nifty_expiry(
    chain: NiftyOptionChain,
    today: date | None = None,
) -> date:
    current_date = (
        today
        if today is not None
        else date.today()
    )

    future_expiries = [
        expiry
        for expiry in chain.expiry_dates
        if expiry >= current_date
    ]

    if not future_expiries:
        raise LiveMarketDataError(
            "NSE option chain contains no future NIFTY expiry."
        )

    return min(future_expiries)


def build_option_chain_snapshot(
    payload: dict[str, Any],
    nifty_price: float,
    expiry: date,
    strikes_each_side: int = 2,
) -> OptionChainSnapshot:
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
            "No strikes found for requested expiry."
        )

    atm_index = min(
        range(len(strikes)),
        key=lambda index: abs(
            strikes[index] - reference_price
        ),
    )

    low = max(
        0,
        atm_index - strikes_each_side,
    )

    high = min(
        len(strikes),
        atm_index + strikes_each_side + 1,
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

        if isinstance(ce, dict):
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

        if isinstance(pe, dict):
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
    payload: dict[str, Any],
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

    _underlying, _expiries, records = (
        _normalise_chain_records(
            payload
        )
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
                f"No {option_type} quote available."
            )

        quote = dict(raw_quote)

        quote["timestamp"] = (
            quote.get("timestamp")
            or quote.get("lastUpdateTime")
            or datetime.now().isoformat()
        )

        quote["strike"] = strike
        quote["expiry"] = expiry
        quote["optionType"] = option_type

        return normalize_option_quote(
            quote
        )

    raise LiveMarketDataError(
        f"No {option_type} quote found for "
        f"{strike} / {expiry}."
    )