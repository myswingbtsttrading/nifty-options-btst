from dataclasses import dataclass
from math import floor


@dataclass(frozen=True)
class RiskConfig:
    """
    Risk parameters for a long NIFTY option BTST trade.

    Percentages are expressed as decimal fractions.

    Example:
        stop_loss_pct=0.15  -> 15%
        target_pct=0.30     -> 30%
        risk_per_trade_pct=0.01 -> 1% of capital
        max_allocation_pct=0.20 -> maximum 20% of capital
    """

    stop_loss_pct: float = 0.15
    target_pct: float = 0.30

    risk_per_trade_pct: float = 0.01
    max_allocation_pct: float = 0.20

    def __post_init__(self) -> None:
        if not 0 < self.stop_loss_pct < 1:
            raise ValueError(
                "stop_loss_pct must be between 0 and 1."
            )

        if self.target_pct <= 0:
            raise ValueError(
                "target_pct must be positive."
            )

        if not 0 < self.risk_per_trade_pct <= 1:
            raise ValueError(
                "risk_per_trade_pct must be greater than 0 "
                "and no greater than 1."
            )

        if not 0 < self.max_allocation_pct <= 1:
            raise ValueError(
                "max_allocation_pct must be greater than 0 "
                "and no greater than 1."
            )


@dataclass(frozen=True)
class TradePlan:
    """
    Complete planning information for one long option BTST trade.
    """

    entry_price: float
    stop_loss: float
    target: float

    risk_per_unit: float
    reward_per_unit: float
    risk_reward_ratio: float

    capital: float
    risk_budget: float
    max_allocation: float

    lot_size: int
    lots: int
    quantity: int

    capital_required: float
    planned_risk: float
    planned_reward: float

    risk_pct_of_capital: float
    allocation_pct_of_capital: float

    @property
    def is_tradeable(self) -> bool:
        return self.quantity > 0 and self.lots > 0


def calculate_stop_loss(
    entry_price: float,
    stop_loss_pct: float = 0.15,
) -> float:
    """
    Calculate the option stop-loss price.

    This is a premium-based stop for a long option.
    """

    if entry_price <= 0:
        raise ValueError(
            "entry_price must be positive."
        )

    if not 0 < stop_loss_pct < 1:
        raise ValueError(
            "stop_loss_pct must be between 0 and 1."
        )

    stop_loss = entry_price * (
        1 - stop_loss_pct
    )

    if stop_loss <= 0:
        raise ValueError(
            "Calculated stop-loss must be positive."
        )

    return round(stop_loss, 2)


def calculate_target(
    entry_price: float,
    target_pct: float = 0.30,
) -> float:
    """
    Calculate the option target price.
    """

    if entry_price <= 0:
        raise ValueError(
            "entry_price must be positive."
        )

    if target_pct <= 0:
        raise ValueError(
            "target_pct must be positive."
        )

    return round(
        entry_price * (1 + target_pct),
        2,
    )


def calculate_trade_plan(
    entry_price: float,
    capital: float,
    lot_size: int,
    config: RiskConfig = RiskConfig(),
) -> TradePlan:
    """
    Build a complete BTST trade plan.

    Position sizing uses BOTH:

    1. Risk budget:
           capital × risk_per_trade_pct

    2. Maximum capital allocation:
           capital × max_allocation_pct

    The number of lots is the smaller of the two limits.

    This prevents a low-premium option from consuming excessive
    risk while also preventing the trade from using too much
    available capital.
    """

    if entry_price <= 0:
        raise ValueError(
            "entry_price must be positive."
        )

    if capital <= 0:
        raise ValueError(
            "capital must be positive."
        )

    if not isinstance(lot_size, int):
        raise ValueError(
            "lot_size must be an integer."
        )

    if lot_size <= 0:
        raise ValueError(
            "lot_size must be positive."
        )

    stop_loss = calculate_stop_loss(
        entry_price=entry_price,
        stop_loss_pct=config.stop_loss_pct,
    )

    target = calculate_target(
        entry_price=entry_price,
        target_pct=config.target_pct,
    )

    risk_per_unit = round(
        entry_price - stop_loss,
        2,
    )

    reward_per_unit = round(
        target - entry_price,
        2,
    )

    if risk_per_unit <= 0:
        raise ValueError(
            "Risk per unit must be positive."
        )

    if reward_per_unit <= 0:
        raise ValueError(
            "Reward per unit must be positive."
        )

    risk_reward_ratio = (
        reward_per_unit / risk_per_unit
    )

    risk_budget = (
        capital
        * config.risk_per_trade_pct
    )

    max_allocation = (
        capital
        * config.max_allocation_pct
    )

    risk_per_lot = (
        risk_per_unit * lot_size
    )

    capital_per_lot = (
        entry_price * lot_size
    )

    lots_by_risk = floor(
        risk_budget / risk_per_lot
    )

    lots_by_capital = floor(
        max_allocation / capital_per_lot
    )

    lots = min(
        lots_by_risk,
        lots_by_capital,
    )

    quantity = lots * lot_size

    capital_required = round(
        quantity * entry_price,
        2,
    )

    planned_risk = round(
        quantity * risk_per_unit,
        2,
    )

    planned_reward = round(
        quantity * reward_per_unit,
        2,
    )

    risk_pct_of_capital = (
        planned_risk / capital * 100
    )

    allocation_pct_of_capital = (
        capital_required / capital * 100
    )

    return TradePlan(
        entry_price=round(entry_price, 2),
        stop_loss=stop_loss,
        target=target,
        risk_per_unit=risk_per_unit,
        reward_per_unit=reward_per_unit,
        risk_reward_ratio=round(
            risk_reward_ratio,
            2,
        ),
        capital=round(capital, 2),
        risk_budget=round(risk_budget, 2),
        max_allocation=round(
            max_allocation,
            2,
        ),
        lot_size=lot_size,
        lots=lots,
        quantity=quantity,
        capital_required=capital_required,
        planned_risk=planned_risk,
        planned_reward=planned_reward,
        risk_pct_of_capital=round(
            risk_pct_of_capital,
            4,
        ),
        allocation_pct_of_capital=round(
            allocation_pct_of_capital,
            4,
        ),
    )