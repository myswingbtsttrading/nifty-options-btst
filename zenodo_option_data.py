from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from historical_option_loader import (
    filter_contract,
    find_price_at_or_after,
    find_price_at_or_before,
    load_month_zip_bytes,
    parse_monthly_zip_filename,
)

import zipfile


OptionRow = Dict[str, object]


def load_month_contract(
    year_zip_path: str | Path,
    monthly_zip_name: str,
    option_type: str,
    strike: float,
) -> List[OptionRow]:
    """
    Load one CE/PE strike from a nested Zenodo yearly archive.

    Structure:

        NiftyOptions YYYY.zip
            └── November YYYY.zip
                └── PE 10050.txt
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
        year_zip_path
    ) as year_archive:

        matching_name = None

        for name in year_archive.namelist():
            if Path(name).name.lower() == (
                Path(monthly_zip_name).name.lower()
            ):
                matching_name = name
                break

        if matching_name is None:
            raise FileNotFoundError(
                f"Monthly ZIP not found inside "
                f"{year_zip_path.name}: "
                f"{monthly_zip_name}"
            )

        monthly_bytes = year_archive.read(
            matching_name
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
            f"{option_type.upper()} {float(strike):g} "
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
    Return the latest available contract observation
    at or before the requested entry time.
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
        if row["timestamp"].date()
        == entry_date
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
    Return the first available contract observation
    at or after the requested exit time.
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
        if row["timestamp"].date()
        == exit_date
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

    Returns the contract metadata plus the selected
    entry and exit observations.
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