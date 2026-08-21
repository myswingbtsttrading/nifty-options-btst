import io
import zipfile

import pytest

from release_archive_loader import (
    find_monthly_zip,
    find_release_asset,
    list_zip_members,
    read_monthly_zip,
    validate_release_archive,
)


def build_release_archive() -> bytes:
    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "November 2017.zip",
            b"november-data",
        )

        archive.writestr(
            "December 2017.zip",
            b"december-data",
        )

    return buffer.getvalue()


def test_find_release_asset(tmp_path):
    release_dir = tmp_path / "release"
    release_dir.mkdir()

    archive = (
        release_dir
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        build_release_archive()
    )

    result = find_release_asset(
        release_dir,
        "NiftyOptions 2017.zip",
    )

    assert result == archive


def test_find_release_asset_is_case_insensitive(
    tmp_path,
):
    release_dir = tmp_path / "release"
    release_dir.mkdir()

    archive = (
        release_dir
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        build_release_archive()
    )

    result = find_release_asset(
        release_dir,
        "niftyoptions 2017.zip",
    )

    assert result == archive


def test_list_zip_members(tmp_path):
    archive = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        build_release_archive()
    )

    members = list_zip_members(
        archive
    )

    assert "November 2017.zip" in members
    assert "December 2017.zip" in members


def test_find_monthly_zip(tmp_path):
    archive = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        build_release_archive()
    )

    member = find_monthly_zip(
        archive,
        "November 2017.zip",
    )

    assert member == "November 2017.zip"


def test_find_monthly_zip_case_insensitive(
    tmp_path,
):
    archive = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        build_release_archive()
    )

    member = find_monthly_zip(
        archive,
        "november 2017.zip",
    )

    assert member == "November 2017.zip"


def test_read_monthly_zip(tmp_path):
    archive = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        build_release_archive()
    )

    data = read_monthly_zip(
        archive,
        "November 2017.zip",
    )

    assert data == b"november-data"


def test_validate_release_archive(tmp_path):
    archive = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        build_release_archive()
    )

    result = validate_release_archive(
        archive,
        [
            "November 2017.zip",
            "December 2017.zip",
        ],
    )

    assert result["valid"] is True
    assert result["member_count"] == 2
    assert result["found_months"] == [
        "November 2017.zip",
        "December 2017.zip",
    ]
    assert result["missing_months"] == []


def test_validate_release_archive_reports_missing(
    tmp_path,
):
    archive = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        build_release_archive()
    )

    result = validate_release_archive(
        archive,
        [
            "November 2017.zip",
            "January 2018.zip",
        ],
    )

    assert result["valid"] is False
    assert result["found_months"] == [
        "November 2017.zip",
    ]
    assert result["missing_months"] == [
        "January 2018.zip",
    ]


def test_missing_release_asset_raises(
    tmp_path,
):
    release_dir = tmp_path / "release"
    release_dir.mkdir()

    with pytest.raises(
        FileNotFoundError,
        match="Release asset not found",
    ):
        find_release_asset(
            release_dir,
            "NiftyOptions 2017.zip",
        )


def test_missing_monthly_zip_raises(
    tmp_path,
):
    archive = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        build_release_archive()
    )

    with pytest.raises(
        FileNotFoundError,
        match="Monthly ZIP not found",
    ):
        find_monthly_zip(
            archive,
            "October 2017.zip",
        )