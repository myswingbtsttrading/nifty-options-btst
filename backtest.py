from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from math import floor
from typing import Any, Dict, List, Optional, Tuple

from backtest_config import (
    BacktestConfig,
    DEFAULT_CONFIG,
)
from historical_dataset import next_trading_date
from option_selector import round_to_strike
from option_strategy import generate_signal

@dataclass
class BacktestTrade:
    entry_time: datetime
    exit_time: datetime

    direction: str
    strike: float
    expiry: str

    entry_price: float
    exit_price: float

    gross_pnl: float
    costs: float
    net_pnl: float

    return_pct: float
    confidence: float

    reason: str


@dataclass
class BacktestResult:
    initial_capital: float
    final_capital: float

    total_trades: int
    winning_trades: int
    losing_trades: int

    win_rate: float
    total_return_pct: float

    gross_profit: float
    gross_loss: float
    profit_factor: float

    max_drawdown_pct: float

    trades: List[BacktestTrade]


def _ema(
    values: List[float],
    period: int,
) -> Optional[float]:
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    value = sum(
        values[:period]
    ) / period

    for price in values[period:]:
        value = (
            price - value
        ) * multiplier + value

    return value


def _rsi(
    values: List[float],
    period: int = 14,
) -> Optional[float]:
    if len(values) <= period:
        return None

    gains = []
    losses = []

    for index in range(1, period + 1):
        change = (
            values[index]
            - values[index - 1]
        )

        if change >= 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))

    average_gain = (
        sum(gains) / period
    )
    average_loss = (
        sum(losses) / period
    )

    for index in range(
        period + 1,
        len(values),
    ):
        change = (
            values[index]
            - values[index - 1]
        )

        gain = max(change, 0.0)
        loss = max(-change, 0.0)

        average_gain = (
            (
                average_gain
                * (period - 1)
            )
            + gain
        ) / period

        average_loss = (
            (
                average_loss
                * (period - 1)
            )
            + loss
        ) / period

    if average_loss == 0:
        return 100.0

    relative_strength = (
        average_gain / average_loss
    )

    return 100 - (
        100 / (1 + relative_strength)
    )


def _time_matches(
    timestamp: datetime,
    hour: int,
    minute: int,
) -> bool:
    return (
        timestamp.hour == hour
        and timestamp.minute == minute
    )


def _find_option_quote(
    option_rows: List[Dict[str, Any]],
    timestamp: datetime,
    strike: float,
    option_type: str,
    expiry: str,
) -> Optional[Dict[str, Any]]:
    candidates = [
        row
        for row in option_rows
        if (
            row["timestamp"] == timestamp
            and row["strike"] == strike
            and row["option_type"] == option_type
            and row["expiry"] == expiry
        )
    ]

    if not candidates:
        return None

    return candidates[0]


def _find_nearest_expiry(
    option_rows: List[Dict[str, Any]],
    timestamp: datetime,
    strike: float,
    option_type: str,
) -> Optional[str]:
    expiries = sorted(
        {
            row["expiry"]
            for row in option_rows
            if (
                row["timestamp"] == timestamp
                and row["strike"] == strike
                and row["option_type"] == option_type
            )
        }
    )

    if not expiries:
        return None

    return expiries[0]



def _apply_entry_slippage(
    price: float,
    config: BacktestConfig,
) -> float:
    return price * (
        1 + config.entry_slippage_pct
    )


def _apply_exit_slippage(
    price: float,
    config: BacktestConfig,
) -> float:
    return price * (
        1 - config.exit_slippage_pct
    )


def _calculate_trade(
    entry_quote: Dict[str, Any],
    exit_quote: Dict[str, Any],
    direction: str,
    confidence: float,
    reason: str,
    config: BacktestConfig,
) -> BacktestTrade:
    raw_entry = float(
        entry_quote["close"]
    )

    raw_exit = float(
        exit_quote["close"]
    )

    entry_price = _apply_entry_slippage(
        raw_entry,
        config,
    )

    exit_price = _apply_exit_slippage(
        raw_exit,
        config,
    )

    gross_pnl = (
        exit_price - entry_price
    )

    costs = (
        entry_price + exit_price
    ) * config.brokerage_and_cost_pct

    net_pnl = (
        gross_pnl - costs
    )

    return_pct = (
        net_pnl / entry_price
    ) * 100

    return BacktestTrade(
        entry_time=entry_quote["timestamp"],
        exit_time=exit_quote["timestamp"],
        direction=direction,
        strike=entry_quote["strike"],
        expiry=entry_quote["expiry"],
        entry_price=entry_price,
        exit_price=exit_price,
        gross_pnl=gross_pnl,
        costs=costs,
        net_pnl=net_pnl,
        return_pct=return_pct,
        confidence=confidence,
        reason=reason,
    )


def _find_next_morning(
    option_rows: List[Dict[str, Any]],
    entry_time: datetime,
    strike: float,
    option_type: str,
    expiry: str,
    config: BacktestConfig,
) -> Optional[Dict[str, Any]]:
    available_dates = sorted(
        {
            row["timestamp"].date()
            for row in option_rows
            if (
                row.get("timestamp") is not None
                and row["timestamp"].date()
                > entry_time.date()
            )
        }
    )

    if not available_dates:
        return None

    target_date = available_dates[0]

    target_timestamp = datetime.combine(
        target_date,
        datetime.min.time(),
    ).replace(
        hour=config.exit_hour,
        minute=config.exit_minute,
    )

    candidates = [
        row
        for row in option_rows
        if (
            row["timestamp"].date() == target_date
            and row["timestamp"] >= target_timestamp
            and row["strike"] == strike
            and row["option_type"] == option_type
            and row["expiry"] == expiry
        )
    ]

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda row: row["timestamp"],
    )


def _calculate_max_drawdown(
    equity_curve: List[float],
) -> float:
    if not equity_curve:
        return 0.0

    peak = equity_curve[0]
    max_drawdown = 0.0

    for value in equity_curve:
        peak = max(peak, value)

        if peak > 0:
            drawdown = (
                (peak - value)
                / peak
            ) * 100

            max_drawdown = max(
                max_drawdown,
                drawdown,
            )

    return max_drawdown


def run_backtest(
    underlying_rows: List[Dict[str, Any]],
    option_rows: List[Dict[str, Any]],
    config: BacktestConfig = DEFAULT_CONFIG,
) -> BacktestResult:
    if not underlying_rows:
        raise ValueError(
            "Underlying data is empty."
        )

    if not option_rows:
        raise ValueError(
            "Options data is empty."
        )

    trades: List[BacktestTrade] = []

    prices: List[float] = []

    for index, row in enumerate(
        underlying_rows
    ):
        prices.append(
            float(row["close"])
        )

        timestamp = row["timestamp"]

        if not _time_matches(
            timestamp,
            config.entry_hour,
            config.entry_minute,
        ):
            continue

        ema20 = _ema(
            prices,
            20,
        )

        ema50 = _ema(
            prices,
            50,
        )

        rsi = _rsi(
            prices,
            14,
        )

        if (
            ema20 is None
            or ema50 is None
            or rsi is None
            or index == 0
        ):
            continue

        previous_close = float(
            underlying_rows[index - 1][
                "close"
            ]
        )

        signal = generate_signal(
            nifty_price=float(
                row["close"]
            ),
            ema20=ema20,
            ema50=ema50,
            rsi=rsi,
            previous_close=previous_close,
        )

        if signal.decision != "BUY":
            continue

        if (
            signal.confidence
            < config.minimum_confidence
        ):
            continue

        strike = round_to_strike(
            float(row["close"])
        )

        expiry = _find_nearest_expiry(
            option_rows,
            timestamp,
            strike,
            signal.direction,
        )

        if expiry is None:
            continue

        entry_quote = _find_option_quote(
            option_rows,
            timestamp,
            strike,
            signal.direction,
            expiry,
        )

        if entry_quote is None:
            continue

        exit_quote = _find_next_morning(
            option_rows,
            timestamp,
            strike,
            signal.direction,
            expiry,
            config,
        )

        if exit_quote is None:
            continue

        trade = _calculate_trade(
            entry_quote,
            exit_quote,
            signal.direction,
            signal.confidence,
            signal.reason,
            config,
        )

        trades.append(trade)

    initial_capital = (
        config.initial_capital
    )

    final_capital = initial_capital

    equity_curve = [
        initial_capital
    ]

    gross_profit = 0.0
    gross_loss = 0.0
    winning_trades = 0
    losing_trades = 0

    for trade in trades:
        final_capital += trade.net_pnl

        equity_curve.append(
            final_capital
        )

        if trade.net_pnl > 0:
            winning_trades += 1
            gross_profit += trade.net_pnl

        elif trade.net_pnl < 0:
            losing_trades += 1
            gross_loss += abs(
                trade.net_pnl
            )

    total_trades = len(trades)

    win_rate = (
        winning_trades
        / total_trades
        * 100
        if total_trades
        else 0.0
    )

    total_return_pct = (
        (
            final_capital
            - initial_capital
        )
        / initial_capital
        * 100
    )

    if gross_loss > 0:
        profit_factor = (
            gross_profit / gross_loss
        )
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    return BacktestResult(
        initial_capital=initial_capital,
        final_capital=final_capital,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=win_rate,
        total_return_pct=total_return_pct,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=profit_factor,
        max_drawdown_pct=_calculate_max_drawdown(
            equity_curve
        ),
        trades=trades,
    )


def format_backtest_report(
    result: BacktestResult,
) -> str:
    profit_factor = (
        "∞"
        if result.profit_factor == float("inf")
        else f"{result.profit_factor:.2f}"
    )

    return (
        "NIFTY OPTIONS BTST BACKTEST\n"
        "\n"
        f"Initial capital: "
        f"₹{result.initial_capital:,.2f}\n"
        f"Final capital: "
        f"₹{result.final_capital:,.2f}\n"
        f"Trades: {result.total_trades}\n"
        f"Wins: {result.winning_trades}\n"
        f"Losses: {result.losing_trades}\n"
        f"Win rate: {result.win_rate:.2f}%\n"
        f"Return: {result.total_return_pct:.2f}%\n"
        f"Profit factor: {profit_factor}\n"
        f"Max drawdown: "
        f"{result.max_drawdown_pct:.2f}%"
    )