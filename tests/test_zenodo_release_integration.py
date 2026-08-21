from datetime import date
import io
import zipfile

from zenodo_option_data import (
    load_btst_contract_from_release,
    load_month_contract_from_release,
)


def _make_month_zip() -> bytes:
    data = """PE 10050,2017/10/26,14:59,55,56,54,55.00,100
PE 10050,2017/10/26,15:00,55,56,54,55.55,100
PE 10050,2017/10/27,09:14,49,50,48,49.50,100
PE 10050,2017/10/27,09:15,49,50,48,49.65,150
"""

    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "PE 10050.txt",
            data,
        )

    return buffer.getvalue()


def _make_year_zip(
    month_name: str,
) -> bytes:
    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            month_name,
            _make_month_zip(),
        )

    return buffer.getvalue()


def test_release_loader_reads_primary_asset(
    tmp_path,
):
    primary = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    primary.write_bytes(
        _make_year_zip(
            "November 2017.zip"
        )
    )

    rows = load_month_contract_from_release(
        release_dir=tmp_path,
        year=2017,
        monthly_zip_name="November 2017.zip",
        option_type="PE",
        strike=10050,
    )

    assert len(rows) == 4
    assert rows[0]["option_type"] == "PE"
    assert rows[0]["strike"] == 10050.0


def test_release_loader_reads_split_asset(
    tmp_path,
):
    primary = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    split = (
        tmp_path
        / "NiftyOptions 2017091.zip"
    )

    primary.write_bytes(
        _make_year_zip(
            "October 2017.zip"
        )
    )

    split.write_bytes(
        _make_year_zip(
            "November 2017.zip"
        )
    )

    rows = load_month_contract_from_release(
        release_dir=tmp_path,
        year=2017,
        monthly_zip_name="November 2017.zip",
        option_type="PE",
        strike=10050,
    )

    assert len(rows) == 4
    assert rows[1]["close"] == 55.55


def test_release_loader_reads_btst_entry_exit(
    tmp_path,
):
    primary = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    primary.write_bytes(
        _make_year_zip(
            "November 2017.zip"
        )
    )

    result = load_btst_contract_from_release(
        release_dir=tmp_path,
        year=2017,
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

    assert (
        result["entry"]["timestamp"].hour
        == 15
    )

    assert (
        result["exit"]["timestamp"].hour
        == 9
    )

    assert result["entry"]["close"] == 55.55
    assert result["exit"]["close"] == 49.65