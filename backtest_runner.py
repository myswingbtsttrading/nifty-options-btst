from pathlib import Path

from backtest import (
    format_backtest_report,
    run_backtest,
)
from backtest_config import DEFAULT_CONFIG
from historical_data import (
    load_nifty_history,
    load_nifty_option_history,
    validate_historical_data,
)


DATA_DIR = Path("data")

NIFTY_FILE = DATA_DIR / "nifty.csv"
OPTIONS_FILE = DATA_DIR / "nifty_options.csv"


def main() -> None:
    print("NIFTY OPTIONS BTST BACKTEST")
    print("=" * 40)

    if not NIFTY_FILE.exists():
        raise FileNotFoundError(
            f"Missing historical NIFTY data: {NIFTY_FILE}"
        )

    if not OPTIONS_FILE.exists():
        raise FileNotFoundError(
            f"Missing historical options data: {OPTIONS_FILE}"
        )

    nifty = load_nifty_history(
        NIFTY_FILE
    )

    options = load_nifty_option_history(
        OPTIONS_FILE
    )

    validation = validate_historical_data(
        nifty,
        options,
    )

    print(
        f"NIFTY rows: "
        f"{validation['underlying_rows']}"
    )

    print(
        f"Option rows: "
        f"{validation['option_rows']}"
    )

    print(
        f"NIFTY dates: "
        f"{validation['underlying_dates']}"
    )

    print(
        f"Option dates: "
        f"{validation['option_dates']}"
    )

    print(
        f"Overlapping dates: "
        f"{validation['overlapping_dates']}"
    )

    print(
        f"Option types: "
        f"{', '.join(validation['option_types'])}"
    )

    if validation["overlapping_dates"] == 0:
        raise ValueError(
            "NIFTY and option data have no overlapping dates."
        )

    result = run_backtest(
        underlying_rows=nifty,
        option_rows=options,
        config=DEFAULT_CONFIG,
    )

    print()
    print(format_backtest_report(result))


if __name__ == "__main__":
    main()