import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_UNDERLYING_COLUMNS = {
    "timestamp",
    "close",
}

REQUIRED_OPTION_COLUMNS = {
    "timestamp",
    "expiry",
    "strike",
    "option_type",
    "close",
}


def _read_csv(
    path: str | Path,
) -> List[Dict[str, str]]:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Data file not found: {file_path}"
        )

    with file_path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(
                f"CSV has no header: {file_path}"
            )

        return list(reader)


def _parse_timestamp(value: str) -> datetime:
    value = value.strip()

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
    )

    for fmt in formats:
        try:
            return datetime.strptime(
                value,
                fmt,
            )
        except ValueError:
            continue

    raise ValueError(
        f"Unsupported timestamp: {value}"
    )


def load_underlying_data(
    path: str | Path,
) -> List[Dict[str, Any]]:
    rows = _read_csv(path)

    if not rows:
        return []

    missing = (
        REQUIRED_UNDERLYING_COLUMNS
        - set(rows[0].keys())
    )

    if missing:
        raise ValueError(
            "Underlying CSV missing columns: "
            + ", ".join(sorted(missing))
        )

    result = []

    for row in rows:
        result.append(
            {
                "timestamp": _parse_timestamp(
                    row["timestamp"]
                ),
                "close": float(row["close"]),
            }
        )

    result.sort(
        key=lambda item: item["timestamp"]
    )

    return result


def load_option_data(
    path: str | Path,
) -> List[Dict[str, Any]]:
    rows = _read_csv(path)

    if not rows:
        return []

    missing = (
        REQUIRED_OPTION_COLUMNS
        - set(rows[0].keys())
    )

    if missing:
        raise ValueError(
            "Options CSV missing columns: "
            + ", ".join(sorted(missing))
        )

    result = []

    for row in rows:
        result.append(
            {
                "timestamp": _parse_timestamp(
                    row["timestamp"]
                ),
                "expiry": row["expiry"].strip(),
                "strike": float(row["strike"]),
                "option_type": (
                    row["option_type"]
                    .strip()
                    .upper()
                ),
                "close": float(row["close"]),
            }
        )

    result.sort(
        key=lambda item: item["timestamp"]
    )

    return result