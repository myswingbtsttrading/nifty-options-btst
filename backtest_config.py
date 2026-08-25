from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestConfig:
    # BTST entry at 3:00 PM.
    entry_hour: int = 15
    entry_minute: int = 0

    # BTST exit at 9:15 AM on the next trading day.
    exit_hour: int = 9
    exit_minute: int = 15

    # NIFTY strike interval.
    strike_interval: int = 50

    # Conservative execution assumptions.
    entry_slippage_pct: float = 0.0025
    exit_slippage_pct: float = 0.0025

    # Round-trip trading cost assumption.
    brokerage_and_cost_pct: float = 0.0010

    # Starting capital.
    initial_capital: float = 100000.0

    # Minimum signal confidence.
    minimum_confidence: float = 65.0

    # NIFTY lot size used by the historical contract being tested.
    lot_size: int = 65

    # Step 4 risk management.
    stop_loss_pct: float = 0.15
    target_pct: float = 0.30

    risk_per_trade_pct: float = 0.01
    max_allocation_pct: float = 0.20

    def __post_init__(self) -> None:
        if self.entry_hour < 0 or self.entry_hour > 23:
            raise ValueError(
                "entry_hour must be between 0 and 23."
            )

        if self.entry_minute < 0 or self.entry_minute > 59:
            raise ValueError(
                "entry_minute must be between 0 and 59."
            )

        if self.exit_hour < 0 or self.exit_hour > 23:
            raise ValueError(
                "exit_hour must be between 0 and 23."
            )

        if self.exit_minute < 0 or self.exit_minute > 59:
            raise ValueError(
                "exit_minute must be between 0 and 59."
            )

        if self.strike_interval <= 0:
            raise ValueError(
                "strike_interval must be positive."
            )

        if self.entry_slippage_pct < 0:
            raise ValueError(
                "entry_slippage_pct cannot be negative."
            )

        if self.exit_slippage_pct < 0:
            raise ValueError(
                "exit_slippage_pct cannot be negative."
            )

        if self.brokerage_and_cost_pct < 0:
            raise ValueError(
                "brokerage_and_cost_pct cannot be negative."
            )

        if self.initial_capital <= 0:
            raise ValueError(
                "initial_capital must be positive."
            )

        if self.minimum_confidence < 0:
            raise ValueError(
                "minimum_confidence cannot be negative."
            )

        if self.lot_size <= 0:
            raise ValueError(
                "lot_size must be positive."
            )

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


DEFAULT_CONFIG = BacktestConfig()