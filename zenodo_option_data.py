from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional
import zipfile

from historical_option_loader import (
    filter_contract,
    find_price_at_or_after,
    find_price_at_or_before,
    load_month_zip_bytes,
    parse_monthly_zip_filename,
)


OptionRow = Dict[str, object]


def _find_member_case_insensitive(
    archive: zipfile.ZipFile,
    filename: str,
) -> str | None:
    target = Path(filename).name.lower()

    for name in archive.namelist():
        if Path(name).name.lower() == target:
            return name

    return None


def load_month_contract(
    year_zip_path: str | Path,
    monthly_zip_name: str,
    option_type: str,
    strike: float,
) -> List[OptionRow]:
    """
    Load one CE/PE strike from a yearly Zenodo archive.

    Expected structure:

        NiftyOptions 2017.zip
            ├── November 2017.zip
            │     └── PE 10050.txt
            └── ...

    The monthly archive itself contains the historical
    option-contract text files.
    """

    monthly_expiry = parse_monthly_zip_filename(
        monthly_zip_name
    )

    if monthly_expiry is None:
        raise ValueError(
            f"Invalid monthly ZIP name: "
            f"{monthly_zip_name}"
        )

    year_zip_path = Path(year_zip_path)

    if not year_zip_path.exists():
        raise FileNotFoundError(
            f"Year ZIP not found: "
            f"{year_zip_path}"
        )

    with zipfile.ZipFile(
        year_zip_path,
        "r",
    ) as year_archive:

        member_name = _find_member_case_insensitive(
            year_archive,
            monthly_zip_name,
        )

        if member_name is None:
            raise FileNotFoundError(
                f"Monthly ZIP not found inside "
                f"{year_zip_path.name}: "
                f"{monthly_zip_name}"
            )

        monthly_bytes = year_archive.read(
            member_name
        )

    rows = load_month_zip_bytes(
        monthly_bytes,
        monthly_expiry,
    )

    contract_rows = filter_contract(
        rows,
        option_type,
        strike,
        monthly_expiry,
    )

    if not contract_rows:
        raise ValueError(
            "Option contract not found: "
            f"{option_type.upper()} "
            f"{float(strike):g} "
            f"expiry {monthly_expiry}"
        )

    return sorted(
        contract_rows,
        key=lambda row: row["timestamp"],
    )


def get_entry_quote(
    contract_rows: List[OptionRow],
    entry_date: date,
    entry_time: str = "15:00",
) -> Optional[OptionRow]:
    """
    Return the latest observation at or before the
    requested entry time.
    """

    entry_clock = datetime.strptime(
        entry_time,
        "%H:%M",
    ).time()

    requested = datetime.combine(
        entry_date,
        entry_clock,
    )

    day_rows = [
        row
        for row in contract_rows
        if row["timestamp"].date() == entry_date
    ]

    return find_price_at_or_before(
        day_rows,
        requested,
    )


def get_exit_quote(
    contract_rows: List[OptionRow],
    exit_date: date,
    exit_time: str = "09:15",
) -> Optional[OptionRow]:
    """
    Return the first observation at or after the
    requested exit time.
    """

    exit_clock = datetime.strptime(
        exit_time,
        "%H:%M",
    ).time()

    requested = datetime.combine(
        exit_date,
        exit_clock,
    )

    day_rows = [
        row
        for row in contract_rows
        if row["timestamp"].date() == exit_date
    ]

    return find_price_at_or_after(
        day_rows,
        requested,
    )


def load_btst_contract(
    year_zip_path: str | Path,
    monthly_zip_name: str,
    option_type: str,
    strike: float,
    entry_date: date,
    exit_date: date,
    entry_time: str = "15:00",
    exit_time: str = "09:15",
) -> Dict[str, object]:
    """
    Load one complete historical BTST contract.
    """

    rows = load_month_contract(
        year_zip_path=year_zip_path,
        monthly_zip_name=monthly_zip_name,
        option_type=option_type,
        strike=strike,
    )

    entry = get_entry_quote(
        rows,
        entry_date,
        entry_time,
    )

    exit_ = get_exit_quote(
        rows,
        exit_date,
        exit_time,
    )

    return {
        "option_type": option_type.upper(),
        "strike": float(strike),
        "expiry": parse_monthly_zip_filename(
            monthly_zip_name
        ),
        "entry": entry,
        "exit": exit_,
        "entry_date": entry_date,
        "exit_date": exit_date,
        "entry_time": entry_time,
        "exit_time": exit_time,
    }