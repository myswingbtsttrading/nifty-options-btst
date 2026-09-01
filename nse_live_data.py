def nearest_nifty_expiry(
    chain: (
        NiftyOptionChain
        | dict[str, Any]
    ),
    today: date | None = None,
) -> date:
    if isinstance(
        chain,
        NiftyOptionChain,
    ):
        expiry_dates = tuple(
            chain.expiry_dates
        )

        current_date = (
            today
            if today is not None
            else chain.timestamp.date()
        )
    else:
        expiry_dates = tuple(
            available_nifty_expiries(
                chain
            )
        )

        current_date = (
            today
            if today is not None
            else date.today()
        )

    future_expiries = [
        expiry
        for expiry in expiry_dates
        if expiry >= current_date
    ]

    if not future_expiries:
        raise LiveMarketDataError(
            "NSE option chain contains no future NIFTY expiry."
        )

    return min(future_expiries)