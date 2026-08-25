from datetime import datetime

import pytest

from backtest import (
    _calculate_trade,
)
from backtest_config import (
    BacktestConfig,
)


def test_backtest_trade_uses_multiple_lots_when_allowed():
    entry_quote = {
        "timestamp": datetime(
            2026,
            8,
            24,
            15,
            0,
        ),
        "strike": 25000,
        "option_type": "CE",
        "expiry": "2026-08-27",
        "close": 100.0,
    }

    exit_quote = {
        "timestamp": datetime(
            2026,
            8,
            25,
            9,
            15,
        ),
        "strike": 25000,
        "option_type": "CE",
        "expiry": "2026-08-27",
        "close": 120.0,
    }

    config = BacktestConfig(
        lot_size=65,
        stop_loss_pct=0.10,
        target_pct=0.20,
        risk_per_trade_pct=0.05,
        max_allocation_pct=0.20,
        entry_slippage_pct=0.0,
        exit_slippage_pct=0.0,
        brokerage_and_cost_pct=0.0,
    )

    trade = _calculate_trade(
        entry_quote=entry_quote,
        exit_quote=exit_quote,
        direction="CE",
        confidence=80.0,
        reason="test",
        capital=100000.0,
        config=config,
    )

    assert trade is not None

    assert trade.lots == 3
    assert trade.quantity == 195

    assert trade.capital_required == 19500.0

    assert trade.gross_pnl == 3900.0

    assert trade.costs == 0.0
    assert trade.net_pnl == 3900.0


def test_backtest_trade_respects_risk_budget():
    entry_quote = {
        "timestamp": datetime(
            2026,
            8,
            24,
            15,
            0,
        ),
        "strike": 25000,
        "option_type": "PE",
        "expiry": "2026-08-27",
        "close": 200.0,
    }

    exit_quote = {
        "timestamp": datetime(
            2026,
            8,
            25,
            9,
            15,
        ),
        "strike": 25000,
        "option_type": "PE",
        "expiry": "2026-08-27",
        "close": 180.0,
    }

    config = BacktestConfig(
        lot_size=65,
        stop_loss_pct=0.10,
        target_pct=0.20,
        risk_per_trade_pct=0.01,
        max_allocation_pct=0.50,
        entry_slippage_pct=0.0,
        exit_slippage_pct=0.0,
        brokerage_and_cost_pct=0.0,
    )

    trade = _calculate_trade(
        entry_quote=entry_quote,
        exit_quote=exit_quote,
        direction="PE",
        confidence=80.0,
        reason="test",
        capital=100000.0,
        config=config,
    )

    # Risk per option = ₹20.
    # Risk per lot = ₹20 × 65 = ₹1,300.
    # Risk budget = ₹1,000.
    #
    # One complete lot already exceeds the risk budget,
    # so the risk engine correctly rejects the trade.
    assert trade is None


def test_backtest_trade_rejects_when_one_lot_exceeds_risk_budget():
    entry_quote = {
        "timestamp": datetime(
            2026,
            8,
            24,
            15,
            0,
        ),
        "strike": 25000,
        "option_type": "PE",
        "expiry": "2026-08-27",
        "close": 200.0,
    }

    exit_quote = {
        "timestamp": datetime(
            2026,
            8,
            25,
            9,
            15,
        ),
        "strike": 25000,
        "option_type": "PE",
        "expiry": "2026-08-27",
        "close": 180.0,
    }

    config = BacktestConfig(
        lot_size=65,
        stop_loss_pct=0.10,
        target_pct=0.20,
        risk_per_trade_pct=0.01,
        max_allocation_pct=0.50,
        entry_slippage_pct=0.0,
        exit_slippage_pct=0.0,
        brokerage_and_cost_pct=0.0,
    )

    trade = _calculate_trade(
        entry_quote=entry_quote,
        exit_quote=exit_quote,
        direction="PE",
        confidence=80.0,
        reason="test",
        capital=100000.0,
        config=config,
    )

    assert trade is None


def test_backtest_trade_uses_risk_budget_when_one_lot_fits():
    entry_quote = {
        "timestamp": datetime(
            2026,
            8,
            24,
            15,
            0,
        ),
        "strike": 25000,
        "option_type": "PE",
        "expiry": "2026-08-27",
        "close": 100.0,
    }

    exit_quote = {
        "timestamp": datetime(
            2026,
            8,
            25,
            9,
            15,
        ),
        "strike": 25000,
        "option_type": "PE",
        "expiry": "2026-08-27",
        "close": 90.0,
    }

    config = BacktestConfig(
        lot_size=65,
        stop_loss_pct=0.10,
        target_pct=0.20,
        risk_per_trade_pct=0.01,
        max_allocation_pct=0.50,
        entry_slippage_pct=0.0,
        exit_slippage_pct=0.0,
        brokerage_and_cost_pct=0.0,
    )

    trade = _calculate_trade(
        entry_quote=entry_quote,
        exit_quote=exit_quote,
        direction="PE",
        confidence=80.0,
        reason="test",
        capital=100000.0,
        config=config,
    )

    assert trade is not None

    # Risk per option = ₹10.
    # Risk per lot = ₹650.
    # Risk budget = ₹1,000.
    # One lot fits, but two lots would exceed the risk budget.
    assert trade.lots == 1
    assert trade.quantity == 65

    assert trade.capital_required == 6500.0
    assert trade.planned_risk == 650.0


def test_backtest_trade_applies_quantity_to_pnl():
    entry_quote = {
        "timestamp": datetime(
            2026,
            8,
            24,
            15,
            0,
        ),
        "strike": 25000,
        "option_type": "CE",
        "expiry": "2026-08-27",
        "close": 100.0,
    }

    exit_quote = {
        "timestamp": datetime(
            2026,
            8,
            25,
            9,
            15,
        ),
        "strike": 25000,
        "option_type": "CE",
        "expiry": "2026-08-27",
        "close": 110.0,
    }

    config = BacktestConfig(
        lot_size=65,
        stop_loss_pct=0.05,
        target_pct=0.10,
        risk_per_trade_pct=0.02,
        max_allocation_pct=0.20,
        entry_slippage_pct=0.0,
        exit_slippage_pct=0.0,
        brokerage_and_cost_pct=0.0,
    )

    trade = _calculate_trade(
        entry_quote=entry_quote,
        exit_quote=exit_quote,
        direction="CE",
        confidence=80.0,
        reason="test",
        capital=100000.0,
        config=config,
    )

    assert trade is not None

    assert trade.lots == 3
    assert trade.quantity == 195

    assert trade.gross_pnl == 1950.0


def test_backtest_trade_includes_transaction_costs():
    entry_quote = {
        "timestamp": datetime(
            2026,
            8,
            24,
            15,
            0,
        ),
        "strike": 25000,
        "option_type": "CE",
        "expiry": "2026-08-27",
        "close": 100.0,
    }

    exit_quote = {
        "timestamp": datetime(
            2026,
            8,
            25,
            9,
            15,
        ),
        "strike": 25000,
        "option_type": "CE",
        "expiry": "2026-08-27",
        "close": 110.0,
    }

    config = BacktestConfig(
        lot_size=65,
        stop_loss_pct=0.05,
        target_pct=0.10,
        risk_per_trade_pct=0.02,
        max_allocation_pct=0.20,
        entry_slippage_pct=0.0,
        exit_slippage_pct=0.0,
        brokerage_and_cost_pct=0.001,
    )

    trade = _calculate_trade(
        entry_quote=entry_quote,
        exit_quote=exit_quote,
        direction="CE",
        confidence=80.0,
        reason="test",
        capital=100000.0,
        config=config,
    )

    assert trade is not None

    assert trade.quantity == 195

    assert trade.gross_pnl == 1950.0

    # Floating-point arithmetic can produce
    # 40.949999999999996 internally.
    assert trade.costs == pytest.approx(
        40.95,
        abs=1e-9,
    )

    assert trade.net_pnl == pytest.approx(
        1909.05,
        abs=1e-9,
    )