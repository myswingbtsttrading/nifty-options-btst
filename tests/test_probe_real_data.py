from pathlib import Path
from zipfile import ZipFile


RELEASE_TAG = "data-2017-v1"

OCTOBER_ASSET = "October.2017.zip"
NOVEMBER_ASSET = "November.2017.zip"


def test_release_monthly_assets_exist():
    release_dir = Path("release-data")

    october = release_dir / OCTOBER_ASSET
    november = release_dir / NOVEMBER_ASSET

    assert october.exists(), (
        f"Missing release asset: {october}"
    )

    assert november.exists(), (
        f"Missing release asset: {november}"
    )


def test_release_monthly_assets_are_valid_zip_files():
    release_dir = Path("release-data")

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


def test_release_asset_names_match_current_release():
    expected = {
        OCTOBER_ASSET,
        NOVEMBER_ASSET,
    }

    release_dir = Path("release-data")

    actual = {
        path.name
        for path in release_dir.glob("*.zip")
    }

    assert expected.issubset(actual), (
        f"Expected release assets "
        f"{sorted(expected)}, "
        f"found {sorted(actual)}"
    )