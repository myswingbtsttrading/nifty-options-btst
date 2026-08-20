from datetime import date
import io
import zipfile

from historical_option_loader import (
    filter_contract,
    find_price_at_or_after,
    find_price_at_or_before,
    load_month_zip_bytes,
    parse_monthly_zip_filename,
)


def build_month_zip() -> bytes:
    option_data = """PE 10050,2017/10/26,14:59,55,56,54,55.00,100
PE 10050,2017/10/26,15:00,55,56,54,55.55,100
PE 10050,2017/10/27,09:15,49,50,48,49.65,100
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


def build_year_zip() -> bytes:
    monthly_bytes = build_month_zip()

    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "November 2017.zip",
            monthly_bytes,
        )

    return buffer.getvalue()


def test_monthly_filename_maps_to_expected_expiry():
    expiry = parse_monthly_zip_filename(
        "November 2017.zip"
    )

    assert expiry == date(2017, 11, 30)


def test_nested_monthly_archive_contains_expected_contract():
    year_bytes = build_year_zip()

    with zipfile.ZipFile(
        io.BytesIO(year_bytes)
    ) as year_archive:
        monthly_bytes = year_archive.read(
            "November 2017.zip"
        )

    rows = load_month_zip_bytes(
        monthly_bytes,
        date(2017, 11, 30),
    )

    contract = filter_contract(
        rows,
        "PE",
        10050,
        date(2017, 11, 30),
    )

    assert len(contract) == 3


def test_real_data_entry_timestamp_selection():
    monthly_bytes = build_month_zip()

    rows = load_month_zip_bytes(
        monthly_bytes,
        date(2017, 11, 30),
    )

    contract = filter_contract(
        rows,
        "PE",
        10050,
        date(2017, 11, 30),
    )

    entry_rows = [
        row
        for row in contract
        if row["timestamp"].date()
        == date(2017, 10, 26)
    ]

    entry = find_price_at_or_before(
        entry_rows,
        contract[1]["timestamp"],
    )

    assert entry is not None
    assert entry["timestamp"].strftime(
        "%Y-%m-%d %H:%M"
    ) == "2017-10-26 15:00"
    assert entry["close"] == 55.55


def test_real_data_next_morning_selection():
    monthly_bytes = build_month_zip()

    rows = load_month_zip_bytes(
        monthly_bytes,
        date(2017, 11, 30),
    )

    contract = filter_contract(
        rows,
        "PE",
        10050,
        date(2017, 11, 30),
    )

    exit_rows = [
        row
        for row in contract
        if row["timestamp"].date()
        == date(2017, 10, 27)
    ]

    exit_ = find_price_at_or_after(
        exit_rows,
        exit_rows[0]["timestamp"],
    )

    assert exit_ is not None
    assert exit_["timestamp"].strftime(
        "%Y-%m-%d %H:%M"
    ) == "2017-10-27 09:15"
    assert exit_["close"] == 49.65