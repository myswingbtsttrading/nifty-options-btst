from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable, Mapping, Optional


class OptionSelectionError(Exception):
    """Raised when a suitable option contract cannot be selected."""


@dataclass(frozen=True)
class OptionContract:
    expiry: date
    strike: float
    option_type: str
    premium: float
    lot_size: int = 65

    @property
    def symbol(self) -> str:
        return (
            f"NIFTY {self.expiry.isoformat()} "
            f"{self.strike:g}{self.option_type.upper()}"
        )


def round_to_strike(
    spot: float,
    strike_step: int = 50,
) -> float:
    if strike_step <= 0:
        raise ValueError(
            "strike_step must be greater than zero."
        )

    if spot <= 0:
        raise ValueError(
            "spot must be greater than zero."
        )

    return float(
        int(
            (spot / strike_step) + 0.5
        )
        * strike_step
    )


def select_atm_strike(
    spot: float,
    strike_step: int = 50,
) -> float:
    """
    Backward-compatible helper returning the ATM strike.
    """
    return round_to_strike(
        spot=spot,
        strike_step=strike_step,
    )


def _normalise_option_type(
    option_type: str,
) -> str:
    value = str(
        option_type
    ).strip().upper()

    if value not in {"CE", "PE"}:
        raise OptionSelectionError(
            "option_type must be CE or PE."
        )

    return value


def _get_value(
    row: Any,
    *names: str,
) -> Any:
    if isinstance(row, Mapping):
        for name in names:
            if name in row:
                return row[name]
        return None

    for name in names:
        if hasattr(row, name):
            return getattr(row, name)

    return None


def _to_float(
    value: Any,
) -> Optional[float]:
    if value is None:
        return None

    try:
        result = float(
            str(value).replace(",", "")
        )
    except (TypeError, ValueError):
        return None

    if result <= 0:
        return None

    return result


def _to_date(
    value: Any,
) -> Optional[date]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()

    for fmt in (
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ):
        try:
            return datetime.strptime(
                text,
                fmt,
            ).date()
        except ValueError:
            continue

    return None


def _extract_expiry(
    row: Any,
) -> Optional[date]:
    return _to_date(
        _get_value(
            row,
            "expiry",
            "Expiry",
            "expiry_date",
            "ExpiryDate",
        )
    )


def _extract_strike(
    row: Any,
) -> Optional[float]:
    return _to_float(
        _get_value(
            row,
            "strike",
            "Strike",
            "strikePrice",
            "strike_price",
        )
    )


def _extract_premium(
    row: Any,
) -> Optional[float]:
    return _to_float(
        _get_value(
            row,
            "premium",
            "Premium",
            "lastPrice",
            "last_price",
            "LTP",
            "ltp",
            "close",
            "Close",
            "option_price",
        )
    )


def _extract_option_type(
    row: Any,
) -> Optional[str]:
    value = _get_value(
        row,
        "option_type",
        "OptionType",
        "optionType",
        "type",
        "Type",
        "instrumentType",
    )

    if value is None:
        return None

    value = str(value).strip().upper()

    if value in {"CE", "PE"}:
        return value

    return None


def _extract_lot_size(
    row: Any,
    default: int = 65,
) -> int:
    value = _get_value(
        row,
        "lot_size",
        "lotSize",
        "LotSize",
        "qty",
        "quantity",
    )

    try:
        lot_size = int(float(value))
    except (TypeError, ValueError):
        lot_size = default

    return lot_size if lot_size > 0 else default


def _iter_rows(
    option_chain: Any,
) -> Iterable[Any]:
    if option_chain is None:
        return []

    if isinstance(option_chain, Mapping):
        for key in (
            "records",
            "data",
            "options",
            "chain",
        ):
            value = option_chain.get(key)

            if (
                isinstance(value, Iterable)
                and not isinstance(
                    value,
                    (
                        str,
                        bytes,
                        Mapping,
                    ),
                )
            ):
                return value

        return []

    if hasattr(option_chain, "data"):
        value = option_chain.data

        if (
            isinstance(value, Iterable)
            and not isinstance(
                value,
                (
                    str,
                    bytes,
                    Mapping,
                ),
            )
        ):
            return value

    if (
        isinstance(option_chain, Iterable)
        and not isinstance(
            option_chain,
            (
                str,
                bytes,
                Mapping,
            ),
        )
    ):
        return option_chain

    return []


def _build_candidates(
    option_chain: Any,
    option_type: str,
    expiry: Optional[date],
):
    candidates = []

    for row in _iter_rows(option_chain):
        row_type = _extract_option_type(row)

        if row_type != option_type:
            continue

        row_expiry = _extract_expiry(row)

        if (
            expiry is not None
            and row_expiry != expiry
        ):
            continue

        strike = _extract_strike(row)
        premium = _extract_premium(row)

        if (
            strike is None
            or premium is None
        ):
            continue

        candidates.append(
            (
                row,
                strike,
                premium,
                row_expiry,
            )
        )

    return candidates


def select_contract(
    option_chain: Any,
    spot: float,
    option_type: str,
    expiry: Optional[date] = None,
    strike_step: int = 50,
    selection_mode: str = "ATM",
    lot_size: int = 65,
) -> OptionContract:
    if spot <= 0:
        raise OptionSelectionError(
            "spot must be greater than zero."
        )

    option_type = _normalise_option_type(
        option_type
    )

    mode = str(
        selection_mode
    ).strip().upper()

    if mode not in {
        "ATM",
        "ITM",
        "OTM",
    }:
        raise OptionSelectionError(
            "selection_mode must be ATM, ITM, or OTM."
        )

    candidates = _build_candidates(
        option_chain=option_chain,
        option_type=option_type,
        expiry=expiry,
    )

    if not candidates:
        raise OptionSelectionError(
            "No valid option contract found "
            f"for {option_type}."
        )

    def distance(item):
        return abs(
            item[1] - spot
        )

    if mode == "ATM":
        selected = min(
            candidates,
            key=distance,
        )

    elif mode == "ITM":
        if option_type == "CE":
            preferred = [
                item
                for item in candidates
                if item[1] <= spot
            ]
        else:
            preferred = [
                item
                for item in candidates
                if item[1] >= spot
            ]

        selected = min(
            preferred or candidates,
            key=distance,
        )

    else:
        if option_type == "CE":
            preferred = [
                item
                for item in candidates
                if item[1] >= spot
            ]
        else:
            preferred = [
                item
                for item in candidates
                if item[1] <= spot
            ]

        selected = min(
            preferred or candidates,
            key=distance,
        )

    row, strike, premium, selected_expiry = selected

    if selected_expiry is None:
        if expiry is None:
            raise OptionSelectionError(
                "Selected contract has no expiry."
            )

        selected_expiry = expiry

    return OptionContract(
        expiry=selected_expiry,
        strike=float(strike),
        option_type=option_type,
        premium=float(premium),
        lot_size=_extract_lot_size(
            row,
            default=lot_size,
        ),
    )


def select_atm_contract(
    option_chain: Any,
    spot: float,
    option_type: str,
    expiry: Optional[date] = None,
    strike_step: int = 50,
    lot_size: int = 65,
) -> OptionContract:
    """
    Backward-compatible ATM contract selector.
    """
    return select_contract(
        option_chain=option_chain,
        spot=spot,
        option_type=option_type,
        expiry=expiry,
        strike_step=strike_step,
        selection_mode="ATM",
        lot_size=lot_size,
    )


def select_live_contract(
    option_chain: Any,
    spot: float,
    option_type: str,
    expiry: Optional[date] = None,
    strike_step: int = 50,
    selection_mode: str = "ATM",
    lot_size: int = 65,
) -> OptionContract:
    """
    Compatibility wrapper used by live_signal_engine.py.
    """
    return select_contract(
        option_chain=option_chain,
        spot=spot,
        option_type=option_type,
        expiry=expiry,
        strike_step=strike_step,
        selection_mode=selection_mode,
        lot_size=lot_size,
    )