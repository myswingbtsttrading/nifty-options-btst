from __future__ import annotations

import io
import re
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import BinaryIO, Dict, Iterable, List, Optional


OPTION_FILENAME_PATTERN = re.compile(
    r"^(CE|PE)\s+(\d+(?:\.\d+)?)\.txt$",
    re.IGNORECASE,
)

MONTHLY_ZIP_PATTERN = re.compile(
    r"^(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+(\d{4})\.zip$",
    re.IGNORECASE,
)

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def parse_option_filename(
    filename: str,
) -> Optional[Dict[str, object]]:
    name = Path(filename).name.strip()

    match = OPTION_FILENAME_PATTERN.match(name)

    if not match:
        return None

    return {
        "option_type": match.group(1).upper(),
        "strike": float(match.group(2)),
    }


def parse_monthly_zip_filename(
    filename: str,
) -> Optional[date]:
    """
    Convert a monthly archive name such as:

        November 2017.zip

    into the corresponding monthly expiry date.
    """

    name = Path(filename).name.strip()

    match = MONTHLY_ZIP_PATTERN.match(name)

    if not match:
        return None

    month_name = match.group(1).lower()
    year = int(match.group(2))
    month = MONTHS[month_name]

    from expiry_calendar import standard_monthly_expiry

    return standard_monthly_expiry(
        year,
        month,
    )


def parse_option_line(
    line: str,
    option_type: str,
    strike: float,
    expiry: Optional[date] = None,
) -> Optional[Dict[str, object]]:
    line = line.strip()

    if not line:
        return None

    parts = [
        part.strip()
        for part in line.split(",")
    ]

    if len(parts) < 8:
        return None

    try:
        timestamp = datetime.strptime(
            f"{parts[1]} {parts[2]}",
            "%Y/%m/%d %H:%M",
        )

        return {
            "timestamp": timestamp,
            "option_type": option_type.upper(),
            "strike": float(strike),
            "expiry": expiry,
            "open": float(parts[3]),
            "high": float(parts[4]),
            "low": float(parts[5]),
            "close": float(parts[6]),
            "volume": float(parts[7]),
        }

    except (
        ValueError,
        TypeError,
    ):
        return None


def parse_option_text(
    text: str,
    filename: str,
    expiry: Optional[date] = None,
) -> List[Dict[str, object]]:
    metadata = parse_option_filename(
        filename
    )

    if metadata is None:
        return []

    option_type = str(
        metadata["option_type"]
    )

    strike = float(
        metadata["strike"]
    )

    rows: List[Dict[str, object]] = []

    for line in text.splitlines():
        row = parse_option_line(
            line,
            option_type,
            strike,
            expiry,
        )

        if row is not None:
            rows.append(row)

    return rows


def load_option_file(
    file_obj: BinaryIO,
    filename: str,
    expiry: Optional[date] = None,
) -> List[Dict[str, object]]:
    raw = file_obj.read()

    text = raw.decode(
        "utf-8",
        errors="replace",
    )

    return parse_option_text(
        text,
        filename,
        expiry,
    )


def iter_option_files(
    archive: zipfile.ZipFile,
) -> Iterable[str]:
    for filename in archive.namelist():

        if filename.endswith("/"):
            continue

        if parse_option_filename(
            Path(filename).name
        ) is not None:
            yield filename


def load_month_zip_bytes(
    data: bytes,
    expiry: Optional[date] = None,
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []

    with zipfile.ZipFile(
        io.BytesIO(data)
    ) as archive:

        for filename in iter_option_files(
            archive
        ):
            with archive.open(
                filename
            ) as file_obj:

                rows.extend(
                    load_option_file(
                        file_obj,
                        Path(filename).name,
                        expiry,
                    )
                )

    return rows


def load_month_zip(
    path: str | Path,
    expiry: Optional[date] = None,
) -> List[Dict[str, object]]:
    with open(
        path,
        "rb",
    ) as file_obj:
        return load_month_zip_bytes(
            file_obj.read(),
            expiry,
        )


def iter_monthly_zip_files(
    archive: zipfile.ZipFile,
) -> Iterable[str]:
    for filename in archive.namelist():

        if filename.endswith("/"):
            continue

        if parse_monthly_zip_filename(
            Path(filename).name
        ) is not None:
            yield filename


def load_year_zip(
    path: str | Path,
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []

    with zipfile.ZipFile(
        path
    ) as year_archive:

        for filename in iter_monthly_zip_files(
            year_archive
        ):
            expiry = parse_monthly_zip_filename(
                Path(filename).name
            )

            monthly_bytes = year_archive.read(
                filename
            )

            rows.extend(
                load_month_zip_bytes(
                    monthly_bytes,
                    expiry,
                )
            )

    return rows


def filter_rows_by_date(
    rows: List[Dict[str, object]],
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> List[Dict[str, object]]:
    filtered: List[Dict[str, object]] = []

    for row in rows:
        timestamp = row.get(
            "timestamp"
        )

        if not isinstance(
            timestamp,
            datetime,
        ):
            continue

        if (
            start is not None
            and timestamp < start
        ):
            continue

        if (
            end is not None
            and timestamp > end
        ):
            continue

        filtered.append(row)

    return filtered


def find_price_at_or_before(
    rows: List[Dict[str, object]],
    timestamp: datetime,
) -> Optional[Dict[str, object]]:
    candidates = [
        row
        for row in rows
        if isinstance(
            row.get("timestamp"),
            datetime,
        )
        and row["timestamp"] <= timestamp
    ]

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda row: row["timestamp"],
    )


def find_price_at_or_after(
    rows: List[Dict[str, object]],
    timestamp: datetime,
) -> Optional[Dict[str, object]]:
    candidates = [
        row
        for row in rows
        if isinstance(
            row.get("timestamp"),
            datetime,
        )
        and row["timestamp"] >= timestamp
    ]

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda row: row["timestamp"],
    )


def filter_contract(
    rows: List[Dict[str, object]],
    option_type: str,
    strike: float,
    expiry: Optional[date] = None,
) -> List[Dict[str, object]]:
    normalized_type = option_type.upper()

    return [
        row
        for row in rows
        if str(
            row.get("option_type", "")
        ).upper()
        == normalized_type
        and float(
            row.get("strike", 0)
        ) == float(strike)
        and (
            expiry is None
            or row.get("expiry") == expiry
        )
    ]