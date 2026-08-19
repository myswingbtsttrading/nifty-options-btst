from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from zenodo_contract_probe import probe_contract


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe one real Zenodo NIFTY options contract."
    )

    parser.add_argument(
        "zip_path",
        help="Path to NiftyOptions 2017.zip",
    )

    parser.add_argument(
        "--month-zip",
        default="November 2017.zip",
    )

    parser.add_argument(
        "--option-type",
        default="PE",
        choices=["CE", "PE"],
    )

    parser.add_argument(
        "--strike",
        type=float,
        default=10050,
    )

    parser.add_argument(
        "--entry-date",
        type=parse_date,
        default=date(2017, 10, 26),
    )

    parser.add_argument(
        "--next-date",
        type=parse_date,
        default=date(2017, 10, 27),
    )

    parser.add_argument(
        "--entry-time",
        default="15:00",
    )

    parser.add_argument(
        "--exit-time",
        default="09:15",
    )

    args = parser.parse_args()

    zip_path = Path(args.zip_path)

    if not zip_path.exists():
        print(
            f"ERROR: ZIP file not found: {zip_path}"
        )
        return 1

    try:
        result = probe_contract(
            zip_path,
            args.month_zip,
            args.option_type,
            args.strike,
            args.entry_date,
            args.next_date,
            args.entry_time,
            args.exit_time,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    entry = result["entry"]
    exit_ = result["exit"]

    print()
    print("=" * 60)
    print("ZENODO REAL-DATA CONTRACT PROBE")
    print("=" * 60)

    print(
        f"Contract: {result['option_type']} "
        f"{result['strike']:.0f}"
    )

    print(
        f"Expiry:   {result['expiry'].isoformat()}"
    )

    print()
    print("ENTRY")
    print("-" * 60)

    print(
        f"Requested: "
        f"{result['entry_requested']}"
    )

    if entry is None:
        print("Actual:    NOT FOUND")
        print("Price:     NOT FOUND")
        print()
        print("STATUS: FAIL")
        return 1

    print(
        f"Actual:    {entry['timestamp']}"
    )

    print(
        f"Price:     ₹{float(entry['close']):.2f}"
    )

    print()
    print("NEXT MORNING")
    print("-" * 60)

    print(
        f"Requested: "
        f"{result['exit_requested']}"
    )

    if exit_ is None:
        print("Actual:    NOT FOUND")
        print("Price:     NOT FOUND")
        print()
        print("STATUS: FAIL")
        return 1

    print(
        f"Actual:    {exit_['timestamp']}"
    )

    print(
        f"Price:     ₹{float(exit_['close']):.2f}"
    )

    print()
    print("=" * 60)
    print("STATUS: PASS")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())