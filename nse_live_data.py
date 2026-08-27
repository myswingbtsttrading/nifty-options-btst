def _normalise_chain_records(
    payload: dict[str, Any],
) -> tuple[
    float,
    tuple[date, ...],
    tuple[dict[str, Any], ...],
]:
    if not isinstance(payload, dict):
        raise LiveMarketDataError(
            "NSE option-chain payload is invalid."
        )

    records = payload.get("records")

    if not isinstance(records, dict):
        records = {}

    filtered = payload.get("filtered")

    if not isinstance(filtered, dict):
        filtered = {}

    # NSE option-chain-v3 can expose the contract rows through
    # records.data or filtered.data. Prefer records.data because
    # it contains the full chain when available.
    raw_data = records.get("data")

    if not isinstance(raw_data, list):
        raw_data = filtered.get("data")

    if not isinstance(raw_data, list):
        raw_data = payload.get("data")

    if not isinstance(raw_data, list):
        raw_data = []

    underlying = _first_float(
        records.get("underlyingValue"),
        payload.get("underlyingValue"),
    )

    if underlying is None:
        for item in raw_data:
            if not isinstance(item, dict):
                continue

            ce = item.get("CE")
            pe = item.get("PE")

            if isinstance(ce, dict):
                underlying = _first_float(
                    ce.get("underlyingValue")
                )

            if underlying is None and isinstance(pe, dict):
                underlying = _first_float(
                    pe.get("underlyingValue")
                )

            if underlying is not None:
                break

    if underlying is None:
        underlying = 0.0

    raw_expiries = records.get(
        "expiryDates",
        payload.get("expiryDates", []),
    )

    expiries: list[date] = []

    if isinstance(raw_expiries, list):
        for value in raw_expiries:
            parsed = _parse_expiry(value)

            if parsed is not None:
                expiries.append(parsed)

    normalized_records: list[
        dict[str, Any]
    ] = []

    for item in raw_data:
        if not isinstance(item, dict):
            continue

        strike = _first_float(
            item.get("strikePrice"),
            item.get("strike"),
        )

        if strike is None:
            continue

        ce = item.get("CE")
        pe = item.get("PE")

        if not isinstance(ce, dict):
            ce = None

        if not isinstance(pe, dict):
            pe = None

        expiry = _parse_expiry(
            item.get("expiryDate")
            or item.get("expiry")
        )

        # v3 commonly provides expiryDate inside CE/PE.
        if expiry is None and ce is not None:
            expiry = _parse_expiry(
                ce.get("expiryDate")
                or ce.get("expiry")
            )

        if expiry is None and pe is not None:
            expiry = _parse_expiry(
                pe.get("expiryDate")
                or pe.get("expiry")
            )

        # Some v3 responses expose expiryDates as the row-level
        # field rather than expiryDate.
        if expiry is None:
            row_expiry = item.get("expiryDates")

            if isinstance(row_expiry, list):
                for value in row_expiry:
                    parsed = _parse_expiry(value)

                    if parsed is not None:
                        expiry = parsed
                        break
            else:
                expiry = _parse_expiry(row_expiry)

        if expiry is None:
            continue

        normalized_records.append(
            {
                "strike": strike,
                "expiry": expiry,
                "CE": ce,
                "PE": pe,
            }
        )

        if expiry not in expiries:
            expiries.append(expiry)

    # If NSE supplied an expiry list but the individual rows did
    # not expose it, retain the supplied expiry list.
    expiries = sorted(
        set(expiries)
    )

    return (
        underlying,
        tuple(expiries),
        tuple(normalized_records),
    )