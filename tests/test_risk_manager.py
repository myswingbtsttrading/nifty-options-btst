import pytest

from risk_manager import (
    RiskConfig,
    TradePlan,
    calculate_stop_loss,
    calculate_target,
    calculate_trade_plan,
)


def test_stop_loss():
    assert calculate_stop_loss(
        entry_price=200,
        stop_loss_pct=0.15,
    ) == 170.0


def test_target():
    assert calculate_target(
        entry_price=200,
        target_pct=0.30,
    ) == 260.0


def test_default_trade_plan():
    plan = calculate_trade_plan(
        entry_price=200,
        capital=100000,
        lot_size=65,
    )

    assert isinstance(plan, TradePlan)

    assert plan.entry_price == 200.0
    assert plan.stop_loss == 170.0
    assert plan.target == 260.0

    assert plan.risk_per_unit == 30.0
    assert plan.reward_per_unit == 60.0
    assert plan.risk_reward_ratio == 2.0

    assert plan.risk_budget == 1000.0
    assert plan.max_allocation == 20000.0

    # Risk allows:
    # 1000 / (30 × 65) = 0.51 lots -> 0 lots.
    assert plan.lots == 0
    assert plan.quantity == 0
    assert plan.is_tradeable is False


def test_trade_plan_with_larger_risk_budget():
    config = RiskConfig(
        stop_loss_pct=0.15,
        target_pct=0.30,
        risk_per_trade_pct=0.05,
        max_allocation_pct=0.20,
    )

    plan = calculate_trade_plan(
        entry_price=200,
        capital=100000,
        lot_size=65,
        config=config,
    )

    # Risk budget = ₹5,000.
    # Risk per lot = 30 × 65 = ₹1,950.
    # 2 lots fit the risk budget.
    assert plan.lots == 2
    assert plan.quantity == 130

    assert plan.capital_required == 26000.0
    assert plan.planned_risk == 3900.0
    assert plan.planned_reward == 7800.0

    assert plan.is_tradeable is True


def test_capital_allocation_limits_position():
    config = RiskConfig(
        stop_loss_pct=0.05,
        target_pct=0.10,
        risk_per_trade_pct=0.50,
        max_allocation_pct=0.20,
    )

    plan = calculate_trade_plan(
        entry_price=200,
        capital=100000,
        lot_size=65,
        config=config,
    )

    # Risk budget would permit many lots, but allocation
    # is capped at ₹20,000.
    #
    # 20,000 / (200 × 65) = 1 lot.
    assert plan.lots == 1
    assert plan.quantity == 65
    assert plan.capital_required == 13000.0
    assert plan.allocation_pct_of_capital == 13.0


def test_risk_limit_reduces_position_size():
    config = RiskConfig(
        stop_loss_pct=0.10,
        target_pct=0.20,
        risk_per_trade_pct=0.01,
        max_allocation_pct=0.50,
    )

    plan = calculate_trade_plan(
        entry_price=100,
        capital=100000,
        lot_size=65,
        config=config,
    )

    # Risk budget = ₹1,000.
    # Risk per lot = ₹650.
    # One lot fits; two lots do not.
    assert plan.lots == 1
    assert plan.quantity == 65
    assert plan.planned_risk == 650.0


def test_trade_plan_can_have_zero_lots():
    config = RiskConfig(
        stop_loss_pct=0.20,
        target_pct=0.40,
        risk_per_trade_pct=0.01,
        max_allocation_pct=0.20,
    )

    plan = calculate_trade_plan(
        entry_price=500,
        capital=100000,
        lot_size=65,
        config=config,
    )

    # Risk per lot = 100 × 65 = ₹6,500.
    # Risk budget = ₹1,000.
    assert plan.lots == 0
    assert plan.quantity == 0
    assert plan.capital_required == 0.0
    assert plan.planned_risk == 0.0
    assert plan.planned_reward == 0.0
    assert plan.is_tradeable is False


def test_custom_risk_reward():
    config = RiskConfig(
        stop_loss_pct=0.10,
        target_pct=0.25,
        risk_per_trade_pct=0.05,
        max_allocation_pct=0.20,
    )

    plan = calculate_trade_plan(
        entry_price=200,
        capital=100000,
        lot_size=65,
        config=config,
    )

    assert plan.stop_loss == 180.0
    assert plan.target == 250.0
    assert plan.risk_per_unit == 20.0
    assert plan.reward_per_unit == 50.0
    assert plan.risk_reward_ratio == 2.5


def test_invalid_entry_price():
    with pytest.raises(ValueError):
        calculate_trade_plan(
            entry_price=0,
            capital=100000,
            lot_size=65,
        )


def test_negative_entry_price():
    with pytest.raises(ValueError):
        calculate_trade_plan(
            entry_price=-100,
            capital=100000,
            lot_size=65,
        )


def test_invalid_capital():
    with pytest.raises(ValueError):
        calculate_trade_plan(
            entry_price=200,
            capital=0,
            lot_size=65,
        )


def test_invalid_lot_size():
    with pytest.raises(ValueError):
        calculate_trade_plan(
            entry_price=200,
            capital=100000,
            lot_size=0,
        )


def test_non_integer_lot_size():
    with pytest.raises(ValueError):
        calculate_trade_plan(
            entry_price=200,
            capital=100000,
            lot_size=65.0,
        )


def test_invalid_stop_loss_percentage():
    with pytest.raises(ValueError):
        RiskConfig(
            stop_loss_pct=0,
        )


def test_stop_loss_percentage_cannot_reach_100_percent():
    with pytest.raises(ValueError):
        RiskConfig(
            stop_loss_pct=1,
        )


def test_invalid_target():
    with pytest.raises(ValueError):
        RiskConfig(
            target_pct=0,
        )


def test_invalid_risk_percentage():
    with pytest.raises(ValueError):
        RiskConfig(
            risk_per_trade_pct=0,
        )


def test_risk_percentage_cannot_exceed_100_percent():
    with pytest.raises(ValueError):
        RiskConfig(
            risk_per_trade_pct=1.01,
        )


def test_invalid_allocation_percentage():
    with pytest.raises(ValueError):
        RiskConfig(
            max_allocation_pct=0,
        )


def test_allocation_percentage_cannot_exceed_100_percent():
    with pytest.raises(ValueError):
        RiskConfig(
            max_allocation_pct=1.01,
        )


def test_stop_loss_rejects_invalid_price():
    with pytest.raises(ValueError):
        calculate_stop_loss(
            entry_price=0,
        )


def test_target_rejects_invalid_price():
    with pytest.raises(ValueError):
        calculate_target(
            entry_price=0,
        )


def test_trade_plan_never_exceeds_allocation_limit():
    config = RiskConfig(
        stop_loss_pct=0.05,
        target_pct=0.15,
        risk_per_trade_pct=0.20,
        max_allocation_pct=0.20,
    )

    plan = calculate_trade_plan(
        entry_price=100,
        capital=100000,
        lot_size=65,
        config=config,
    )

    assert plan.capital_required <= plan.max_allocation


def test_trade_plan_never_exceeds_risk_budget():
    config = RiskConfig(
        stop_loss_pct=0.10,
        target_pct=0.20,
        risk_per_trade_pct=0.02,
        max_allocation_pct=0.50,
    )

    plan = calculate_trade_plan(
        entry_price=100,
        capital=100000,
        lot_size=65,
        config=config,
    )

    assert plan.planned_risk <= plan.risk_budget