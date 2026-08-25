from datetime import date
import io
import zipfile

from btst_historical_backtest import (
    run_monthly_btst_baseline,
)


def _build_month_zip(path):
    option_data = "\n".join(
        [
            (
                "PE 10050,"
                "2017/10/26,15:00,"
                "55.00,56.00,54.00,55.55,100"
            ),
            (
                "PE 10050,"
                "2017/10/27,09:15,"
                "49.30,49.65,49.30,49.65,150"
            ),
            (
                "PE 10050,"
                "2017/10/27,15:00,"
                "50.00,51.00,49.00,50.00,100"
            ),
            (
                "PE 10050,"
                "2017/10/30,09:15,"
                "52.00,53.00,52.00,52.50,200"
            ),
        ]
    )

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

    path.write_bytes(
        buffer.getvalue()
    )


def test_monthly_btst_baseline_builds_overnight_trades(
    tmp_path,
):
    monthly_zip = (
        tmp_path / "November.2017.zip"
    )

    _build_month_zip(
        monthly_zip
    )

    trades = run_monthly_btst_baseline(
        monthly_zip
    )

    assert len(trades) == 2

    first = trades[0]

    assert first.option_type == "PE"
    assert first.strike == 10050.0

    assert first.entry_price == 55.55
    assert first.exit_price == 49.65

    assert first.entry_timestamp.date() == date(
        2017,
        10,
        26,
    )

    assert first.exit_timestamp.date() == date(
        2017,
        10,
        27,
    )


def test_monthly_btst_baseline_uses_next_observed_trading_day(
    tmp_path,
):
    monthly_zip = (
        tmp_path / "November.2017.zip"
    )

    _build_month_zip(
        monthly_zip
    )

    trades = run_monthly_btst_baseline(
        monthly_zip
    )

    second = trades[1]

    assert second.entry_timestamp.date() == date(
        2017,
        10,
        27,
    )

    assert second.exit_timestamp.date() == date(
        2017,
        10,
        30,
    )

    assert second.entry_price == 50.0
    assert second.exit_price == 52.5


def test_monthly_btst_baseline_rejects_missing_zip(
    tmp_path,
):
    missing = (
        tmp_path / "November.2017.zip"
    )

    try:
        run_monthly_btst_baseline(
            missing
        )
    except FileNotFoundError:
        return

    raise AssertionError(
        "Expected FileNotFoundError"
    )