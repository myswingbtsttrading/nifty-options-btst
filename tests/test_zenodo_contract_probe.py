from datetime import date
import io
import zipfile

from zenodo_contract_probe import (
    probe_contract,
)


def build_test_year_zip() -> bytes:

    monthly_buffer = io.BytesIO()

    option_text = "\n".join(
        [
            (
                "PE 10050,2017/10/26,14:59,"
                "55,56,54,55.00,100"
            ),
            (
                "PE 10050,2017/10/26,15:00,"
                "55.5,56,55,55.55,100"
            ),
            (
                "PE 10050,2017/10/26,15:17,"
                "56,57,55,56.00,100"
            ),
            (
                "PE 10050,2017/10/27,09:15,"
                "49,50,48,49.65,100"
            ),
            (
                "PE 10050,2017/10/27,09:20,"
                "50,51,49,50.80,100"
            ),
        ]
    )

    with zipfile.ZipFile(
        monthly_buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as monthly_zip:

        monthly_zip.writestr(
            "PE 10050.txt",
            option_text,
        )

    year_buffer = io.BytesIO()

    with zipfile.ZipFile(
        year_buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as year_zip:

        year_zip.writestr(
            "November 2017.zip",
            monthly_buffer.getvalue(),
        )

    return year_buffer.getvalue()


def test_probe_finds_3pm_entry_and_morning_exit(
    tmp_path,
):

    archive = build_test_year_zip()

    path = tmp_path / "NiftyOptions 2017.zip"

    path.write_bytes(
        archive
    )

    result = probe_contract(
        path,
        "November 2017.zip",
        "PE",
        10050,
        date(
            2017,
            10,
            26,
        ),
        date(
            2017,
            10,
            27,
        ),
    )

    assert result["expiry"] == date(
        2017,
        11,
        30,
    )

    assert result["entry"] is not None
    assert result["entry"]["timestamp"].strftime(
        "%H:%M"
    ) == "15:00"

    assert result["entry"]["close"] == 55.55

    assert result["exit"] is not None
    assert result["exit"]["timestamp"].strftime(
        "%H:%M"
    ) == "09:15"

    assert result["exit"]["close"] == 49.65


def test_probe_uses_latest_price_before_3pm(
    tmp_path,
):

    monthly_buffer = io.BytesIO()

    option_text = (
        "PE 10050,2017/10/26,14:58,"
        "54,55,53,54.50,100\n"
        "PE 10050,2017/10/26,14:59,"
        "55,56,54,55.00,100\n"
        "PE 10050,2017/10/27,09:15,"
        "49,50,48,49.65,100\n"
    )

    with zipfile.ZipFile(
        monthly_buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as monthly_zip:

        monthly_zip.writestr(
            "PE 10050.txt",
            option_text,
        )

    year_buffer = io.BytesIO()

    with zipfile.ZipFile(
        year_buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as year_zip:

        year_zip.writestr(
            "November 2017.zip",
            monthly_buffer.getvalue(),
        )

    path = tmp_path / "NiftyOptions 2017.zip"

    path.write_bytes(
        year_buffer.getvalue()
    )

    result = probe_contract(
        path,
        "November 2017.zip",
        "PE",
        10050,
        date(
            2017,
            10,
            26,
        ),
        date(
            2017,
            10,
            27,
        ),
    )

    assert result["entry"]["timestamp"].strftime(
        "%H:%M"
    ) == "14:59"

    assert result["entry"]["close"] == 55.00


def test_probe_uses_first_available_morning_price(
    tmp_path,
):

    monthly_buffer = io.BytesIO()

    option_text = (
        "PE 10050,2017/10/26,15:00,"
        "55,56,54,55.55,100\n"
        "PE 10050,2017/10/27,09:16,"
        "49,50,48,49.80,100\n"
        "PE 10050,2017/10/27,09:20,"
        "50,51,49,50.80,100\n"
    )

    with zipfile.ZipFile(
        monthly_buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as monthly_zip:

        monthly_zip.writestr(
            "PE 10050.txt",
            option_text,
        )

    year_buffer = io.BytesIO()

    with zipfile.ZipFile(
        year_buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as year_zip:

        year_zip.writestr(
            "November 2017.zip",
            monthly_buffer.getvalue(),
        )

    path = tmp_path / "NiftyOptions 2017.zip"

    path.write_bytes(
        year_buffer.getvalue()
    )

    result = probe_contract(
        path,
        "November 2017.zip",
        "PE",
        10050,
        date(
            2017,
            10,
            26,
        ),
        date(
            2017,
            10,
            27,
        ),
    )

    assert result["exit"]["timestamp"].strftime(
        "%H:%M"
    ) == "09:16"

    assert result["exit"]["close"] == 49.80