from pathlib import Path
from zipfile import ZipFile

import pytest


RELEASE_TAG = "data-2017-v1"

OCTOBER_ASSET = "October.2017.zip"
NOVEMBER_ASSET = "November.2017.zip"


def _release_data_dir() -> Path:
    return Path("release-data")


def _release_data_available() -> bool:
    release_dir = _release_data_dir()

    return (
        (release_dir / OCTOBER_ASSET).exists()
        and
        (release_dir / NOVEMBER_ASSET).exists()
    )


def _require_release_data() -> Path:
    release_dir = _release_data_dir()

    if not _release_data_available():
        pytest.skip(
            "Release data not downloaded; "
            "run the release BTST workflow for "
            "real-data validation."
        )

    return release_dir


def test_release_monthly_assets_exist():
    release_dir = _require_release_data()

    october = release_dir / OCTOBER_ASSET
    november = release_dir / NOVEMBER_ASSET

    assert october.exists(), (
        f"Missing release asset: {october}"
    )

    assert november.exists(), (
        f"Missing release asset: {november}"
    )


def test_release_monthly_assets_are_valid_zip_files():
    release_dir = _require_release_data()

    archives = [
        release_dir / OCTOBER_ASSET,
        release_dir / NOVEMBER_ASSET,
    ]

    for archive in archives:
        assert archive.exists(), (
            f"Missing release asset: {archive}"
        )

        assert archive.stat().st_size > 0, (
            f"Release asset is empty: {archive}"
        )

        with ZipFile(archive) as zf:
            members = zf.namelist()

            assert members, (
                f"Release archive is empty: {archive}"
            )

            bad_file = zf.testzip()

            assert bad_file is None, (
                f"Corrupt ZIP {archive}: "
                f"{bad_file}"
            )


def test_release_asset_names_match_current_release():
    release_dir = _require_release_data()

    expected = {
        OCTOBER_ASSET,
        NOVEMBER_ASSET,
    }

    actual = {
        path.name
        for path in release_dir.glob("*.zip")
    }

    assert expected.issubset(actual), (
        f"Expected release assets "
        f"{sorted(expected)}, "
        f"found {sorted(actual)}"
    )