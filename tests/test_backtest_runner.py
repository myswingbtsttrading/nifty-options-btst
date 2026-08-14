from pathlib import Path

import backtest_runner


def test_backtest_runner_paths():
    assert isinstance(
        backtest_runner.DATA_DIR,
        Path,
    )

    assert (
        backtest_runner.NIFTY_FILE.name
        == "nifty.csv"
    )

    assert (
        backtest_runner.OPTIONS_FILE.name
        == "nifty_options.csv"
    )