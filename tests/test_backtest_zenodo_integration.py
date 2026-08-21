from datetime import date
import io
import json
import zipfile

from backtest_runner import run_zenodo_btst_probe


def build_realistic_year_zip() -> bytes:
    option_data = """PE 10050,2017/10/26,14:59,55,56,54,55.00,100
PE 10050,2017/10/26,15:00,55,56,54,55.55,100
PE 10050,2017/10/26,15:01,55,56,54,55.60,100
PE 10050,2017/10/27,09:14,49,50,48,49.50,100
PE 10050,2017/10/27,09:15,49,50,48,49.65,150
PE 10050,2017/10/27,09:16,49,50,48,49.80,100
"""

    month_buffer = io.BytesIO()

    with zipfile.ZipFile(
        month_buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as month_zip:
        month_zip.writestr(
            "PE 10050.txt",
            option_data,
        )

    year_buffer = io.BytesIO()

    with zipfile.ZipFile(
        year_buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as year_zip:
        year_zip.writestr(
            "November 2017.zip",
            month_buffer.getvalue(),
        )

    return year_buffer.getvalue()


def test_zenodo_btst_probe_selects_real_entry_and_exit(
    tmp_path,
):
    archive = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        build_realistic_year_zip()
    )

    result = run_zenodo_btst_probe(
        archive_path=archive,
        monthly_zip_name="November 2017.zip",
        option_type="PE",
        strike=10050,
        entry_date=date(
            2017,
            10,
            26,
        ),
        exit_date=date(
            2017,
            10,
            27,
        ),
    )

    assert result["option_type"] == "PE"
    assert result["strike"] == 10050.0

    assert result["entry"]["timestamp"].hour == 15
    assert result["entry"]["timestamp"].minute == 0
    assert result["entry"]["close"] == 55.55

    assert result["exit"]["timestamp"].hour == 9
    assert result["exit"]["timestamp"].minute == 15
    assert result["exit"]["close"] == 49.65


def test_zenodo_btst_probe_returns_expected_metadata(
    tmp_path,
):
    archive = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        build_realistic_year_zip()
    )

    result = run_zenodo_btst_probe(
        archive_path=archive,
        monthly_zip_name="November 2017.zip",
        option_type="PE",
        strike=10050,
        entry_date=date(
            2017,
            10,
            26,
        ),
        exit_date=date(
            2017,
            10,
            27,
        ),
    )

    assert result["archive"] == (
        "NiftyOptions 2017.zip"
    )

    assert result["monthly_zip"] == (
        "November 2017.zip"
    )

    assert str(result["expiry"]) == (
        "2017-11-30"
    )


def test_zenodo_btst_probe_uses_first_valid_exit_at_or_after_915(
    tmp_path,
):
    archive = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        build_realistic_year_zip()
    )

    result = run_zenodo_btst_probe(
        archive_path=archive,
        monthly_zip_name="November 2017.zip",
        option_type="PE",
        strike=10050,
        entry_date=date(
            2017,
            10,
            26,
        ),
        exit_date=date(
            2017,
            10,
            27,
        ),
    )

    assert result["exit"]["timestamp"].strftime(
        "%H:%M"
    ) == "09:15"

    assert result["exit"]["close"] == 49.65