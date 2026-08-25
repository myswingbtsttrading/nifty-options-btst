from math import isclose

from btst_cost_validation import (
    validate_trade_costs,
)


def test_validate_trade_costs():
    trades = [
        {
            "entry_price": 100,
            "exit_price": 110,
        },
        {
            "entry_price": 100,
            "exit_price": 90,
        },
    ]

    result = validate_trade_costs(
        trades,
        cost_per_side=0.001,
    )

    assert result.total_trades == 2
    assert result.winning_trades == 1
    assert result.losing_trades == 1

    assert isclose(
        result.net_profit,
        -0.004,
    )


def test_cost_validation_handles_empty_input():
    result = validate_trade_costs([])

    assert result.total_trades == 0
    assert result.winning_trades == 0
    assert result.losing_trades == 0
    assert result.net_profit == 0.0