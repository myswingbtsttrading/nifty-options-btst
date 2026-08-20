from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestConfig:
    entry_hour: int = 15
    entry_minute: int = 0

    # BTST exit: next trading day's first available
    # observation at or after 09:15.
    exit_hour: int = 9
    exit_minute: int = 15

    strike_interval: int = 50

    # Conservative execution assumptions.
    entry_slippage_pct: float = 0.0025
    exit_slippage_pct: float = 0.0025

    brokerage_and_cost_pct: float = 0.0010

    initial_capital: float = 100000.0

    # Only trade sufficiently strong signals.
    minimum_confidence: float = 65.0


DEFAULT_CONFIG = BacktestConfig()