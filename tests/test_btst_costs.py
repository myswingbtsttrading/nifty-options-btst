from math import isclose


def test_round_trip_cost_is_applied_to_gross_return():
    entry = 100.0
    exit_price = 110.0
    cost_per_side = 0.001

    gross = (exit_price - entry) / entry
    net = gross - (2 * cost_per_side)

    assert isclose(gross, 0.10)
    assert isclose(net, 0.098)
    assert net < gross


def test_losing_trade_remains_a_loss_after_costs():
    entry = 100.0
    exit_price = 95.0
    cost_per_side = 0.001

    gross = (exit_price - entry) / entry
    net = gross - (2 * cost_per_side)

    assert gross < 0
    assert net < gross


def test_costs_are_not_applied_as_a_percentage_of_profit():
    entry = 100.0
    exit_price = 110.0
    cost_per_side = 0.001

    gross = (exit_price - entry) / entry
    correct_net = gross - (2 * cost_per_side)

    incorrect_net = gross * (
        1 - (2 * cost_per_side)
    )

    assert isclose(correct_net, 0.098)
    assert not isclose(
        correct_net,
        incorrect_net,
    )