from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict

from zenodo_option_data import (
    load_btst_contract,
    load_btst_contract_from_release,
)


DATA_DIR = Path(__file__).resolve().parent / "data"
NIFTY_FILE = DATA_DIR / "nifty.csv"


def run_zenodo_btst_probe(
    archive_path: str | Path | None = None,
    monthly_zip_name: str = "November 2017.zip",
    option_type: str = "PE",
    strike: float = 10050,
    entry_date: date = date(2017, 10, 26),
    exit_date: date = date(2017, 10, 27),
) -> Dict[str, Any]:
    """
    Run a single BTST probe.

    If archive_path points directly to a yearly ZIP, use the
    legacy single-archive loader.

    If archive_path points to a directory, resolve all release
    assets for 2017 and use the split-aware release loader.
    """

    if archive_path is None:
        archive_path = DATA_DIR

    path = Path(archive_path)

    if path.is_dir():
        result = load_btst_contract_from_release(
            release_dir=path,
            year=entry_date.year,
            monthly_zip_name=monthly_zip_name,
            option_type=option_type,
            strike=strike,
            entry_date=entry_date,
            exit_date=exit_date,
        )

    else:
        result = load_btst_contract(
            year_zip_path=path,
            monthly_zip_name=monthly_zip_name,
            option_type=option_type,
            strike=strike,
            entry_date=entry_date,
            exit_date=exit_date,
        )

    return result


def run_release_btst_probe(
    release_dir: str | Path,
    year: int,
    monthly_zip_name: str,
    option_type: str,
    strike: float,
    entry_date: date,
    exit_date: date,
) -> Dict[str, Any]:
    """
    Explicit release-backed BTST probe.

    This is the preferred entry point when using the GitHub
    Release assets.
    """

    return load_btst_contract_from_release(
        release_dir=release_dir,
        year=year,
        monthly_zip_name=monthly_zip_name,
        option_type=option_type,
        strike=strike,
        entry_date=entry_date,
        exit_date=exit_date,
    )