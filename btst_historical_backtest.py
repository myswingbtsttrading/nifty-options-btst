from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from pathlib import Path
from statistics import mean, median
from typing import Dict, Iterable, List, Tuple
import json

from historical_option_loader import (
    load_month_zip,
    parse_monthly_zip_filename,
)


ENTRY_TIME = time(15, 0)
EXIT_TIME = time(9, 15)


@dataclass(frozen=True)
class BTSTTrade:
    expiry: date
    option_type: str
    strike: float
    entry_timestamp: datetime
    exit_timestamp: datetime
    entry_price: float
    exit_price: float
    return_pct: float


def _group_contract_rows(
    rows: Iterable[Dict[str, object]],
) -> Dict[Tuple[str, float], List[Dict[str, object]]]:
    grouped: Dict[
        Tuple[str, float],
        List[Dict[str, object]],
    ] = {}

    for row in rows:
        option_type = str(
            row.get("option_type", "")
        ).upper()

        try:
            strike = float(row["strike"])
        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            continue

        timestamp = row.get("timestamp")

        if not isinstance(timestamp, datetime):
            continue

        grouped.setdefault(
            (option_type, strike),
            [],
        ).append(row)

    for contract_rows in grouped.values():
        contract_rows.sort(
            key=lambda row: row["timestamp"]
        )

    return grouped


def _entry_quote(
    rows: List[Dict[str, object]],
    trading_date: date,
) -> Dict[str, object] | None:
    candidates = [
        row
        for row in rows
        if isinstance(
            row.get("timestamp"),
            datetime,
        )
        and row["timestamp"].date() == trading_date
        and row["timestamp"].time() <= ENTRY_TIME
    ]

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda row: row["timestamp"],
    )


def _next_trading_date(
    rows: List[Dict[str, object]],
    trading_date: date,
) -> date | None:
    dates = sorted(
        {
            row["timestamp"].date()
            for row in rows
            if isinstance(
                row.get("timestamp"),
                datetime,
            )
            and row["timestamp"].date() > trading_date
        }
    )

    if not dates:
        return None

    return dates[0]


def _exit_quote(
    rows: List[Dict[str, object]],
    trading_date: date,
) -> Dict[str, object] | None:
    candidates = [
        row
        for row in rows
        if isinstance(
            row.get("timestamp"),
            datetime,
        )
        and row["timestamp"].date() == trading_date
        and row["timestamp"].time() >= EXIT_TIME
    ]

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda row: row["timestamp"],
    )


def _build_contract_trades(
    rows: List[Dict[str, object]],
    expiry: date,
) -> List[BTSTTrade]:
    if not rows:
        return []

    trading_dates = sorted(
        {
            row["timestamp"].date()
            for row in rows
            if isinstance(
                row.get("timestamp"),
                datetime,
            )
        }
    )

    trades: List[BTSTTrade] = []

    for trading_date in trading_dates:
        entry = _entry_quote(
            rows,
            trading_date,
        )

        if entry is None:
            continue

        next_date = _next_trading_date(
            rows,
            trading_date,
        )

        if next_date is None:
            continue

        exit_ = _exit_quote(
            rows,
            next_date,
        )

        if exit_ is None:
            continue

        try:
            entry_price = float(
                entry["close"]
            )
            exit_price = float(
                exit_["close"]
            )
        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            continue

        if entry_price <= 0 or exit_price <= 0:
            continue

        return_pct = (
            (exit_price / entry_price) - 1.0
        ) * 100.0

        trades.append(
            BTSTTrade(
                expiry=expiry,
                option_type=str(
                    entry["option_type"]
                ).upper(),
                strike=float(
                    entry["strike"]
                ),
                entry_timestamp=entry[
                    "timestamp"
                ],
                exit_timestamp=exit_[
                    "timestamp"
                ],
                entry_price=entry_price,
                exit_price=exit_price,
                return_pct=return_pct,
            )
        )

    return trades


def run_monthly_btst_baseline(
    monthly_zip: str | Path,
) -> List[BTSTTrade]:
    monthly_zip = Path(monthly_zip)

    if not monthly_zip.exists():
        raise FileNotFoundError(
            f"Monthly ZIP not found: "
            f"{monthly_zip}"
        )

    expiry = parse_monthly_zip_filename(
        monthly_zip.name
    )

    if expiry is None:
        raise ValueError(
            f"Invalid monthly ZIP name: "
            f"{monthly_zip.name}"
        )

    rows = load_month_zip(
        monthly_zip,
        expiry=expiry,
    )

    grouped = _group_contract_rows(
        rows
    )

    trades: List[BTSTTrade] = []

    for contract_rows in grouped.values():
        trades.extend(
            _build_contract_trades(
                contract_rows,
                expiry,
            )
        )

    trades.sort(
        key=lambda trade: (
            trade.entry_timestamp,
            trade.expiry,
            trade.option_type,
            trade.strike,
        )
    )

    return trades


def run_2017_btst_baseline(
    release_dir: str | Path,
) -> Dict[str, object]:
    release_dir = Path(release_dir)

    if not release_dir.exists():
        raise FileNotFoundError(
            f"Release directory not found: "
            f"{release_dir}"
        )

    monthly_zips = sorted(
        release_dir.glob("*.zip"),
        key=lambda path: path.name.lower(),
    )

    monthly_zips = [
        path
        for path in monthly_zips
        if parse_monthly_zip_filename(
            path.name
        ) is not None
    ]

    if len(monthly_zips) != 12:
        raise ValueError(
            "Expected exactly 12 monthly 2017 ZIP files, "
            f"found {len(monthly_zips)}"
        )

    all_trades: List[BTSTTrade] = []
    monthly_counts: Dict[str, int] = {}

    for monthly_zip in monthly_zips:
        trades = run_monthly_btst_baseline(
            monthly_zip
        )

        monthly_counts[
            monthly_zip.name
        ] = len(trades)

        all_trades.extend(trades)

    returns = [
        trade.return_pct
        for trade in all_trades
    ]

    wins = [
        value
        for value in returns
        if value > 0
    ]

    losses = [
        value
        for value in returns
        if value < 0
    ]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        profit_factor = (
            gross_profit / gross_loss
        )
    else:
        profit_factor = None

    if returns:
        average_return = mean(returns)
        median_return = median(returns)
        best_return = max(returns)
        worst_return = min(returns)
    else:
        average_return = 0.0
        median_return = 0.0
        best_return = 0.0
        worst_return = 0.0

    total_trades = len(all_trades)
    win_count = len(wins)
    loss_count = len(losses)

    win_rate = (
        (win_count / total_trades) * 100.0
        if total_trades
        else 0.0
    )

    result = {
        "year": 2017,
        "monthly_files": [
            path.name
            for path in monthly_zips
        ],
        "monthly_trade_counts": monthly_counts,
        "total_trades": total_trades,
        "wins": win_count,
        "losses": loss_count,
        "win_rate_pct": win_rate,
        "average_return_pct": average_return,
        "median_return_pct": median_return,
        "best_return_pct": best_return,
        "worst_return_pct": worst_return,
        "gross_profit_pct": gross_profit,
        "gross_loss_pct": gross_loss,
        "profit_factor": profit_factor,
        "trades": [
            asdict(trade)
            for trade in all_trades
        ],
    }

    return result


def write_json_report(
    result: Dict[str, object],
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file_obj:
        json.dump(
            result,
            file_obj,
            indent=2,
            default=str,
        )

    return output_path


def print_summary(
    result: Dict[str, object],
) -> None:
    print(
        "2017 HISTORICAL BTST BASELINE"
    )
    print(
        "============================="
    )
    print(
        f"Monthly ZIPs: "
        f"{len(result['monthly_files'])}"
    )
    print(
        f"Trades: "
        f"{result['total_trades']}"
    )
    print(
        f"Wins: "
        f"{result['wins']}"
    )
    print(
        f"Losses: "
        f"{result['losses']}"
    )
    print(
        f"Win rate: "
        f"{result['win_rate_pct']:.2f}%"
    )
    print(
        f"Average overnight return: "
        f"{result['average_return_pct']:.4f}%"
    )
    print(
        f"Median overnight return: "
        f"{result['median_return_pct']:.4f}%"
    )
    print(
        f"Best return: "
        f"{result['best_return_pct']:.4f}%"
    )
    print(
        f"Worst return: "
        f"{result['worst_return_pct']:.4f}%"
    )

    profit_factor = result[
        "profit_factor"
    ]

    if profit_factor is None:
        print(
            "Profit factor: N/A"
        )
    else:
        print(
            f"Profit factor: "
            f"{profit_factor:.4f}"
        )

    print()
    print("Monthly trade counts:")

    monthly_counts = result[
        "monthly_trade_counts"
    ]

    for name in sorted(
        monthly_counts
    ):
        print(
            f"- {name}: "
            f"{monthly_counts[name]}"
        )


if __name__ == "__main__":
    result = run_2017_btst_baseline(
        "release-data"
    )

    write_json_report(
        result,
        "artifacts/btst_2017_baseline.json",
    )

    print_summary(result)

    print()
    print("STATUS: PASS")