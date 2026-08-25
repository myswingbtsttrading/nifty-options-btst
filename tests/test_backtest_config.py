import pytest

from backtest_config import (
    BacktestConfig,
)


def test_default_config():
    config = BacktestConfig()

    assert config.entry_hour == 15
    assert config.entry_minute == 0

    assert config.exit_hour == 9
    assert config.exit_minute == 15

    assert config.lot_size == 65

    assert config.initial_capital == 100000.0
    assert config.minimum_confidence == 65.0

    assert config.stop_loss_pct == 0.15
    assert config.target_pct == 0.30

    assert config.risk_per_trade_pct == 0.01
    assert config.max_allocation_pct == 0.20


def test_invalid_lot_size():
    with pytest.raises(ValueError):
        BacktestConfig(
            lot_size=0,
        )


def test_invalid_capital():
    with pytest.raises(ValueError):
        BacktestConfig(
            initial_capital=0,
        )


def test_invalid_entry_hour():
    with pytest.raises(ValueError):
        BacktestConfig(
            entry_hour=24,
        )


def test_invalid_exit_hour():
    with pytest.raises(ValueError):
        BacktestConfig(
            exit_hour=24,
        )


def test_invalid_entry_minute():
    with pytest.raises(ValueError):
        BacktestConfig(
            entry_minute=60,
        )


def test_invalid_exit_minute():
    with pytest.raises(ValueError):
        BacktestConfig(
            exit_minute=60,
        )


def test_invalid_strike_interval():
    with pytest.raises(ValueError):
        BacktestConfig(
            strike_interval=0,
        )


def test_negative_entry_slippage():
    with pytest.raises(ValueError):
        BacktestConfig(
            entry_slippage_pct=-0.01,
        )


def test_negative_exit_slippage():
    with pytest.raises(ValueError):
        BacktestConfig(
            exit_slippage_pct=-0.01,
        )


def test_negative_cost():
    with pytest.raises(ValueError):
        BacktestConfig(
            brokerage_and_cost_pct=-0.01,
        )


def test_invalid_stop_loss():
    with pytest.raises(ValueError):
        BacktestConfig(
            stop_loss_pct=0,
        )


def test_invalid_target():
    with pytest.raises(ValueError):
        BacktestConfig(
            target_pct=0,
        )


def test_invalid_risk_percentage():
    with pytest.raises(ValueError):
        BacktestConfig(
            risk_per_trade_pct=0,
        )


def test_invalid_allocation_percentage():
    with pytest.raises(ValueError):
        BacktestConfig(
            max_allocation_pct=0,
        )