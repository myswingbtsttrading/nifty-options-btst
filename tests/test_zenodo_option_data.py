from datetime import date, datetime
import io
import zipfile

import pytest

from zenodo_option_data import (
    get_entry_quote,
    get_exit_quote,
    load_btst_contract,
    load_month_contract,
)


def build_year_zip() -> bytes:
    option_data = """PE 10050,2017/10/26,14:59,55,56,54,55.00,100
PE 10050,2017/10/26,15:00,55,56,54,55.55,100
PE 10050,2017/10/27,09:15,49,50,48,49.65,150
PE 10050,2017/10/27,09:16,49,50,48,49.80,100
"""

    monthly_buffer = io.BytesIO()

    with zipfile.ZipFile(
        monthly_buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as monthly_archive:
        monthly_archive.writestr(
            "PE 10050.txt",
            option_data,
        )

    year_buffer = io.BytesIO()

    with zipfile.ZipFile(
        year_buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as year_archive:
        year_archive.writestr(
            "November 2017.zip",
            monthly_buffer.getvalue(),
        )

    return year_buffer.getvalue()


def test_load_month_contract(tmp_path):
    year_zip = tmp_path / "NiftyOptions 2017.zip"

    year_zip.write_bytes(
        build_year_zip()
    )

    rows = load_month_contract(
        year_zip_path=year_zip,
        monthly_zip_name="November 2017.zip",
        option_type="PE",
        strike=10050,
    )

    assert len(rows) == 4

    assert rows[0]["option_type"] == "PE"
    assert rows[0]["strike"] == 10050.0
    assert rows[0]["expiry"] == date(
        2017,
        11,
        30,
    )


def test_get_entry_quote_uses_3pm_observation(
    tmp_path,
):
    year_zip = tmp_path / "NiftyOptions 2017.zip"

    year_zip.write_bytes(
        build_year_zip()
    )

    rows = load_month_contract(
        year_zip,
        "November 2017.zip",
        "PE",
        10050,
    )

    entry = get_entry_quote(
        rows,
        date(2017, 10, 26),
        "15:00",
    )

    assert entry is not None

    assert entry["timestamp"] == datetime(
        2017,
        10,
        26,
        15,
        0,
    )

    assert entry["close"] == 55.55


def test_get_exit_quote_uses_915_observation(
    tmp_path,
):
    year_zip = tmp_path / "NiftyOptions 2017.zip"

    year_zip.write_bytes(
        build_year_zip()
    )

    rows = load_month_contract(
        year_zip,
        "November 2017.zip",
        "PE",
        10050,
    )

    exit_quote = get_exit_quote(
        rows,
        date(2017, 10, 27),
        "09:15",
    )

    assert exit_quote is not None

    assert exit_quote["timestamp"] == datetime(
        2017,
        10,
        27,
        9,
        15,
    )

    assert exit_quote["close"] == 49.65


def test_load_btst_contract_returns_entry_and_exit(
    tmp_path,
):
    year_zip = tmp_path / "NiftyOptions 2017.zip"

    year_zip.write_bytes(
        build_year_zip()
    )

    result = load_btst_contract(
        year_zip_path=year_zip,
        monthly_zip_name="November 2017.zip",
        option_type="PE",
        strike=10050,
        entry_date=date(2017, 10, 26),
        exit_date=date(2017, 10, 27),
    )

    assert result["option_type"] == "PE"
    assert result["strike"] == 10050.0
    assert result["expiry"] == date(
        2017,
        11,
        30,
    )

    assert result["entry"] is not None
    assert result["exit"] is not None

    assert result["entry"]["close"] == 55.55
    assert result["exit"]["close"] == 49.65


def test_missing_month_raises(tmp_path):
    year_zip = tmp_path / "NiftyOptions 2017.zip"

    year_zip.write_bytes(
        build_year_zip()
    )

    with pytest.raises(
        FileNotFoundError
    ):
        load_month_contract(
            year_zip,
            "October 2017.zip",
            "PE",
            10050,
        )


def test_missing_contract_raises(tmp_path):
    year_zip = tmp_path / "NiftyOptions 2017.zip"

    year_zip.write_bytes(
        build_year_zip()
    )

    with pytest.raises(
        ValueError,
        match="Option contract not found",
    ):
        load_month_contract(
            year_zip,
            "November 2017.zip",
            "CE",
            10050,
        )