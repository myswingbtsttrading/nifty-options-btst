from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from github_release_assets import (
    download_release_assets,
)
from backtest_runner import (
    run_release_btst_probe,
)


DEFAULT_OWNER = "myswingbtsttrading"
DEFAULT_REPO = "nifty-options-btst"
DEFAULT_TAG = "data-2017-v1"

DEFAULT_ASSETS = [
    "NiftyOptions 2017.zip",
    "NiftyOptions 2017091.zip",
]


def prepare_release_assets(
    destination_dir: str | Path,
    owner: str = DEFAULT_OWNER,
    repo: str = DEFAULT_REPO,
    tag: str = DEFAULT_TAG,
    asset_names: list[str] | None = None,
) -> list[Path]:
    destination_dir = Path(
        destination_dir
    )

    names = (
        list(asset_names)
        if asset_names is not None
        else list(DEFAULT_ASSETS)
    )

    return download_release_assets(
        owner=owner,
        repo=repo,
        tag=tag,
        asset_names=names,
        destination_dir=destination_dir,
    )


def run_release_btst_pipeline(
    destination_dir: str | Path,
    monthly_zip_name: str,
    option_type: str,
    strike: float,
    entry_date: date,
    exit_date: date,
    owner: str = DEFAULT_OWNER,
    repo: str = DEFAULT_REPO,
    tag: str = DEFAULT_TAG,
    asset_names: list[str] | None = None,
) -> dict[str, Any]:
    destination_dir = Path(
        destination_dir
    )

    downloaded = prepare_release_assets(
        destination_dir=destination_dir,
        owner=owner,
        repo=repo,
        tag=tag,
        asset_names=asset_names,
    )

    result = run_release_btst_probe(
        release_dir=destination_dir,
        year=entry_date.year,
        monthly_zip_name=monthly_zip_name,
        option_type=option_type,
        strike=strike,
        entry_date=entry_date,
        exit_date=exit_date,
    )

    result["release_owner"] = owner
    result["release_repo"] = repo
    result["release_tag"] = tag
    result["downloaded_assets"] = [
        path.name
        for path in downloaded
    ]

    return result