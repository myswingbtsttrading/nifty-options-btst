from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional
import io
import re
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


def _normalise_monthly_zip_name(
    filename: str,
) -> str:
    """
    Normalise monthly ZIP naming so both of these work:

        November 2017.zip
        November.2017.zip

    The release currently stores monthly assets using the
    dot form.
    """
    name = Path(filename).name.strip()

    match = re.match(
        r"^(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"[ .]+(\d{4})\.zip$",
        name,
        re.IGNORECASE,
    )

    if not match:
        return name

    return (
        f"{match.group(1)} "
        f"{match.group(2)}.zip"
    )


def _find_member_case_insensitive(
    archive: zipfile.ZipFile,
    filename: str,
) -> str | None:
    target = Path(filename).name.lower()

    for name in archive.namelist():
        if Path(name).name.lower() == target:
            return name

    return None


def _find_monthly_member(
    archive: zipfile.ZipFile,
    filename: str,
) -> str | None:
    """
    Find a monthly ZIP member while accepting both:

        November 2017.zip
        November.2017.zip
    """
    target = _normalise_monthly_zip_name(filename).lower()

    for name in archive.namelist():
        member_name = Path(name).name

        if (
            _normalise_monthly_zip_name(member_name).lower()
            == target
        ):
            return name

    return None


def _find_direct_monthly_asset(
    release_dir: str | Path,
    monthly_zip_name: str,
    year: int,
) -> Path | None:
    """
    Find a release asset that is itself the monthly ZIP.

    Example:

        release-data/November.2017.zip

    This is the current release layout.
    """
    release_dir = Path(release_dir)

    target = _normalise_monthly_zip_name(
        monthly_zip_name
    ).lower()

    for path in release_dir.glob("*.zip"):
        if (
            _normalise_monthly_zip_name(path.name).lower()
            == target
        ):
            return path

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
        _normalise_monthly_zip_name(
            monthly_zip_name
        )
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
        member_name = _find_monthly_member(
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


class _temporary_zip:
    """
    In-memory ZipFile context manager.
    """

    def __init__(
        self,
        data: bytes,
    ):
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


def load_month_contract_from_release(
    release_dir: str | Path,
    year: int,
    monthly_zip_name: str,
    option_type: str,
    strike: float,
) -> List[OptionRow]:
    """
    Load a monthly option contract from release data.

    Supported release layouts:

    1. Direct monthly assets:

       release-data/November.2017.zip

    2. A yearly ZIP containing monthly ZIPs:

       NiftyOptions 2017.zip
           November 2017.zip

    3. Split yearly ZIP assets.
    """

    normalised_monthly_name = (
        _normalise_monthly_zip_name(
            monthly_zip_name
        )
    )

    monthly_expiry = parse_monthly_zip_filename(
        normalised_monthly_name
    )

    if monthly_expiry is None:
        raise ValueError(
            f"Invalid monthly ZIP name: "
            f"{monthly_zip_name}"
        )

    release_dir = Path(release_dir)

    # ---------------------------------------------------------
    # CURRENT RELEASE LAYOUT:
    # Each monthly ZIP is itself a release asset.
    # ---------------------------------------------------------
    direct_asset = _find_direct_monthly_asset(
        release_dir=release_dir,
        monthly_zip_name=monthly_zip_name,
        year=year,
    )

    if direct_asset is not None:
        with zipfile.ZipFile(
            direct_asset,
            "r",
        ) as archive:
            rows = load_month_zip_bytes(
                direct_asset.read_bytes(),
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
                f"expiry {monthly_expiry} "
                f"in {direct_asset.name}"
            )

        return sorted(
            contract_rows,
            key=lambda row: row["timestamp"],
        )

    # ---------------------------------------------------------
    # LEGACY YEARLY/SPLIT RELEASE LAYOUT
    # ---------------------------------------------------------
    archive_bytes = _load_year_archive_bytes(
        release_dir,
        year,
    )

    with _temporary_zip(
        archive_bytes
    ) as archive:

        member_name = _find_monthly_member(
            archive,
            normalised_monthly_name,
        )

        if member_name is None:
            raise FileNotFoundError(
                "Monthly ZIP not found in release "
                f"assets: {monthly_zip_name}"
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
            _normalise_monthly_zip_name(
                monthly_zip_name
            )
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
            _normalise_monthly_zip_name(
                monthly_zip_name
            )
        ),
        "entry": entry,
        "exit": exit_,
        "entry_date": entry_date,
        "exit_date": exit_date,
        "entry_time": entry_time,
        "exit_time": exit_time,
    }