from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping

from data_loader import (
    load_option_data,
    load_underlying_data,
)


class DataProviderError(ValueError):
    """Raised when provider data cannot be normalized."""


def _first_present(
    row: Mapping[str, Any],
    names: tuple[str, ...],
) -> Any:
    for name in names:
        if name in row and row[name] not in (
            None,
            "",
        ):
            return row[name]

    return None


def _parse_timestamp(
    value: Any,
) -> datetime:
    if isinstance(value, datetime):
        return value

    if value is None:
        raise DataProviderError(
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

    raise DataProviderError(
        f"Unsupported timestamp: {text}"
    )


def _float_value(
    value: Any,
    field_name: str,
) -> float:
    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise DataProviderError(
            f"Invalid {field_name}: {value}"
        ) from exc


def normalize_underlying_row(
    row: Mapping[str, Any],
) -> Dict[str, Any]:
    timestamp = _first_present(
        row,
        (
            "timestamp",
            "datetime",
            "date_time",
            "DateTime",
        ),
    )

    close = _first_present(
        row,
        (
            "close",
            "Close",
            "close_price",
            "ClosePrice",
        ),
    )

    if timestamp is None:
        raise DataProviderError(
            "Underlying row has no timestamp."
        )

    if close is None:
        raise DataProviderError(
            "Underlying row has no close price."
        )

    return {
        "timestamp": _parse_timestamp(
            timestamp
        ),
        "close": _float_value(
            close,
            "underlying close",
        ),
    }


def normalize_option_row(
    row: Mapping[str, Any],
) -> Dict[str, Any]:
    timestamp = _first_present(
        row,
        (
            "timestamp",
            "datetime",
            "date_time",
            "DateTime",
        ),
    )

    expiry = _first_present(
        row,
        (
            "expiry",
            "expiry_date",
            "Expiry",
            "ExpiryDate",
        ),
    )

    strike = _first_present(
        row,
        (
            "strike",
            "strike_price",
            "Strike",
            "StrikePrice",
        ),
    )

    option_type = _first_present(
        row,
        (
            "option_type",
            "optiontype",
            "type",
            "OptionType",
        ),
    )

    close = _first_present(
        row,
        (
            "close",
            "Close",
            "close_price",
            "ClosePrice",
            "last_price",
            "LastPrice",
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

    if close is None:
        missing.append("close")

    if missing:
        raise DataProviderError(
            "Option row missing fields: "
            + ", ".join(missing)
        )

    normalized_type = str(
        option_type
    ).strip().upper()

    if normalized_type not in {
        "CE",
        "PE",
    }:
        raise DataProviderError(
            f"Unsupported option type: "
            f"{normalized_type}"
        )

    return {
        "timestamp": _parse_timestamp(
            timestamp
        ),
        "expiry": str(expiry).strip(),
        "strike": _float_value(
            strike,
            "strike",
        ),
        "option_type": normalized_type,
        "close": _float_value(
            close,
            "option close",
        ),
    }


def normalize_underlying_data(
    rows: List[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    result = [
        normalize_underlying_row(row)
        for row in rows
    ]

    result.sort(
        key=lambda row: row["timestamp"]
    )

    return result


def normalize_option_data(
    rows: List[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    result = [
        normalize_option_row(row)
        for row in rows
    ]

    result.sort(
        key=lambda row: row["timestamp"]
    )

    return result


def load_provider_underlying_csv(
    path: str | Path,
) -> List[Dict[str, Any]]:
    return load_underlying_data(path)


def load_provider_option_csv(
    path: str | Path,
) -> List[Dict[str, Any]]:
    return load_option_data(path)