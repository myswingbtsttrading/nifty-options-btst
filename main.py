from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from live_market_data import LiveMarketDataError
from live_signal_engine import build_live_signal
from notifier import send_alert
from nse_live_data import (
    fetch_nifty_option_chain,
    find_option_quote,
)
from yahoo_nifty_data import load_nifty_history


DATA_DIR = Path("data")
STATE_FILE = DATA_DIR / "live_btst_signal.json"
EXIT_FILE = DATA_DIR / "last_btst_exit.json"


def _load_historical_nifty_rows():
    """
    Load recent NIFTY daily history from Yahoo Finance.

    The current live NIFTY quote is intentionally not fetched here.
    build_live_signal() owns the live quote and option-chain retrieval.
    """
    rows = load_nifty_history(
        days=120
    )

    if len(rows) < 50:
        raise LiveMarketDataError(
            "Fewer than 50 valid NIFTY historical prices "
            "were returned by Yahoo Finance."
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
        "📌 Exit/review next trading morning at 9:30 AM."
    )


def _save_signal_state(
    signal,
) -> None:
    """
    Persist an actionable BUY signal.

    Supports both the real BTSTSignal.to_dict() API and the
    older to_json() compatibility API used by existing tests.
    """
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if hasattr(
        signal,
        "to_dict",
    ):
        payload = signal.to_dict()

        STATE_FILE.write_text(
            json.dumps(
                payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        return

    if hasattr(
        signal,
        "to_json",
    ):
        raw = signal.to_json()

        try:
            parsed = json.loads(raw)
        except (
            TypeError,
            json.JSONDecodeError,
        ) as exc:
            raise LiveMarketDataError(
                "BTST signal returned invalid JSON state."
            ) from exc

        STATE_FILE.write_text(
            json.dumps(
                parsed,
                indent=2,
            ),
            encoding="utf-8",
        )

        return

    raise LiveMarketDataError(
        "BTST signal does not provide to_dict() or to_json()."
    )


def _load_signal_state() -> dict:
    if not STATE_FILE.exists():
        raise LiveMarketDataError(
            "No BTST position state found. "
            "There is no previous BUY signal to exit."
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
            f"Unable to read BTST position state: {exc}"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise LiveMarketDataError(
            "BTST position state is invalid."
        )

    required = (
        "decision",
        "direction",
        "expiry",
        "strike",
        "option_type",
        "entry_price",
        "quantity",
        "lots",
    )

    missing = [
        key
        for key in required
        if key not in payload
    ]

    if missing:
        raise LiveMarketDataError(
            "BTST position state is missing: "
            + ", ".join(missing)
        )

    if str(
        payload["decision"]
    ).upper() != "BUY":
        raise LiveMarketDataError(
            "Stored BTST position is not an active BUY."
        )

    try:
        entry_price = float(
            payload["entry_price"]
        )
        quantity = int(
            payload["quantity"]
        )
        lots = int(
            payload["lots"]
        )
        strike = float(
            payload["strike"]
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise LiveMarketDataError(
            "BTST position state contains invalid numeric values."
        ) from exc

    if entry_price <= 0:
        raise LiveMarketDataError(
            "Stored BTST entry premium must be positive."
        )

    if quantity <= 0:
        raise LiveMarketDataError(
            "Stored BTST quantity must be positive."
        )

    if lots <= 0:
        raise LiveMarketDataError(
            "Stored BTST lots must be positive."
        )

    if strike <= 0:
        raise LiveMarketDataError(
            "Stored BTST strike must be positive."
        )

    option_type = str(
        payload["option_type"]
    ).upper()

    if option_type not in {
        "CE",
        "PE",
    }:
        raise LiveMarketDataError(
            "Stored BTST option_type must be CE or PE."
        )

    try:
        date.fromisoformat(
            str(payload["expiry"])
        )
    except ValueError as exc:
        raise LiveMarketDataError(
            "Stored BTST expiry is invalid."
        ) from exc

    return payload


def _calculate_pnl(
    entry_price: float,
    exit_price: float,
    quantity: int,
) -> tuple[float, float]:
    if entry_price <= 0:
        raise LiveMarketDataError(
            "Entry premium must be positive."
        )

    if exit_price <= 0:
        raise LiveMarketDataError(
            "Exit premium must be positive."
        )

    if quantity <= 0:
        raise LiveMarketDataError(
            "Quantity must be positive."
        )

    pnl = (
        exit_price - entry_price
    ) * quantity

    pnl_pct = (
        (
            exit_price - entry_price
        )
        / entry_price
        * 100.0
    )

    return pnl, pnl_pct


def _format_sell_message(
    position: dict,
    exit_price: float,
    exit_timestamp,
) -> str:
    entry_price = float(
        position["entry_price"]
    )

    quantity = int(
        position["quantity"]
    )

    pnl, pnl_pct = _calculate_pnl(
        entry_price=entry_price,
        exit_price=exit_price,
        quantity=quantity,
    )

    if pnl > 0:
        result = "🟢 PROFIT"
    elif pnl < 0:
        result = "🔴 LOSS"
    else:
        result = "⚪ BREAKEVEN"

    return (
        "📤 NIFTY BTST SELL ALERT\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{result}\n\n"
        f"Option: {position['strike']} "
        f"{position['option_type']}\n"
        f"Expiry: {position['expiry']}\n"
        f"Quantity: {quantity}\n"
        f"Lots: {position['lots']}\n\n"
        f"Entry Premium: ₹{entry_price:,.2f}\n"
        f"Exit Premium: ₹{exit_price:,.2f}\n"
        f"P/L: ₹{pnl:,.2f}\n"
        f"P/L %: {pnl_pct:+.2f}%\n\n"
        f"Exit Time: {exit_timestamp}\n"
        "Position closed by the 9:30 AM BTST exit process."
    )


def _save_exit_record(
    position: dict,
    exit_price: float,
    exit_timestamp,
) -> None:
    """
    Persist the completed exit result.

    This provides an audit record after the active BUY state
    has been removed.
    """
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    entry_price = float(
        position["entry_price"]
    )
    quantity = int(
        position["quantity"]
    )

    pnl, pnl_pct = _calculate_pnl(
        entry_price=entry_price,
        exit_price=exit_price,
        quantity=quantity,
    )

    payload = {
        "status": "CLOSED",
        "closed_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "entry_timestamp": position.get(
            "timestamp"
        ),
        "exit_timestamp": str(
            exit_timestamp
        ),
        "direction": position["direction"],
        "option_type": position["option_type"],
        "strike": float(
            position["strike"]
        ),
        "expiry": position["expiry"],
        "entry_price": entry_price,
        "exit_price": exit_price,
        "quantity": quantity,
        "lots": int(
            position["lots"]
        ),
        "pnl": pnl,
        "pnl_pct": pnl_pct,
    }

    EXIT_FILE.write_text(
        json.dumps(
            payload,
            indent=2,
        ),
        encoding="utf-8",
    )


def run_3pm() -> None:
    """
    Generate the 3 PM BTST signal.

    Telegram is sent only for an actionable BUY.
    A WAIT/NO TRADE result is printed but does not generate
    a Telegram alert or position state.
    """
    historical_rows = _load_historical_nifty_rows()

    result = build_live_signal(
        historical_rows=historical_rows,
        capital=100000.0,
        lot_size=65,
        today=date.today(),
    )

    message = _format_signal_message(
        result
    )

    print(message)

    if result.signal.decision != "BUY":
        return

    send_alert(message)

    _save_signal_state(
        result.signal
    )


def run_930() -> None:
    """
    Close the previous BTST position using the current live
    premium of the exact stored option contract.

    State is removed only after:
        1. The exact contract is found.
        2. A positive live premium is received.
        3. The SELL Telegram alert succeeds.
        4. The completed exit record is persisted.
    """
    position = _load_signal_state()

    chain = fetch_nifty_option_chain()

    try:
        expiry = date.fromisoformat(
            str(position["expiry"])
        )
    except ValueError as exc:
        raise LiveMarketDataError(
            "Stored BTST expiry is invalid."
        ) from exc

    option_type = str(
        position["option_type"]
    ).upper()

    if option_type not in {
        "CE",
        "PE",
    }:
        raise LiveMarketDataError(
            "Stored BTST option_type must be CE or PE."
        )

    strike = float(
        position["strike"]
    )

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
            "Current option premium must be positive."
        )

    message = _format_sell_message(
        position=position,
        exit_price=exit_price,
        exit_timestamp=option_quote.timestamp,
    )

    # Send the SELL alert before mutating/removing the active
    # position state. If Telegram fails, the BUY remains active
    # and the next execution can safely retry.
    send_alert(message)

    # Persist the completed transaction before deleting the
    # active state. If persistence fails, the BUY remains active.
    _save_exit_record(
        position=position,
        exit_price=exit_price,
        exit_timestamp=option_quote.timestamp,
    )

    print(message)

    if STATE_FILE.exists():
        STATE_FILE.unlink()


def run_915() -> None:
    """
    Backward-compatible alias for the old 9:15 AM exit mode.

    Production scheduling is now 9:30 AM.
    """
    run_930()


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
        "Modes: 3pm, 930, 915, smoke."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NIFTY Options BTST production runner."
    )

    parser.add_argument(
        "--mode",
        choices=(
            "3pm",
            "930",
            "915",
            "smoke",
        ),
        default="smoke",
    )

    args = parser.parse_args()

    if args.mode == "3pm":
        run_3pm()
    elif args.mode in {
        "930",
        "915",
    }:
        run_930()
    else:
        run_smoke()


if __name__ == "__main__":
    main()