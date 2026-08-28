from **future** import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Optional

class OptionSelectionError(Exception):
"""Raised when an option contract cannot be selected."""

@dataclass(frozen=True)
class OptionContract:
expiry: date
strike: float
option_type: str

def round_to_strike(
price: float,
strike_interval: int = 50,
) -> float:
if price <= 0:
raise ValueError("Price must be positive.")

```
if strike_interval <= 0:
    raise ValueError("Strike interval must be positive.")

return float(
    round(price / strike_interval)
    * strike_interval
)
```

def _normalise_option_type(
option_type: str,
) -> str:
value = str(option_type).upper().strip()

```
aliases = {
    "CALL": "CE",
    "PUT": "PE",
    "C": "CE",
    "P": "PE",
}

value = aliases.get(
    value,
    value,
)

if value not in {"CE", "PE"}:
    raise OptionSelectionError(
        f"Unsupported option type: {option_type}"
    )

return value
```

def _extract_expiry(
row: Mapping[str, Any],
) -> Optional[date]:
value = (
row.get("expiry")
or row.get("expiryDate")
or row.get("expiry_date")
)

```
if isinstance(value, date):
    return value

if not value:
    return None

text = str(value).strip()

formats = (
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
)

for fmt in formats:
    try:
        return date.fromisoformat(
            date.strptime(
                text,
                fmt,
            ).isoformat()
        )
    except (ValueError, AttributeError):
        continue

return None
```

def _extract_strike(
row: Mapping[str, Any],
) -> Optional[float]:
for name in (
"strike",
"strikePrice",
"strike_price",
):
value = row.get(name)

```
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

return None
```

def _extract_option_type(
row: Mapping[str, Any],
) -> Optional[str]:
for name in (
"option_type",
"optionType",
"type",
):
value = row.get(name)

```
    if value:
        try:
            return _normalise_option_type(
                str(value)
            )
        except OptionSelectionError:
            return None

return None
```

def _contract_from_row(
row: Mapping[str, Any],
) -> Optional[OptionContract]:
expiry = _extract_expiry(row)
strike = _extract_strike(row)
option_type = _extract_option_type(row)

```
if (
    expiry is None
    or strike is None
    or option_type is None
):
    return None

return OptionContract(
    expiry=expiry,
    strike=strike,
    option_type=option_type,
)
```

def _extract_contract_rows(
payload: Any,
) -> list[OptionContract]:
if isinstance(payload, list):
rows = payload

```
elif isinstance(payload, tuple):
    rows = list(payload)

elif isinstance(payload, Mapping):
    records = payload.get(
        "records",
        payload,
    )

    if isinstance(records, Mapping):
        rows = records.get(
            "data",
            [],
        )

    else:
        rows = []

else:
    rows = []

contracts: list[OptionContract] = []

for row in rows:
    if not isinstance(row, Mapping):
        continue

    contract = _contract_from_row(row)

    if contract is not None:
        contracts.append(contract)

return contracts
```

def select_contract(
contracts: list[OptionContract],
nifty_price: float,
option_type: str,
selection_mode: str = "ATM",
) -> OptionContract:
if not contracts:
raise OptionSelectionError(
"No option contracts supplied."
)

```
if nifty_price <= 0:
    raise OptionSelectionError(
        "NIFTY price must be positive."
    )

requested_type = _normalise_option_type(
    option_type
)

mode = str(
    selection_mode
).upper().strip()

if mode not in {
    "ATM",
    "ITM",
    "OTM",
}:
    raise OptionSelectionError(
        "selection_mode must be ATM, ITM, or OTM."
    )

candidates = [
    contract
    for contract in contracts
    if contract.option_type
    == requested_type
]

if not candidates:
    raise OptionSelectionError(
        f"No {requested_type} contracts available."
    )

if mode == "ATM":
    return min(
        candidates,
        key=lambda contract: (
            abs(
                contract.strike
                - nifty_price
            ),
            contract.strike,
        ),
    )

if requested_type == "CE":
    if mode == "ITM":
        itm = [
            contract
            for contract in candidates
            if contract.strike <= nifty_price
        ]

        if itm:
            return max(
                itm,
                key=lambda contract: contract.strike,
            )

    else:
        otm = [
            contract
            for contract in candidates
            if contract.strike >= nifty_price
        ]

        if otm:
            return min(
                otm,
                key=lambda contract: contract.strike,
            )

else:
    if mode == "ITM":
        itm = [
            contract
            for contract in candidates
            if contract.strike >= nifty_price
        ]

        if itm:
            return min(
                itm,
                key=lambda contract: contract.strike,
            )

    else:
        otm = [
            contract
            for contract in candidates
            if contract.strike <= nifty_price
        ]

        if otm:
            return max(
                otm,
                key=lambda contract: contract.strike,
            )

return min(
    candidates,
    key=lambda contract: abs(
        contract.strike
        - nifty_price
    ),
)
```

def select_live_contract(
option_chain_payload: Any,
nifty_price: float,
expiry: date,
option_type: str,
selection_mode: str = "ATM",
) -> OptionContract:
requested_type = _normalise_option_type(
option_type
)

```
contracts = _extract_contract_rows(
    option_chain_payload
)

candidates = [
    contract
    for contract in contracts
    if contract.expiry == expiry
    and contract.option_type
    == requested_type
]

if candidates:
    return select_contract(
        contracts=candidates,
        nifty_price=nifty_price,
        option_type=requested_type,
        selection_mode=selection_mode,
    )

if isinstance(
    option_chain_payload,
    Mapping,
):
    records = option_chain_payload.get(
        "records",
        {},
    )

    if isinstance(records, Mapping):
        data = records.get(
            "data",
            [],
        )

        fallback_contracts: list[
            OptionContract
        ] = []

        for row in data:
            if not isinstance(row, Mapping):
                continue

            row_expiry = _extract_expiry(row)
            row_strike = _extract_strike(row)

            if (
                row_expiry != expiry
                or row_strike is None
            ):
                continue

            fallback_contracts.append(
                OptionContract(
                    expiry=expiry,
                    strike=row_strike,
                    option_type=requested_type,
                )
            )

        if fallback_contracts:
            return select_contract(
                contracts=fallback_contracts,
                nifty_price=nifty_price,
                option_type=requested_type,
                selection_mode=selection_mode,
            )

raise OptionSelectionError(
    "No matching live option contract found "
    f"for expiry {expiry} and "
    f"option type {requested_type}."
)
```
