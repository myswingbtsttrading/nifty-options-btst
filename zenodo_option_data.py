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
from release_asset_resolver import find_year_assets
from split_archive_loader import merge_year_release_assets


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
    Backward-compatible loader for a single yearly ZIP.
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
    ) as archive:

        member_name = _find_member_case_insensitive(
            archive,
            monthly_zip_name,
        )

        if member_name is None:
            raise FileNotFoundError(
                f"Monthly ZIP not found inside "
                f"{year_zip_path.name}: "
                f"{monthly_zip_name}"
            )

        monthly_bytes = archive.read(
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


def _load_year_archive_bytes(
    release_dir: str | Path,
    year: int,
) -> bytes:
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
    Load a monthly option contract from all release
    assets belonging to the requested year.
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

    with zipfile.ZipFile(
        Path(
            release_dir
        ) / "__merged_release__.zip",
        "w",
    ) if False else _temporary_zip(
        archive_bytes
    ) as archive:

        member_name = _find_member_case_insensitive(
            archive,
            monthly_zip_name,
        )

        if member_name is None:
            raise FileNotFoundError(
                f"Monthly ZIP not found: "
                f"{monthly_zip_name}"
            )

        monthly_bytes = archive.read(
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


class _temporary_zip:
    """
    In-memory ZipFile context manager.
    """

    def __init__(
        self,
        data: bytes,
    ):
        import io

        self._buffer = io.BytesIO(data)
        self._archive: zipfile.ZipFile | None = None

    def __enter__(
        self,
    ) -> zipfile.ZipFile:
        self._archive = zipfile.ZipFile(
            self._buffer,
            "r",
        )
        return self._archive

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        if self._archive is not None:
            self._archive.close()

        self._buffer.close()

        return False


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