from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Dict, Iterable, List, Optional


OPTION_FILENAME_PATTERN = re.compile(
    r"^(CE|PE)\s+(\d+(?:\.\d+)?)\.txt$",
    re.IGNORECASE,
)


def parse_option_filename(
    filename: str,
) -> Optional[Dict[str, object]]:
    """
    Parse filenames such as:

        CE 8250.txt
        PE 18000.txt

    Returns option type and strike.
    """

    name = Path(filename).name.strip()

    match = OPTION_FILENAME_PATTERN.match(name)

    if not match:
        return None

    option_type = match.group(1).upper()
    strike = float(match.group(2))

    return {
        "option_type": option_type,
        "strike": strike,
    }


def parse_option_line(
    line: str,
    option_type: str,
    strike: float,
) -> Optional[Dict[str, object]]:
    """
    Parse one Zenodo option-data row.

    Expected format:

        CE 8250,2016/12/22,11:08,
        52.15,52.15,52.15,52.15,300

    Columns:

        symbol
        date
        time
        open
        high
        low
        close
        volume
    """

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
            "expiry": None,
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
) -> List[Dict[str, object]]:
    """
    Parse a complete Zenodo option text file.
    """

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
        )

        if row is not None:
            rows.append(row)

    return rows


def load_option_file(
    file_obj: BinaryIO,
    filename: str,
) -> List[Dict[str, object]]:
    """
    Read one option text file from a ZIP archive.
    """

    raw = file_obj.read()

    text = raw.decode(
        "utf-8",
        errors="replace",
    )

    return parse_option_text(
        text,
        filename,
    )


def iter_option_files(
    archive: zipfile.ZipFile,
) -> Iterable[str]:
    """
    Return valid option files from a ZIP archive.
    """

    for filename in archive.namelist():

        if filename.endswith("/"):
            continue

        if parse_option_filename(
            filename
        ) is not None:
            yield filename


def load_month_zip_bytes(
    data: bytes,
) -> List[Dict[str, object]]:
    """
    Load one monthly ZIP from bytes.

    The monthly ZIP contains files such as:

        CE 8250.txt
        PE 8250.txt
    """

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
                        filename,
                    )
                )

    return rows


def load_month_zip(
    path: str | Path,
) -> List[Dict[str, object]]:
    """
    Load one monthly ZIP from disk.
    """

    with open(
        path,
        "rb",
    ) as file_obj:

        return load_month_zip_bytes(
            file_obj.read()
        )


def load_year_zip(
    path: str | Path,
) -> List[Dict[str, object]]:
    """
    Load a Zenodo yearly ZIP.

    Example:

        NiftyOptions 2017.zip

    The yearly ZIP contains:

        January 2017.zip
        February 2017.zip
        ...
    """

    rows: List[Dict[str, object]] = []

    with zipfile.ZipFile(
        path
    ) as year_archive:

        for filename in year_archive.namelist():

            if not filename.lower().endswith(
                ".zip"
            ):
                continue

            monthly_bytes = (
                year_archive.read(filename)
            )

            rows.extend(
                load_month_zip_bytes(
                    monthly_bytes
                )
            )

    return rows


def filter_rows_by_date(
    rows: List[Dict[str, object]],
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> List[Dict[str, object]]:
    """
    Filter normalized option rows by timestamp.
    """

    filtered: List[
        Dict[str, object]
    ] = []

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
    """
    Find the latest available observation
    at or before the requested timestamp.
    """

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
    """
    Find the first available observation
    at or after the requested timestamp.
    """

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
) -> List[Dict[str, object]]:
    """
    Select one option contract by CE/PE and strike.
    """

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
        )
        == float(strike)
    ]