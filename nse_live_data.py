from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Optional

import requests

from live_market_data import (
    LiveMarketDataError,
    LiveOptionQuote,
    LiveUnderlyingQuote,
    normalize_option_quote,
    normalize_underlying_quote,
)
from option_chain_confirmation import (
    OptionChainSnapshot,
)


NSE_BASE_URL = "https://www.nseindia.com"

NSE_INDEX_QUOTE_URL = (
    f"{NSE_BASE_URL}/api/equity-stockIndices"
)

NSE_OPTION_CHAIN_URL = (
    f"{NSE_BASE_URL}/api/option-chain-indices"
)

YAHOO_CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/^NSEI"
)


@dataclass(frozen=True)
class NiftyIndicators:
    ema20: float
    ema50: float
    rsi: float
    vwap: float


@dataclass(frozen=True)
class NiftyLiveSnapshot:
    quote: LiveUnderlyingQuote
    indicators: NiftyIndicators
    option_chain: OptionChainSnapshot


def _number(
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

    if result < 0:
        raise LiveMarketDataError(
            f"{field} cannot be negative."
        )

    return result


def _request_json(
    session: requests.Session,
    url: str,
    params: Optional[Mapping[str, Any]] = None,
) -> Any:
    try:
        response = session.get(
            url,
            params=params,
            timeout=15,
        )
    except requests.RequestException as exc:
        raise LiveMarketDataError(
            f"Live market-data request failed: {exc}"
        ) from exc

    if response.status_code != 200:
        raise LiveMarketDataError(
            "Live market-data request returned "
            f"HTTP {response.status_code}."
        )

    try:
        return response.json()
    except ValueError as exc:
        raise LiveMarketDataError(
            "Live market-data response was not JSON."
        ) from exc


def _extract_quote_payload(
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    data = payload.get("data")

    if isinstance(data, list) and data:
        first = data[0]

        if isinstance(first, Mapping):
            return first

    if isinstance(data, Mapping):
        return data

    if "priceInfo" in payload:
        return payload

    raise LiveMarketDataError(
        "NIFTY quote response has an unexpected structure."
    )


def _extract_price(
    payload: Mapping[str, Any],
) -> float:
    price_info = payload.get(
        "priceInfo",
        {},
    )

    if not isinstance(
        price_info,
        Mapping,
    ):
        price_info = {}

    value = (
        price_info.get("lastPrice")
        or payload.get("lastPrice")
        or payload.get("ltp")
        or payload.get("price")
    )

    if value is None:
        raise LiveMarketDataError(
            "NIFTY quote does not contain last price."
        )

    return float(value)


def _extract_previous_close(
    payload: Mapping[str, Any],
) -> float:
    price_info = payload.get(
        "priceInfo",
        {},
    )

    if not isinstance(
        price_info,
        Mapping,
    ):
        price_info = {}

    value = (
        price_info.get("previousClose")
        or payload.get("previousClose")
        or payload.get("previous_close")
    )

    if value is None:
        raise LiveMarketDataError(
            "NIFTY quote does not contain previous close."
        )

    return float(value)


def _extract_timestamp(
    payload: Mapping[str, Any],
) -> datetime:
    value = (
        payload.get("timestamp")
        or payload.get("lastUpdateTime")
        or payload.get("datetime")
    )

    if value is None:
        return datetime.now()

    text = str(value).strip()

    formats = (
        "%d-%b-%Y %H:%M:%S",
        "%d-%b-%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
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


def fetch_nifty_quote(
    session: Optional[requests.Session] = None,
) -> LiveUnderlyingQuote:
    """
    Fetch the current NIFTY 50 index quote from NSE.
    """

    client = (
        session
        if session is not None
        else requests.Session()
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10) "
            "AppleWebKit/537.36 "
            "Chrome/151.0 Mobile Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"{NSE_BASE_URL}/",
        "Connection": "keep-alive",
    }

    try:
        client.get(
            NSE_BASE_URL,
            headers=headers,
            timeout=15,
        )
    except requests.RequestException as exc:
        raise LiveMarketDataError(
            f"Unable to establish NSE session: {exc}"
        ) from exc

    try:
        response = client.get(
            NSE_INDEX_QUOTE_URL,
            params={
                "index": "NIFTY 50",
            },
            headers=headers,
            timeout=15,
        )
    except requests.RequestException as exc:
        raise LiveMarketDataError(
            f"Unable to fetch NIFTY quote: {exc}"
        ) from exc

    if response.status_code != 200:
        raise LiveMarketDataError(
            "NSE NIFTY quote returned "
            f"HTTP {response.status_code}."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise LiveMarketDataError(
            "NSE NIFTY quote was not valid JSON."
        ) from exc

    quote_payload = _extract_quote_payload(
        payload
    )

    return normalize_underlying_quote(
        {
            "timestamp": _extract_timestamp(
                quote_payload
            ),
            "price": _extract_price(
                quote_payload
            ),
            "previous_close": _extract_previous_close(
                quote_payload
            ),
        }
    )


def fetch_nifty_option_chain(
    session: Optional[requests.Session] = None,
) -> Mapping[str, Any]:
    """
    Fetch the complete current NIFTY option chain
    from NSE.
    """

    client = (
        session
        if session is not None
        else requests.Session()
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10) "
            "AppleWebKit/537.36 "
            "Chrome/151.0 Mobile Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": (
            f"{NSE_BASE_URL}/option-chain"
        ),
        "Connection": "keep-alive",
    }

    try:
        client.get(
            NSE_BASE_URL,
            headers=headers,
            timeout=15,
        )

        response = client.get(
            NSE_OPTION_CHAIN_URL,
            params={
                "symbol": "NIFTY",
            },
            headers=headers,
            timeout=15,
        )
    except requests.RequestException as exc:
        raise LiveMarketDataError(
            f"Unable to fetch NIFTY option chain: {exc}"
        ) from exc

    if response.status_code != 200:
        raise LiveMarketDataError(
            "NSE option-chain request returned "
            f"HTTP {response.status_code}."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise LiveMarketDataError(
            "NSE option-chain response was not valid JSON."
        ) from exc

    if not isinstance(
        payload,
        Mapping,
    ):
        raise LiveMarketDataError(
            "NSE option-chain response has an "
            "unexpected structure."
        )

    return payload


def available_nifty_expiries(
    option_chain_payload: Mapping[str, Any],
) -> list[date]:
    records = option_chain_payload.get(
        "records",
        {},
    )

    if not isinstance(
        records,
        Mapping,
    ):
        raise LiveMarketDataError(
            "Option-chain records are missing."
        )

    raw_expiries = records.get(
        "expiryDates",
        [],
    )

    result: list[date] = []

    for value in raw_expiries:
        text = str(value).strip()

        for fmt in (
            "%d-%b-%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
        ):
            try:
                parsed = datetime.strptime(
                    text,
                    fmt,
                ).date()

                result.append(parsed)
                break
            except ValueError:
                continue

    if not result:
        raise LiveMarketDataError(
            "No valid NIFTY option expiries were found."
        )

    return sorted(
        set(result)
    )


def nearest_nifty_expiry(
    option_chain_payload: Mapping[str, Any],
    today: Optional[date] = None,
) -> date:
    current_date = (
        today
        if today is not None
        else date.today()
    )

    expiries = available_nifty_expiries(
        option_chain_payload
    )

    future = [
        expiry
        for expiry in expiries
        if expiry >= current_date
    ]

    if not future:
        raise LiveMarketDataError(
            "No current or future NIFTY expiry found."
        )

    return future[0]


def _rows(
    payload: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    records = payload.get(
        "records",
        {},
    )

    if not isinstance(
        records,
        Mapping,
    ):
        raise LiveMarketDataError(
            "Option-chain records are invalid."
        )

    rows = records.get(
        "data",
        [],
    )

    if not isinstance(
        rows,
        list,
    ):
        raise LiveMarketDataError(
            "Option-chain data is invalid."
        )

    return [
        row
        for row in rows
        if isinstance(
            row,
            Mapping,
        )
    ]


def build_option_chain_snapshot(
    option_chain_payload: Mapping[str, Any],
    nifty_price: float,
    expiry: date,
    strikes_each_side: int = 5,
) -> OptionChainSnapshot:
    """
    Aggregate CE/PE OI, OI change and volume around ATM.
    """

    if nifty_price <= 0:
        raise ValueError(
            "nifty_price must be positive."
        )

    if strikes_each_side < 0:
        raise ValueError(
            "strikes_each_side cannot be negative."
        )

    rows = _rows(
        option_chain_payload
    )

    eligible = []

    for row in rows:
        row_expiry = row.get(
            "expiryDate"
        )

        if row_expiry is None:
            continue

        try:
            parsed_expiry = datetime.strptime(
                str(row_expiry).strip(),
                "%d-%b-%Y",
            ).date()
        except ValueError:
            continue

        if parsed_expiry != expiry:
            continue

        strike = row.get(
            "strikePrice"
        )

        if strike is None:
            continue

        eligible.append(
            (
                float(strike),
                row,
            )
        )

    if not eligible:
        raise LiveMarketDataError(
            "No option-chain rows found for "
            f"expiry {expiry}."
        )

    eligible.sort(
        key=lambda item: abs(
            item[0] - nifty_price
        )
    )

    selected = eligible[
        : (1 + 2 * strikes_each_side)
    ]

    ce_oi = 0.0
    pe_oi = 0.0
    ce_oi_change = 0.0
    pe_oi_change = 0.0
    ce_volume = 0.0
    pe_volume = 0.0

    for _, row in selected:
        ce = row.get(
            "CE"
        )

        pe = row.get(
            "PE"
        )

        if isinstance(
            ce,
            Mapping,
        ):
            ce_oi += _number(
                ce.get("openInterest", 0),
                "CE open interest",
            )

            ce_oi_change += _number(
                ce.get(
                    "changeinOpenInterest",
                    0,
                ),
                "CE OI change",
            )

            ce_volume += _number(
                ce.get(
                    "totalTradedVolume",
                    0,
                ),
                "CE volume",
            )

        if isinstance(
            pe,
            Mapping,
        ):
            pe_oi += _number(
                pe.get("openInterest", 0),
                "PE open interest",
            )

            pe_oi_change += _number(
                pe.get(
                    "changeinOpenInterest",
                    0,
                ),
                "PE OI change",
            )

            pe_volume += _number(
                pe.get(
                    "totalTradedVolume",
                    0,
                ),
                "PE volume",
            )

    return OptionChainSnapshot(
        ce_oi=ce_oi,
        pe_oi=pe_oi,
        ce_oi_change=ce_oi_change,
        pe_oi_change=pe_oi_change,
        ce_volume=ce_volume,
        pe_volume=pe_volume,
    )


def find_option_quote(
    option_chain_payload: Mapping[str, Any],
    expiry: date,
    strike: float,
    option_type: str,
) -> LiveOptionQuote:
    normalized_type = option_type.upper()

    if normalized_type not in {
        "CE",
        "PE",
    }:
        raise ValueError(
            "option_type must be CE or PE."
        )

    for row in _rows(
        option_chain_payload
    ):
        try:
            row_expiry = datetime.strptime(
                str(
                    row.get(
                        "expiryDate"
                    )
                ).strip(),
                "%d-%b-%Y",
            ).date()
        except (
            TypeError,
            ValueError,
        ):
            continue

        if row_expiry != expiry:
            continue

        try:
            row_strike = float(
                row.get(
                    "strikePrice"
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if row_strike != float(strike):
            continue

        leg = row.get(
            normalized_type
        )

        if not isinstance(
            leg,
            Mapping,
        ):
            continue

        price = (
            leg.get("lastPrice")
            or leg.get("close")
        )

        if price is None:
            continue

        timestamp = (
            leg.get("timestamp")
            or option_chain_payload.get(
                "records",
                {},
            ).get(
                "timestamp",
                datetime.now().isoformat(),
            )
        )

        return normalize_option_quote(
            {
                "timestamp": timestamp,
                "expiry": expiry,
                "strike": strike,
                "option_type": normalized_type,
                "price": price,
            }
        )

    raise LiveMarketDataError(
        "Requested NIFTY option quote was not "
        "found in the live option chain."
    )