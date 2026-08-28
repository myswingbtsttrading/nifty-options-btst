```python
from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from live_market_data import LiveMarketDataError
from live_signal_engine import build_live_signal
from notifier import send_alert
from nse_live_data import (
    fetch_nifty_option_chain,
    find_option_quote,
    nearest_nifty_expiry,
)
from yahoo_nifty_data import (
    fetch_nifty_quote,
    load_nifty_history,
)


DATA_DIR = Path("data")
STATE_FILE = DATA_DIR / "live_btst_signal.json"


def _load_historical_nifty_rows(
    current_price: float | None = None,
    previous_close: float | None = None,
):
    """
    Load NIFTY history for the live indicator engine.

    The current live price is appended to the historical series.
    Arguments remain optional for compatibility with automation tests.
    """

    rows = load_nifty_history(
        days=120
    )

    if not rows:
        raise LiveMarketDataError(
            "Yahoo Finance returned no NIFTY historical rows."
        )

    if len(rows) < 50:
        raise LiveMarketDataError(
            f"Fewer than 50 NIFTY historical rows were returned: "
            f"{len(rows)}."
        )

    if current_price is None:
        quote = fetch_nifty_quote()

        current_price = quote.price

        if previous_close is None:
            previous_close = quote.previous_close

    if previous_close is None:
        previous_close = float(current_price)

    rows = list(rows)

    rows.append(
        {
            "timestamp": datetime.now(),
            "close": float(current_price),
        }
    )

    return rows


def _format_signal_message(
    result,
) -> str:
    signal = result.signal
    nifty_signal = result.nifty_signal
    indicators = result.indicators

    if signal.decision != "BUY":
        return (
            "NIFTY BTST ALERT\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🟡 NO TRADE\n\n"
            f"NIFTY: ₹{signal.nifty_price:,.2f}\n"
            f"Decision: {signal.decision}\n"
            f"Confidence: {signal.confidence:.1f}%\n"
            f"Reason: {nifty_signal.reason}\n"
            f"EMA20: {indicators.ema20:.2f}\n"
            f"EMA50: {indicators.ema50:.2f}\n"
            f"RSI: {indicators.rsi:.1f}\n"
            "\nNo BTST position recommended."
        )

    return (
        "🚀 NIFTY BTST BUY ALERT\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"Direction: BUY {signal.direction}\n"
        f"Expiry: {signal.expiry}\n"
        f"Strike: {signal.strike}\n"
        f"Option: {signal.option_type}\n\n"
        f"Entry: ₹{signal.entry_price:,.2f}\n"
        f"Stop Loss: ₹{signal.stop_loss:,.2f}\n"
        f"Target: ₹{signal.target:,.2f}\n\n"
        f"Lots: {signal.lots}\n"
        f"Quantity: {signal.quantity}\n"
        f"Capital Required: "
        f"₹{signal.capital_required:,.2f}\n"
        f"Planned Risk: "
        f"₹{signal.planned_risk:,.2f}\n"
        f"Risk/Reward: "
        f"{signal.risk_reward_ratio:.2f}\n"
        f"Confidence: "
        f"{signal.confidence:.1f}%\n\n"
        f"NIFTY: ₹{signal.nifty_price:,.2f}\n"
        f"EMA20: {indicators.ema20:.2f}\n"
        f"EMA50: {indicators.ema50:.2f}\n"
        f"RSI: {indicators.rsi:.1f}\n\n"
        "📌 BTST: Buy near 3 PM.\n"
        "📌 Exit next trading morning according to "
        "the exit plan/target."
    )


def _save_signal_state(
    signal,
) -> None:
    """
    Save an active BUY position state.
    """

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if hasattr(signal, "to_dict"):
        payload = signal.to_dict()

        STATE_FILE.write_text(
            json.dumps(
                payload,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        return

    if hasattr(signal, "to_json"):
        STATE_FILE.write_text(
            signal.to_json(),
            encoding="utf-8",
        )

        return

    raise TypeError(
        "Signal object must provide to_dict() or to_json()."
    )


def _load_signal_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        raise LiveMarketDataError(
            "No BTST position state found."
        )

    try:
        payload = json.loads(
            STATE_FILE.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise LiveMarketDataError(
            "BTST position state is invalid."
        ) from exc

    if not isinstance(payload, dict):
        raise LiveMarketDataError(
            "BTST position state must be a JSON object."
        )

    return payload


def _persist_signal_state(
    result,
) -> None:
    """
    Persist only an active BUY position.

    A NO TRADE result removes stale state.
    """

    if result.signal.decision == "BUY":
        _save_signal_state(
            result.signal
        )

        print(
            f"BTST position state written to "
            f"{STATE_FILE}."
        )

        return

    if STATE_FILE.exists():
        STATE_FILE.unlink()

        print(
            "NO TRADE: removed stale BTST position state."
        )
    else:
        print(
            "NO TRADE: no BTST position state to remove."
        )


def _position_value(
    position: Mapping[str, Any],
    *names: str,
    default: Any = None,
) -> Any:
    for name in names:
        if name in position:
            return position[name]

    return default


def _format_sell_message(
    position: Mapping[str, Any],
    exit_price: float,
    exit_timestamp: datetime,
) -> str:
    entry_price = float(
        _position_value(
            position,
            "entry_price",
            "entryPrice",
            "price",
            default=0.0,
        )
    )

    quantity = int(
        float(
            _position_value(
                position,
                "quantity",
                "qty",
                default=1,
            )
        )
    )

    strike = _position_value(
        position,
        "strike",
        default="N/A",
    )

    option_type = _position_value(
        position,
        "option_type",
        "optionType",
        default="N/A",
    )

    expiry = _position_value(
        position,
        "expiry",
        default="N/A",
    )

    pnl = (
        float(exit_price) - entry_price
    ) * quantity

    if pnl >= 0:
        result_label = "PROFIT"
    else:
        result_label = "LOSS"

    return (
        "NIFTY BTST EXIT ALERT\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔴 {result_label}\n\n"
        f"Option: {option_type}\n"
        f"Strike: {strike}\n"
        f"Expiry: {expiry}\n\n"
        f"Entry Premium: ₹{entry_price:,.2f}\n"
        f"Exit Premium: ₹{float(exit_price):,.2f}\n"
        f"Quantity: {quantity}\n"
        f"P/L: ₹{pnl:,.2f}\n"
        f"Exit Time: {exit_timestamp}\n"
    )


def run_915() -> None:
    """
    Exit the persisted BTST position using the actual live
    option premium from the NSE option chain.
    """

    position = _load_signal_state()

    expiry_value = _position_value(
        position,
        "expiry",
    )

    if expiry_value is None:
        raise LiveMarketDataError(
            "BTST position state has no expiry."
        )

    expiry_text = str(
        expiry_value
    )

    try:
        expiry = date.fromisoformat(
            expiry_text
        )
    except ValueError:
        try:
            expiry = datetime.fromisoformat(
                expiry_text
            ).date()
        except ValueError as exc:
            raise LiveMarketDataError(
                "BTST position state contains an invalid expiry."
            ) from exc

    strike_value = _position_value(
        position,
        "strike",
    )

    if strike_value is None:
        raise LiveMarketDataError(
            "BTST position state has no strike."
        )

    strike = float(
        strike_value
    )

    option_type = str(
        _position_value(
            position,
            "option_type",
            "optionType",
            default="",
        )
    ).upper()

    if option_type not in {
        "CE",
        "PE",
    }:
        raise LiveMarketDataError(
            "BTST position state has an invalid option type."
        )

    chain = fetch_nifty_option_chain()

    # Use keyword arguments so the call remains compatible with
    # both the production implementation and the automation mocks.
    option_quote = find_option_quote(
        payload=chain,
        expiry=expiry,
        strike=strike,
        option_type=option_type,
    )

    exit_price = float(
        option_quote.price
    )

    if exit_price <= 0:
        raise LiveMarketDataError(
            "Live option exit premium must be positive."
        )

    exit_timestamp = getattr(
        option_quote,
        "timestamp",
        datetime.now(),
    )

    message = _format_sell_message(
        position=position,
        exit_price=exit_price,
        exit_timestamp=exit_timestamp,
    )

    send_alert(message)

    if STATE_FILE.exists():
        STATE_FILE.unlink()

    print(message)

    print(
        "BTST position state removed after exit."
    )


def run_3pm() -> None:
    quote = fetch_nifty_quote()

    historical_rows = _load_historical_nifty_rows(
        current_price=quote.price,
        previous_close=quote.previous_close,
    )

    result = build_live_signal(
        historical_rows=historical_rows,
        capital=100000.0,
        lot_size=65,
        today=date.today(),
    )

    # A NO TRADE result must not generate a Telegram alert.
    if result.signal.decision != "BUY":
        _persist_signal_state(
            result
        )

        message = _format_signal_message(
            result
        )

        print(message)

        return

    message = _format_signal_message(
        result
    )

    send_alert(message)

    _persist_signal_state(
        result
    )

    print(message)


def run_smoke() -> None:
    print(
        "NIFTY Options BTST production runner initialized."
    )

    print(
        "Underlying provider: Yahoo Finance."
    )

    print(
        "Option-chain provider: NSE."
    )

    print(
        "Modes: 3pm, 915, smoke."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NIFTY Options BTST production runner."
    )

    parser.add_argument(
        "--mode",
        choices=(
            "3pm",
            "915",
            "smoke",
        ),
        default="smoke",
    )

    args = parser.parse_args()

    if args.mode == "3pm":
        run_3pm()

    elif args.mode == "915":
        run_915()

    else:
        run_smoke()


if __name__ == "__main__":
    main()
```
