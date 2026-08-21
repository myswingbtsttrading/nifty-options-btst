from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from backtest import BacktestResult, run_backtest
from backtest_config import BacktestConfig
from data_loader import _read_csv
from zenodo_option_data import load_month_contract


BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

NIFTY_FILE = DATA_DIR / "nifty.csv"
OPTIONS_FILE = DATA_DIR / "nifty_options.csv"

UNDERLYING_DATA = NIFTY_FILE
OPTIONS_DATA = OPTIONS_FILE


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def _load_underlying(
    path: Path,
) -> List[Dict[str, Any]]:
    return _read_csv(path)


def _load_options_from_zenodo(
    archive_path: Path,
    monthly_zip_name: str,
    option_type: str,
    strike: float,
) -> List[Dict[str, Any]]:
    return load_month_contract(
        year_zip_path=archive_path,
        monthly_zip_name=monthly_zip_name,
        option_type=option_type,
        strike=strike,
    )


def _select_entry_quote(
    rows: List[Dict[str, Any]],
) -> Dict[str, Any] | None:
    exact = [
        row
        for row in rows
        if (
            row["timestamp"].hour == 15
            and row["timestamp"].minute == 0
        )
    ]

    if exact:
        return min(
            exact,
            key=lambda row: row["timestamp"],
        )

    candidates = [
        row
        for row in rows
        if (
            row["timestamp"].hour,
            row["timestamp"].minute,
        )
        <= (15, 0)
    ]

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda row: row["timestamp"],
    )


def _select_exit_quote(
    rows: List[Dict[str, Any]],
) -> Dict[str, Any] | None:
    candidates = [
        row
        for row in rows
        if (
            row["timestamp"].hour,
            row["timestamp"].minute,
        )
        >= (9, 15)
    ]

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda row: row["timestamp"],
    )


def run_zenodo_btst_probe(
    archive_path: str | Path,
    monthly_zip_name: str,
    option_type: str,
    strike: float,
    entry_date: date,
    exit_date: date,
) -> Dict[str, Any]:

    archive_path = Path(archive_path)

    rows = _load_options_from_zenodo(
        archive_path=archive_path,
        monthly_zip_name=monthly_zip_name,
        option_type=option_type,
        strike=strike,
    )

    entry_rows = [
        row
        for row in rows
        if row["timestamp"].date() == entry_date
    ]

    exit_rows = [
        row
        for row in rows
        if row["timestamp"].date() == exit_date
    ]

    if not entry_rows:
        raise ValueError(
            f"No option data found for entry date "
            f"{entry_date}"
        )

    if not exit_rows:
        raise ValueError(
            f"No option data found for exit date "
            f"{exit_date}"
        )

    entry = _select_entry_quote(
        entry_rows
    )

    exit_ = _select_exit_quote(
        exit_rows
    )

    if entry is None:
        raise ValueError(
            f"No entry observation at or before 15:00 "
            f"on {entry_date}"
        )

    if exit_ is None:
        raise ValueError(
            f"No exit observation at or after 09:15 "
            f"on {exit_date}"
        )

    return {
        "archive": archive_path.name,
        "monthly_zip": monthly_zip_name,
        "option_type": option_type.upper(),
        "strike": float(strike),
        "expiry": rows[0]["expiry"],
        "entry": entry,
        "exit": exit_,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NIFTY Options BTST backtest runner"
    )

    parser.add_argument(
        "--underlying",
        type=Path,
        default=NIFTY_FILE,
    )

    parser.add_argument(
        "--options",
        type=Path,
        default=OPTIONS_FILE,
    )

    parser.add_argument(
        "--zenodo-year-zip",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--zenodo-month-zip",
        type=str,
        default=None,
    )

    parser.add_argument(
        "--zenodo-option-type",
        type=str,
        default="PE",
    )

    parser.add_argument(
        "--zenodo-strike",
        type=float,
        default=None,
    )

    parser.add_argument(
        "--zenodo-entry-date",
        type=str,
        default=None,
    )

    parser.add_argument(
        "--zenodo-exit-date",
        type=str,
        default=None,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backtest_result.json"),
    )

    args = parser.parse_args()

    zenodo_arguments = (
        args.zenodo_year_zip,
        args.zenodo_month_zip,
        args.zenodo_strike,
        args.zenodo_entry_date,
        args.zenodo_exit_date,
    )

    if all(
        value is not None
        for value in zenodo_arguments
    ):
        result = run_zenodo_btst_probe(
            archive_path=args.zenodo_year_zip,
            monthly_zip_name=args.zenodo_month_zip,
            option_type=args.zenodo_option_type,
            strike=args.zenodo_strike,
            entry_date=date.fromisoformat(
                args.zenodo_entry_date
            ),
            exit_date=date.fromisoformat(
                args.zenodo_exit_date
            ),
        )

        print(
            json.dumps(
                result,
                default=str,
                indent=2,
            )
        )

        return

    underlying_rows = _load_underlying(
        args.underlying
    )

    option_rows = _read_csv(
        args.options
    )

    result: BacktestResult = run_backtest(
        underlying_rows=underlying_rows,
        option_rows=option_rows,
        config=BacktestConfig(),
    )

    payload = asdict(result)

    with args.output.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            payload,
            handle,
            default=str,
            indent=2,
        )

    print(
        json.dumps(
            payload,
            default=str,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()