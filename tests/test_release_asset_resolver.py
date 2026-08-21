from pathlib import Path

import pytest

from release_asset_resolver import (
    discover_release_assets,
    find_primary_year_asset,
    find_split_year_assets,
    find_year_assets,
    resolve_year_archives,
    validate_year_release_assets,
)


def _touch(
    directory: Path,
    name: str,
) -> Path:
    path = directory / name
    path.write_bytes(b"test")
    return path


def test_discover_release_assets(
    tmp_path,
):
    _touch(
        tmp_path,
        "NiftyOptions 2017.zip",
    )

    _touch(
        tmp_path,
        "NiftyOptions 2017091.zip",
    )

    _touch(
        tmp_path,
        "README.txt",
    )

    assets = discover_release_assets(
        tmp_path
    )

    assert len(assets) == 2

    assert {
        asset.name
        for asset in assets
    } == {
        "NiftyOptions 2017.zip",
        "NiftyOptions 2017091.zip",
    }


def test_find_year_assets(
    tmp_path,
):
    _touch(
        tmp_path,
        "NiftyOptions 2017.zip",
    )

    _touch(
        tmp_path,
        "NiftyOptions 2017091.zip",
    )

    _touch(
        tmp_path,
        "NiftyOptions 2018.zip",
    )

    assets = find_year_assets(
        tmp_path,
        2017,
    )

    assert len(assets) == 2

    assert all(
        asset.year == 2017
        for asset in assets
    )


def test_primary_year_asset(
    tmp_path,
):
    path = _touch(
        tmp_path,
        "NiftyOptions 2017.zip",
    )

    _touch(
        tmp_path,
        "NiftyOptions 2017091.zip",
    )

    asset = find_primary_year_asset(
        tmp_path,
        2017,
    )

    assert asset.path == path
    assert asset.year == 2017
    assert asset.part is None


def test_split_year_assets(
    tmp_path,
):
    _touch(
        tmp_path,
        "NiftyOptions 2017.zip",
    )

    _touch(
        tmp_path,
        "NiftyOptions 2017091.zip",
    )

    assets = find_split_year_assets(
        tmp_path,
        2017,
    )

    assert len(assets) == 1
    assert (
        assets[0].name
        == "NiftyOptions 2017091.zip"
    )


def test_resolve_year_archives(
    tmp_path,
):
    _touch(
        tmp_path,
        "NiftyOptions 2017.zip",
    )

    _touch(
        tmp_path,
        "NiftyOptions 2017091.zip",
    )

    result = resolve_year_archives(
        tmp_path,
        2017,
    )

    assert result["year"] == 2017
    assert result["asset_count"] == 2
    assert result["split_count"] == 1
    assert result["has_primary"] is True
    assert result["has_split"] is True


def test_validate_expected_release_assets(
    tmp_path,
):
    _touch(
        tmp_path,
        "NiftyOptions 2017.zip",
    )

    _touch(
        tmp_path,
        "NiftyOptions 2017091.zip",
    )

    result = validate_year_release_assets(
        tmp_path,
        2017,
        [
            "NiftyOptions 2017.zip",
            "NiftyOptions 2017091.zip",
        ],
    )

    assert result["valid"] is True
    assert result["missing"] == []


def test_validate_missing_release_asset(
    tmp_path,
):
    _touch(
        tmp_path,
        "NiftyOptions 2017.zip",
    )

    result = validate_year_release_assets(
        tmp_path,
        2017,
        [
            "NiftyOptions 2017.zip",
            "NiftyOptions 2017091.zip",
        ],
    )

    assert result["valid"] is False
    assert result["missing"] == [
        "NiftyOptions 2017091.zip"
    ]


def test_missing_release_directory_raises(
    tmp_path,
):
    missing = (
        tmp_path
        / "does-not-exist"
    )

    with pytest.raises(
        FileNotFoundError,
        match="Release directory not found",
    ):
        discover_release_assets(
            missing
        )


def test_missing_year_raises(
    tmp_path,
):
    _touch(
        tmp_path,
        "NiftyOptions 2017.zip",
    )

    with pytest.raises(
        FileNotFoundError,
        match="No ZIP release assets found",
    ):
        resolve_year_archives(
            tmp_path,
            2018,
        )