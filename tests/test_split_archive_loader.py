import io
import zipfile

import pytest

from split_archive_loader import (
    merge_year_release_assets,
    merge_zip_archives,
    merged_member_names,
)


def _make_zip(
    members: dict[str, bytes],
) -> bytes:
    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        for name, data in members.items():
            archive.writestr(
                name,
                data,
            )

    return buffer.getvalue()


def _write_zip(
    path,
    members,
):
    path.write_bytes(
        _make_zip(members)
    )


def _read_members(
    data: bytes,
) -> dict[str, bytes]:
    result = {}

    with zipfile.ZipFile(
        io.BytesIO(data),
        "r",
    ) as archive:
        for name in archive.namelist():
            result[name] = archive.read(name)

    return result


def test_merge_two_split_archives(
    tmp_path,
):
    first = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    second = (
        tmp_path
        / "NiftyOptions 2017091.zip"
    )

    _write_zip(
        first,
        {
            "January 2017.zip":
                b"january",
            "February 2017.zip":
                b"february",
        },
    )

    _write_zip(
        second,
        {
            "March 2017.zip":
                b"march",
            "April 2017.zip":
                b"april",
        },
    )

    merged = merge_year_release_assets(
        [
            first,
            second,
        ]
    )

    members = _read_members(
        merged
    )

    assert members == {
        "January 2017.zip":
            b"january",
        "February 2017.zip":
            b"february",
        "March 2017.zip":
            b"march",
        "April 2017.zip":
            b"april",
    }


def test_merge_preserves_unique_members(
    tmp_path,
):
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    _write_zip(
        first,
        {
            "November 2017.zip":
                b"november",
        },
    )

    _write_zip(
        second,
        {
            "December 2017.zip":
                b"december",
        },
    )

    merged = merge_zip_archives(
        [
            first,
            second,
        ]
    )

    names = set(
        _read_members(merged)
    )

    assert names == {
        "November 2017.zip",
        "December 2017.zip",
    }


def test_later_archive_replaces_duplicate_member(
    tmp_path,
):
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    _write_zip(
        first,
        {
            "November 2017.zip":
                b"old",
        },
    )

    _write_zip(
        second,
        {
            "November 2017.zip":
                b"new",
        },
    )

    merged = merge_zip_archives(
        [
            first,
            second,
        ]
    )

    members = _read_members(
        merged
    )

    assert members[
        "November 2017.zip"
    ] == b"new"


def test_member_names_are_unique(
    tmp_path,
):
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    _write_zip(
        first,
        {
            "November 2017.zip":
                b"one",
            "December 2017.zip":
                b"two",
        },
    )

    _write_zip(
        second,
        {
            "november 2017.zip":
                b"three",
            "January 2018.zip":
                b"four",
        },
    )

    names = merged_member_names(
        [
            first,
            second,
        ]
    )

    assert len(names) == 3
    assert {
        name.lower()
        for name in names
    } == {
        "november 2017.zip",
        "december 2017.zip",
        "january 2018.zip",
    }


def test_empty_archive_list_raises():
    with pytest.raises(
        ValueError,
        match="At least one archive is required",
    ):
        merge_year_release_assets([])


def test_missing_archive_raises(
    tmp_path,
):
    with pytest.raises(
        FileNotFoundError,
        match="Archive not found",
    ):
        merge_year_release_assets(
            [
                tmp_path / "missing.zip"
            ]
        )