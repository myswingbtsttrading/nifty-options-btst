from datetime import date
import io
import zipfile

import pytest

from zenodo_option_data import (
    get_entry_quote,
    get_exit_quote,
    load_month_contract,
)


def _build_month_zip() -> bytes:
    option_data = """PE 10050,2017/10/26,14:59,55,56,54,55.00,100
PE 10050,2017/10/26,15:00,55,56,54,55.55,100
PE 10050,2017/10/26,15:01,55,56,54,55.60,100
PE 10050,2017/10/27,09:14,49,50,48,49.50,100
PE 10050,2017/10/27,09:15,49,50,48,49.65,150
PE 10050,2017/10/27,09:16,49,50,48,49.80,100
"""

    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "PE 10050.txt",
            option_data,
        )

    return buffer.getvalue()


def _build_year_zip(
    monthly_name: str = "November 2017.zip",
) -> bytes:
    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            monthly_name,
            _build_month_zip(),
        )

    return buffer.getvalue()


def test_release_style_year_archive_contains_month_zip(
    tmp_path,
):
    archive_path = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive_path.write_bytes(
        _build_year_zip()
    )

    rows = load_month_contract(
        year_zip_path=archive_path,
        monthly_zip_name="November 2017.zip",
        option_type="PE",
        strike=10050,
    )

    assert len(rows) == 6
    assert rows[0]["option_type"] == "PE"
    assert rows[0]["strike"] == 10050.0


def test_release_style_archive_entry_at_1500(
    tmp_path,
):
    archive_path = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive_path.write_bytes(
        _build_year_zip()
    )

    rows = load_month_contract(
        archive_path,
        "November 2017.zip",
        "PE",
        10050,
    )

    quote = get_entry_quote(
        rows,
        date(2017, 10, 26),
        "15:00",
    )

    assert quote is not None
    assert quote["timestamp"].strftime(
        "%H:%M"
    ) == "15:00"
    assert quote["close"] == 55.55


def test_release_style_archive_exit_at_0915(
    tmp_path,
):
    archive_path = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive_path.write_bytes(
        _build_year_zip()
    )

    rows = load_month_contract(
        archive_path,
        "November 2017.zip",
        "PE",
        10050,
    )

    quote = get_exit_quote(
        rows,
        date(2017, 10, 27),
        "09:15",
    )

    assert quote is not None
    assert quote["timestamp"].strftime(
        "%H:%M"
    ) == "09:15"
    assert quote["close"] == 49.65


def test_missing_release_archive_raises(
    tmp_path,
):
    archive_path = (
        tmp_path
        / "missing.zip"
    )

    with pytest.raises(
        FileNotFoundError,
        match="Year ZIP not found",
    ):
        load_month_contract(
            archive_path,
            "November 2017.zip",
            "PE",
            10050,
        )


def test_missing_monthly_release_zip_raises(
    tmp_path,
):
    archive_path = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive_path.write_bytes(
        _build_year_zip()
    )

    with pytest.raises(
        FileNotFoundError,
        match="Monthly ZIP not found",
    ):
        load_month_contract(
            archive_path,
            "October 2017.zip",
            "PE",
            10050,
        )


def test_monthly_zip_name_is_case_insensitive(
    tmp_path,
):
    archive_path = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive_path.write_bytes(
        _build_year_zip(
            "November 2017.zip"
        )
    )

    rows = load_month_contract(
        archive_path,
        "november 2017.zip",
        "PE",
        10050,
    )

    assert len(rows) == 6