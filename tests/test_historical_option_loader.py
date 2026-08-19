from datetime import datetime
import io
import zipfile

from historical_option_loader import (
    find_price_at_or_after,
    find_price_at_or_before,
    filter_contract,
    filter_rows_by_date,
    load_month_zip_bytes,
    parse_option_filename,
    parse_option_line,
    parse_option_text,
)


def test_parse_ce_filename():

    result = parse_option_filename(
        "CE 8250.txt"
    )

    assert result == {
        "option_type": "CE",
        "strike": 8250.0,
    }


def test_parse_pe_filename():

    result = parse_option_filename(
        "PE 18000.txt"
    )

    assert result == {
        "option_type": "PE",
        "strike": 18000.0,
    }


def test_invalid_filename():

    result = parse_option_filename(
        "random.txt"
    )

    assert result is None


def test_parse_option_line():

    row = parse_option_line(
        (
            "CE 8250,2017/01/05,15:00,"
            "100.4,101.0,99.5,100.8,150"
        ),
        "CE",
        8250,
    )

    assert row is not None

    assert row["option_type"] == "CE"
    assert row["strike"] == 8250.0
    assert row["close"] == 100.8
    assert row["volume"] == 150.0

    assert row["timestamp"] == datetime(
        2017,
        1,
        5,
        15,
        0,
    )


def test_parse_option_text():

    text = "\n".join(
        [
            (
                "CE 8250,2017/01/05,14:59,"
                "100,101,99,100.5,100"
            ),
            (
                "CE 8250,2017/01/05,15:00,"
                "101,102,100,101.5,200"
            ),
        ]
    )

    rows = parse_option_text(
        text,
        "CE 8250.txt",
    )

    assert len(rows) == 2
    assert rows[0]["close"] == 100.5
    assert rows[1]["close"] == 101.5


def test_load_month_zip_bytes():

    text = (
        "CE 8250,2017/01/05,15:00,"
        "100,101,99,100.5,100\n"
    )

    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:

        archive.writestr(
            "CE 8250.txt",
            text,
        )

        archive.writestr(
            "README.txt",
            "ignored",
        )

    rows = load_month_zip_bytes(
        buffer.getvalue()
    )

    assert len(rows) == 1
    assert rows[0]["option_type"] == "CE"
    assert rows[0]["strike"] == 8250.0


def test_filter_rows_by_date():

    rows = [
        {
            "timestamp": datetime(
                2017,
                1,
                5,
                14,
                59,
            ),
            "close": 100,
        },
        {
            "timestamp": datetime(
                2017,
                1,
                5,
                15,
                0,
            ),
            "close": 101,
        },
        {
            "timestamp": datetime(
                2017,
                1,
                6,
                9,
                15,
            ),
            "close": 105,
        },
    ]

    result = filter_rows_by_date(
        rows,
        start=datetime(
            2017,
            1,
            5,
            15,
            0,
        ),
        end=datetime(
            2017,
            1,
            5,
            15,
            0,
        ),
    )

    assert len(result) == 1
    assert result[0]["close"] == 101


def test_find_price_at_or_before():

    rows = [
        {
            "timestamp": datetime(
                2017,
                1,
                5,
                14,
                55,
            ),
            "close": 100,
        },
        {
            "timestamp": datetime(
                2017,
                1,
                5,
                14,
                59,
            ),
            "close": 101,
        },
        {
            "timestamp": datetime(
                2017,
                1,
                5,
                15,
                2,
            ),
            "close": 102,
        },
    ]

    result = find_price_at_or_before(
        rows,
        datetime(
            2017,
            1,
            5,
            15,
            0,
        ),
    )

    assert result is not None
    assert result["close"] == 101


def test_find_price_at_or_after():

    rows = [
        {
            "timestamp": datetime(
                2017,
                1,
                6,
                9,
                14,
            ),
            "close": 100,
        },
        {
            "timestamp": datetime(
                2017,
                1,
                6,
                9,
                17,
            ),
            "close": 105,
        },
    ]

    result = find_price_at_or_after(
        rows,
        datetime(
            2017,
            1,
            6,
            9,
            15,
        ),
    )

    assert result is not None
    assert result["close"] == 105


def test_filter_contract():

    rows = [
        {
            "option_type": "CE",
            "strike": 8250.0,
            "timestamp": datetime(
                2017,
                1,
                5,
                15,
                0,
            ),
            "close": 100,
        },
        {
            "option_type": "PE",
            "strike": 8250.0,
            "timestamp": datetime(
                2017,
                1,
                5,
                15,
                0,
            ),
            "close": 90,
        },
        {
            "option_type": "CE",
            "strike": 8300.0,
            "timestamp": datetime(
                2017,
                1,
                5,
                15,
                0,
            ),
            "close": 80,
        },
    ]

    result = filter_contract(
        rows,
        "CE",
        8250,
    )

    assert len(result) == 1
    assert result[0]["close"] == 100