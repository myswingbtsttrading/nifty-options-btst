from __future__ import annotations

import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional

from historical_option_loader import (
    find_price_at_or_after,
    find_price_at_or_before,
    filter_contract,
    load_month_zip_bytes,
    parse_monthly_zip_filename,
)


def probe_contract(
    year_zip_path: str | Path,
    monthly_zip_name: str,
    option_type: str,
    strike: float,
    entry_date: date,
    next_trading_date: date,
    entry_time: str = "15:00",
    exit_time: str = "09:15",
) -> Dict[str, object]:
    """
    Probe one real Zenodo contract.

    Entry:
        latest available observation at or before entry_time.

    Exit:
        first available observation at or after exit_time
        on the following trading day.
    """

    monthly_expiry = parse_monthly_zip_filename(
        monthly_zip_name
    )

    if monthly_expiry is None:
        raise ValueError(
            f"Invalid monthly ZIP name: {monthly_zip_name}"
        )

    entry_clock = datetime.strptime(
        entry_time,
        "%H:%M",
    ).time()

    exit_clock = datetime.strptime(
        exit_time,
        "%H:%M",
    ).time()

    entry_timestamp = datetime.combine(
        entry_date,
        entry_clock,
    )

    exit_timestamp = datetime.combine(
        next_trading_date,
        exit_clock,
    )

    with zipfile.ZipFile(
        year_zip_path
    ) as year_archive:

        if monthly_zip_name not in year_archive.namelist():
            raise FileNotFoundError(
                monthly_zip_name
            )

        monthly_bytes = year_archive.read(
            monthly_zip_name
        )

    rows = load_month_zip_bytes(
        monthly_bytes,
        monthly_expiry,
    )

    contract_rows = filter_contract(
        rows,
        option_type,
        strike,
        monthly_expiry,
    )

    if not contract_rows:
        raise ValueError(
            "Contract not found: "
            f"{option_type} {strike} "
            f"expiry {monthly_expiry}"
        )

    entry_rows = [
        row
        for row in contract_rows
        if row["timestamp"].date()
        == entry_date
    ]

    exit_rows = [
        row
        for row in contract_rows
        if row["timestamp"].date()
        == next_trading_date
    ]

    entry = find_price_at_or_before(
        entry_rows,
        entry_timestamp,
    )

    exit_ = find_price_at_or_after(
        exit_rows,
        exit_timestamp,
    )

    return {
        "option_type": option_type.upper(),
        "strike": float(strike),
        "expiry": monthly_expiry,
        "entry": entry,
        "exit": exit_,
        "entry_requested": entry_timestamp,
        "exit_requested": exit_timestamp,
    }