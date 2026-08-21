from datetime import date
import io
import zipfile

from backtest_runner import (
    DATA_DIR,
    NIFTY_FILE,
    run_release_btst_probe,
    run_zenodo_btst_probe,
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


def test_runner_release_probe_uses_split_assets(
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

    result = run_release_btst_probe(
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
    assert result["entry"]["close"] == 55.55
    assert result["exit"]["close"] == 49.65


def test_runner_release_probe_uses_15h_entry(
    tmp_path,
):
    archive = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        _make_year_zip(
            "November 2017.zip"
        )
    )

    result = run_release_btst_probe(
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

    assert (
        result["entry"]["timestamp"].hour
        == 15
    )


def test_runner_release_probe_uses_next_morning_exit(
    tmp_path,
):
    archive = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        _make_year_zip(
            "November 2017.zip"
        )
    )

    result = run_release_btst_probe(
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

    assert (
        result["exit"]["timestamp"].hour
        == 9
    )

    assert (
        result["exit"]["timestamp"].minute
        == 15
    )


def test_runner_direct_archive_path_remains_compatible(
    tmp_path,
):
    archive = (
        tmp_path
        / "NiftyOptions 2017.zip"
    )

    archive.write_bytes(
        _make_year_zip(
            "November 2017.zip"
        )
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
    assert result["entry"]["close"] == 55.55
    assert result["exit"]["close"] == 49.65


def test_runner_paths_remain_defined():
    assert isinstance(
        DATA_DIR,
        type(DATA_DIR),
    )

    assert NIFTY_FILE.name == "nifty.csv"