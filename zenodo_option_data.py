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
from release_asset_resolver import find_year_assets
from split_archive_loader import merge_year_release_assets


OptionRow = Dict[str, object]


def _load_year_archive_bytes(
    release_dir: str | Path,
    year: int,
) -> bytes:
    """
    Resolve all release ZIP assets for a year and expose
    them as one logical ZIP archive.

    This supports both:

        NiftyOptions 2017.zip

    and split assets such as:

        NiftyOptions 2017091.zip
    """

    assets = find_year_assets(
        release_dir,
        year,
    )

    if not assets:
        raise FileNotFoundError(
            f"No ZIP release assets found for {year}"
        )

    return merge_year_release_assets(
        [
            asset.path
            for asset in assets
        ]
    )


def load_month_contract_from_release(
    release_dir: str | Path,
    year: int,
    monthly_zip_name: str,
    option_type: str,
    strike: float,
) -> List[OptionRow]:
    """
    Load a contract directly from the release assets
    for a given year.
    """

    monthly_expiry = parse_monthly_zip_filename(
        monthly_zip_name
    )

    if monthly_expiry is None:
        raise ValueError(
            f"Invalid monthly ZIP name: "
            f"{monthly_zip_name}"
        )

    archive_bytes = _load_year_archive_bytes(
        release_dir,
        year,
    )

    rows = load_month_zip_bytes(
        archive_bytes,
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


def load_btst_contract_from_release(
    release_dir: str | Path,
    year: int,
    monthly_zip_name: str,
    option_type: str,
    strike: float,
    entry_date: date,
    exit_date: date,
    entry_time: str = "15:00",
    exit_time: str = "09:15",
) -> Dict[str, object]:
    """
    Load one complete BTST contract directly from the
    GitHub Release asset set.
    """

    rows = load_month_contract_from_release(
        release_dir=release_dir,
        year=year,
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

    if entry is None:
        raise ValueError(
            "No entry quote found for "
            f"{entry_date} {entry_time}"
        )

    if exit_ is None:
        raise ValueError(
            "No exit quote found for "
            f"{exit_date} {exit_time}"
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