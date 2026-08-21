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
OPTIONS_FILE = DATA_DIR / "nifty_options.csv"


def _add_probe_metadata(
    result: Dict[str, Any],
    archive_name: str,
    monthly_zip_name: str,
) -> Dict[str, Any]:
    result["archive"] = archive_name
    result["monthly_zip"] = monthly_zip_name
    return result


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

    A directory is treated as a release-asset directory and all
    matching yearly assets are merged automatically.

    A direct ZIP path continues to use the legacy loader.
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

        assets = sorted(
            path.glob("*.zip"),
            key=lambda item: item.name.lower(),
        )

        archive_name = ",".join(
            asset.name
            for asset in assets
        )

        return _add_probe_metadata(
            result,
            archive_name,
            monthly_zip_name,
        )

    result = load_btst_contract(
        year_zip_path=path,
        monthly_zip_name=monthly_zip_name,
        option_type=option_type,
        strike=strike,
        entry_date=entry_date,
        exit_date=exit_date,
    )

    return _add_probe_metadata(
        result,
        path.name,
        monthly_zip_name,
    )


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
    """

    result = load_btst_contract_from_release(
        release_dir=release_dir,
        year=year,
        monthly_zip_name=monthly_zip_name,
        option_type=option_type,
        strike=strike,
        entry_date=entry_date,
        exit_date=exit_date,
    )

    release_path = Path(release_dir)

    assets = sorted(
        release_path.glob("*.zip"),
        key=lambda item: item.name.lower(),
    )

    archive_name = ",".join(
        asset.name
        for asset in assets
    )

    return _add_probe_metadata(
        result,
        archive_name,
        monthly_zip_name,
    )