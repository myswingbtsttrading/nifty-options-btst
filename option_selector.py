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
    premium: float = 0.0
    lot_size: int = 65
    selection_mode: str = "ATM"

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
        raise OptionSelectionError(
            "strike_step must be greater than zero."
        )

    try:
        value = float(spot)
    except (TypeError, ValueError):
        raise OptionSelectionError(
            "spot must be a positive number."
        ) from None

    if value <= 0:
        raise OptionSelectionError(
            "spot must be positive."
        )

    return float(
        int((value / strike_step) + 0.5) * strike_step
    )


def select_atm_strike(
    spot: float,
    strike_step: int = 50,
) -> float:
    """Return the nearest ATM NIFTY strike."""
    return round_to_strike(
        spot=spot,
        strike_step=strike_step,
    )


def _normalise_option_type(option_type: str) -> str:
    value = str(option_type).strip().upper()

    if value not in {"CE", "PE"}:
        raise OptionSelectionError(
            "option_type must be CE or PE."
        )

    return value


def _normalise_selection_mode(selection_mode: str) -> str:
    value = str(selection_mode).strip().upper()

    if value not in {"ATM", "ITM", "OTM"}:
        raise OptionSelectionError(
            "selection_mode must be ATM, ITM, or OTM."
        )

    return value


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None

    try:
        result = float(
            str(value).replace(",", "").strip()
        )
    except (TypeError, ValueError):
        return None

    return result


def _positive_float(value: Any) -> Optional[float]:
    result = _to_float(value)

    if result is None or result <= 0:
        return None

    return result


def _to_date(value: Any) -> Optional[date]:
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
        "%d/%b/%Y",
        "%d/%B/%Y",
    ):
        try:
            return datetime.strptime(
                text,
                fmt,
            ).date()
        except ValueError:
            continue

    return None


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


def _extract_expiry(row: Any) -> Optional[date]:
    return _to_date(
        _get_value(
            row,
            "expiry",
            "Expiry",
            "expiry_date",
            "expiryDate",
            "ExpiryDate",
        )
    )


def _extract_strike(row: Any) -> Optional[float]:
    return _positive_float(
        _get_value(
            row,
            "strike",
            "Strike",
            "strikePrice",
            "strike_price",
        )
    )


def _extract_premium(row: Any) -> Optional[float]:
    return _positive_float(
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
            "optionPrice",
        )
    )


def _extract_option_type(row: Any) -> Optional[str]:
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
        result = int(float(value))
    except (TypeError, ValueError):
        result = default

    return result if result > 0 else default


def _iter_rows(
    option_chain: Any,
) -> Iterable[Any]:
    if option_chain is None:
        return []

    if isinstance(option_chain, Mapping):
        records = option_chain.get("records")

        if isinstance(records, Mapping):
            data = records.get("data")

            if isinstance(data, Iterable) and not isinstance(
                data,
                (str, bytes, Mapping),
            ):
                return data

        for key in (
            "data",
            "options",
            "chain",
        ):
            value = option_chain.get(key)

            if isinstance(value, Iterable) and not isinstance(
                value,
                (str, bytes, Mapping),
            ):
                return value

        return []

    # Normalized live-chain object returned by nse_live_data.py.
    # NiftyOptionChain stores already-normalized option rows in `records`.
    if hasattr(option_chain, "records"):
        value = option_chain.records

        if isinstance(value, Iterable) and not isinstance(
            value,
            (str, bytes, Mapping),
        ):
            return value

    if hasattr(option_chain, "data"):
        value = option_chain.data

        if isinstance(value, Iterable) and not isinstance(
            value,
            (str, bytes, Mapping),
        ):
            return value

    if isinstance(option_chain, Iterable) and not isinstance(
        option_chain,
        (str, bytes, Mapping),
    ):
        return option_chain

    return []


def _option_side(
    row: Any,
    option_type: str,
) -> Any:
    if not isinstance(row, Mapping):
        return None

    return row.get(option_type)


def _expand_row(
    row: Any,
    option_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Convert both normalized rows and NSE-style rows into a common
    internal representation.

    Supported NSE format:

        {
            "strikePrice": 25000,
            "expiryDate": "27-Aug-2026",
            "CE": {"lastPrice": 105},
            "PE": {"lastPrice": 95},
        }

    Supported normalized format:

        {
            "strike": 25000,
            "expiry": date(...),
            "option_type": "CE",
            "premium": 105,
        }
    """
    if not isinstance(row, Mapping):
        return [dict(
            strike=_extract_strike(row),
            expiry=_extract_expiry(row),
            option_type=_extract_option_type(row),
            premium=_extract_premium(row),
            lot_size=_extract_lot_size(row),
        )]

    strike = _extract_strike(row)
    expiry = _extract_expiry(row)
    explicit_type = _extract_option_type(row)

    result: list[dict[str, Any]] = []

    requested_types = (
        [option_type]
        if option_type in {"CE", "PE"}
        else ["CE", "PE"]
    )

    has_nested_side = any(
        isinstance(row.get(side), Mapping)
        for side in ("CE", "PE")
    )

    if has_nested_side:
        for side in requested_types:
            payload = row.get(side)

            if not isinstance(payload, Mapping):
                continue

            premium = _positive_float(
                _get_value(
                    payload,
                    "lastPrice",
                    "last_price",
                    "LTP",
                    "ltp",
                    "premium",
                    "close",
                    "Close",
                )
            )

            side_strike = (
                _positive_float(
                    _get_value(
                        payload,
                        "strikePrice",
                        "strike",
                        "strike_price",
                    )
                )
                or strike
            )

            side_expiry = (
                _to_date(
                    _get_value(
                        payload,
                        "expiryDate",
                        "expiry",
                        "expiry_date",
                    )
                )
                or expiry
            )

            side_lot_size = _extract_lot_size(
                payload,
                default=_extract_lot_size(row),
            )

            result.append(
                {
                    "strike": side_strike,
                    "expiry": side_expiry,
                    "option_type": side,
                    "premium": premium,
                    "lot_size": side_lot_size,
                }
            )

        return result

    result.append(
        {
            "strike": strike,
            "expiry": expiry,
            "option_type": explicit_type,
            "premium": _extract_premium(row),
            "lot_size": _extract_lot_size(row),
        }
    )

    return result


def _build_candidates(
    option_chain: Any,
    option_type: str,
    expiry: Optional[date],
    require_premium: bool,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for row in _iter_rows(option_chain):
        for item in _expand_row(
            row,
            option_type=option_type,
        ):
            if item["option_type"] != option_type:
                continue

            strike = item["strike"]

            if strike is None:
                continue

            row_expiry = item["expiry"]

            if expiry is not None and row_expiry != expiry:
                continue

            premium = item["premium"]

            if require_premium and premium is None:
                continue

            candidates.append(item)

    return candidates


def _synthetic_contract(
    nifty_price: float,
    expiry: date,
    option_type: str,
    selection_mode: str,
    strike_step: int,
    lot_size: int,
) -> OptionContract:
    """
    Build a contract when only the underlying NIFTY price is supplied.

    This preserves the original selector API used by the backtest and
    signal-builder layers. Live premium discovery is handled separately
    by select_live_contract().
    """
    if expiry is None:
        raise OptionSelectionError(
            "expiry is required."
        )

    if nifty_price <= 0:
        raise OptionSelectionError(
            "nifty_price must be positive."
        )

    mode = _normalise_selection_mode(
        selection_mode
    )

    atm = round_to_strike(
        nifty_price,
        strike_step,
    )

    if mode == "ATM":
        strike = atm
    elif mode == "ITM":
        if option_type == "CE":
            strike = atm - strike_step
        else:
            strike = atm + strike_step
    else:
        if option_type == "CE":
            strike = atm + strike_step
        else:
            strike = atm - strike_step

    return OptionContract(
        expiry=expiry,
        strike=float(strike),
        option_type=option_type,
        premium=0.0,
        lot_size=lot_size,
        selection_mode=mode,
    )


def _select_from_candidates(
    candidates: list[dict[str, Any]],
    nifty_price: float,
    option_type: str,
    expiry: Optional[date],
    selection_mode: str,
    lot_size: int,
) -> OptionContract:
    if not candidates:
        raise OptionSelectionError(
            f"No valid option contract found for {option_type}."
        )

    mode = _normalise_selection_mode(
        selection_mode
    )

    def distance(item: dict[str, Any]) -> float:
        return abs(
            float(item["strike"]) - nifty_price
        )

    if mode == "ATM":
        preferred = candidates

    elif mode == "ITM":
        if option_type == "CE":
            preferred = [
                item
                for item in candidates
                if float(item["strike"]) <= nifty_price
            ]
        else:
            preferred = [
                item
                for item in candidates
                if float(item["strike"]) >= nifty_price
            ]

        if not preferred:
            preferred = candidates

    else:
        if option_type == "CE":
            preferred = [
                item
                for item in candidates
                if float(item["strike"]) >= nifty_price
            ]
        else:
            preferred = [
                item
                for item in candidates
                if float(item["strike"]) <= nifty_price
            ]

        if not preferred:
            preferred = candidates

    selected = min(
        preferred,
        key=distance,
    )

    selected_expiry = selected["expiry"]

    if selected_expiry is None:
        if expiry is None:
            raise OptionSelectionError(
                "Selected contract has no expiry."
            )

        selected_expiry = expiry

    premium = selected["premium"]

    if premium is None:
        premium = 0.0

    return OptionContract(
        expiry=selected_expiry,
        strike=float(selected["strike"]),
        option_type=option_type,
        premium=float(premium),
        lot_size=int(
            selected.get(
                "lot_size",
                lot_size,
            )
            or lot_size
        ),
        selection_mode=mode,
    )


def select_contract(
    option_chain: Any = None,
    spot: Optional[float] = None,
    option_type: str = "CE",
    expiry: Optional[date] = None,
    strike_step: int = 50,
    selection_mode: str = "ATM",
    lot_size: int = 65,
    *,
    nifty_price: Optional[float] = None,
) -> OptionContract:
    """
    Select an option contract.

    Backward-compatible calling styles:

        select_contract(
            nifty_price=25020,
            expiry=...,
            option_type="CE",
        )

    and:

        select_contract(
            option_chain,
            spot,
            "CE",
            expiry=...,
        )

    When no option-chain payload is supplied, this function selects the
    strike from the NIFTY price and leaves premium at 0.0.
    """
    if nifty_price is not None:
        if spot is not None and float(spot) != float(nifty_price):
            raise OptionSelectionError(
                "spot and nifty_price must match when both are supplied."
            )

        spot = nifty_price

    if spot is None:
        raise OptionSelectionError(
            "nifty_price is required."
        )

    try:
        spot_value = float(spot)
    except (TypeError, ValueError):
        raise OptionSelectionError(
            "nifty_price must be a positive number."
        ) from None

    if spot_value <= 0:
        raise OptionSelectionError(
            "nifty_price must be positive."
        )

    normalized_type = _normalise_option_type(
        option_type
    )

    mode = _normalise_selection_mode(
        selection_mode
    )

    if expiry is None:
        raise OptionSelectionError(
            "expiry is required."
        )

    if lot_size <= 0:
        raise OptionSelectionError(
            "lot_size must be greater than zero."
        )

    # No option-chain data means this is the historical/backtest
    # compatibility path.
    if option_chain is None:
        return _synthetic_contract(
            nifty_price=spot_value,
            expiry=expiry,
            option_type=normalized_type,
            selection_mode=mode,
            strike_step=strike_step,
            lot_size=lot_size,
        )

    candidates = _build_candidates(
        option_chain=option_chain,
        option_type=normalized_type,
        expiry=expiry,
        require_premium=False,
    )

    return _select_from_candidates(
        candidates=candidates,
        nifty_price=spot_value,
        option_type=normalized_type,
        expiry=expiry,
        selection_mode=mode,
        lot_size=lot_size,
    )


def select_atm_contract(
    option_chain: Any = None,
    spot: Optional[float] = None,
    option_type: str = "CE",
    expiry: Optional[date] = None,
    strike_step: int = 50,
    lot_size: int = 65,
    *,
    nifty_price: Optional[float] = None,
) -> OptionContract:
    """
    Backward-compatible ATM contract selector.
    """
    return select_contract(
        option_chain=option_chain,
        spot=spot,
        nifty_price=nifty_price,
        option_type=option_type,
        expiry=expiry,
        strike_step=strike_step,
        selection_mode="ATM",
        lot_size=lot_size,
    )


def select_live_contract(
    option_chain: Any = None,
    spot: Optional[float] = None,
    option_type: str = "CE",
    expiry: Optional[date] = None,
    strike_step: int = 50,
    selection_mode: str = "ATM",
    lot_size: int = 65,
    *,
    option_chain_payload: Any = None,
    nifty_price: Optional[float] = None,
) -> OptionContract:
    """
    Select a real live option contract from an NSE-style option-chain
    payload.

    Unlike select_contract(), this function requires a valid positive
    premium for the selected option.
    """
    payload = (
        option_chain_payload
        if option_chain_payload is not None
        else option_chain
    )

    if payload is None:
        raise OptionSelectionError(
            "Live option contract is not available without "
            "an option-chain payload."
        )

    if nifty_price is not None:
        if spot is not None and float(spot) != float(nifty_price):
            raise OptionSelectionError(
                "spot and nifty_price must match when both are supplied."
            )

        spot = nifty_price

    if spot is None:
        raise OptionSelectionError(
            "nifty_price is required."
        )

    try:
        spot_value = float(spot)
    except (TypeError, ValueError):
        raise OptionSelectionError(
            "nifty_price must be a positive number."
        ) from None

    if spot_value <= 0:
        raise OptionSelectionError(
            "nifty_price must be positive."
        )

    normalized_type = _normalise_option_type(
        option_type
    )

    mode = _normalise_selection_mode(
        selection_mode
    )

    if expiry is None:
        raise OptionSelectionError(
            "expiry is required."
        )

    candidates = _build_candidates(
        option_chain=payload,
        option_type=normalized_type,
        expiry=expiry,
        require_premium=True,
    )

    if not candidates:
        raise OptionSelectionError(
            f"Live {normalized_type} contract is not available "
            f"for expiry {expiry.isoformat()}."
        )

    return _select_from_candidates(
        candidates=candidates,
        nifty_price=spot_value,
        option_type=normalized_type,
        expiry=expiry,
        selection_mode=mode,
        lot_size=lot_size,
    )


__all__ = [
    "OptionContract",
    "OptionSelectionError",
    "round_to_strike",
    "select_atm_strike",
    "select_contract",
    "select_atm_contract",
    "select_live_contract",
]