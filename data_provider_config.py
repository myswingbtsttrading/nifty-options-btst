from dataclasses import dataclass


@dataclass(frozen=True)
class DataProviderConfig:
    timezone: str = "Asia/Kolkata"

    entry_hour: int = 15
    entry_minute: int = 0

    exit_hour: int = 9
    exit_minute: int = 30

    underlying: str = "NIFTY"

    option_types: tuple[str, ...] = (
        "CE",
        "PE",
    )


DEFAULT_PROVIDER_CONFIG = DataProviderConfig()