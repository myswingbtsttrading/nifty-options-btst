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