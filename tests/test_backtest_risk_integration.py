from datetime import datetime

from backtest import (
    _calculate_trade,
)
from backtest_config import (
    BacktestConfig,
)


def _config() -> BacktestConfig:
    return BacktestConfig(
        lot_size=65,
        stop_loss_pct=0.15,
        target_pct=0.30,
        risk_per_trade_pct=0.05,
        max_allocation_pct=0.20,
        initial_capital=100000.0,
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

    # ₹10 risk per option.
    # ₹650 risk per lot.
    # ₹5,000 risk budget allows 7 lots.
    # Allocation cap:
    # 7 × 65 × ₹100 = ₹45,500.
    # Therefore allocation cap permits only 3 lots.
    assert trade.lots == 3
    assert trade.quantity == 195

    assert trade.capital_required == 19500.0

    # ₹20 profit per option × 195.
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

    assert trade is not None

    # Risk per option = ₹20.
    # Risk per lot = ₹1,300.
    # Risk budget = ₹1,000.
    # Therefore zero lots are allowed.
    #
    # The backtest must reject the trade instead of
    # silently trading a partial lot.
    assert trade is None


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

    # Risk per option = ₹5.
    # Risk per lot = ₹325.
    # ₹2,000 risk budget allows 6 lots.
    # Allocation cap allows 3 lots.
    assert trade.lots == 3
    assert trade.quantity == 195

    # ₹10 gain × 195 quantity.
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

    # Gross:
    # (110 - 100) × 195 = ₹1,950
    assert trade.gross_pnl == 1950.0

    # Costs:
    # (100 + 110) × 0.001 × 195
    assert trade.costs == 40.95

    assert trade.net_pnl == 1909.05