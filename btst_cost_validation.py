from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


DEFAULT_COST_PER_SIDE = 0.001


@dataclass(frozen=True)
class CostValidation:
    total_trades: int
    winning_trades: int
    losing_trades: int
    gross_profit: float
    gross_loss: float
    net_profit: float
    profit_factor: float
    cost_per_side: float


def _number(
    value,
    default: float = 0.0,
) -> float:
    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


def _trade_return(trade) -> float | None:
    if not isinstance(trade, dict):
        return None

    for key in (
        "net_return",
        "return",
        "pnl_pct",
        "return_pct",
        "profit_pct",
    ):
        if key in trade:
            try:
                return float(trade[key])
            except (
                TypeError,
                ValueError,
            ):
                pass

    entry = None
    exit_price = None

    for key in (
        "entry_price",
        "entry",
        "entry_close",
    ):
        if key in trade:
            entry = _number(trade[key], 0.0)
            break

    for key in (
        "exit_price",
        "exit",
        "exit_close",
    ):
        if key in trade:
            exit_price = _number(
                trade[key],
                0.0,
            )
            break

    if entry and exit_price:
        return (
            (exit_price - entry)
            / entry
        )

    return None


def validate_trade_costs(
    trades,
    cost_per_side: float = DEFAULT_COST_PER_SIDE,
) -> CostValidation:
    gross_returns: list[float] = []

    for trade in trades:
        value = _trade_return(trade)

        if value is None:
            continue

        gross_returns.append(value)

    cost = (
        2.0 * cost_per_side
    )

    net_returns = [
        value - cost
        for value in gross_returns
    ]

    winning = [
        value
        for value in net_returns
        if value > 0
    ]

    losing = [
        value
        for value in net_returns
        if value < 0
    ]

    gross_profit = sum(
        value
        for value in gross_returns
        if value > 0
    )

    gross_loss = abs(
        sum(
            value
            for value in gross_returns
            if value < 0
        )
    )

    net_profit = sum(net_returns)

    if gross_loss > 0:
        profit_factor = (
            gross_profit / gross_loss
        )
    else:
        profit_factor = float("inf")

    return CostValidation(
        total_trades=len(net_returns),
        winning_trades=len(winning),
        losing_trades=len(losing),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        net_profit=net_profit,
        profit_factor=profit_factor,
        cost_per_side=cost_per_side,
    )


def write_validation_report(
    result: CostValidation,
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "total_trades": result.total_trades,
        "winning_trades": result.winning_trades,
        "losing_trades": result.losing_trades,
        "gross_profit": result.gross_profit,
        "gross_loss": result.gross_loss,
        "net_profit": result.net_profit,
        "profit_factor": result.profit_factor,
        "cost_per_side": result.cost_per_side,
    }

    output_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    return output_path