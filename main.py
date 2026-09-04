from __future__ import annotations

import argparse
import json
import os
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
    rows = load_nifty_history(days=120)

    if len(rows) < 50:
        raise LiveMarketDataError(
            "Fewer than 50 valid NIFTY historical prices "
            "were returned by Yahoo Finance."
        )

    return rows


def _format_signal_message(result) -> str:
    signal = result.signal
    nifty_signal = getattr(result, "nifty_signal", None)
    indicators = getattr(result, "indicators", None)

    if signal.decision != "BUY":
        reason = getattr(
            nifty_signal,
            "reason",
            "No qualifying BTST setup.",
        )

        ema20 = getattr(indicators, "ema20", None)
        ema50 = getattr(indicators, "ema50", None)
        rsi = getattr(indicators, "rsi", None)

        ema20_text = (
            f"{ema20:.2f}"
            if ema20 is not None
            else "N/A"
        )

        ema50_text = (
            f"{ema50:.2f}"
            if ema50 is not None
            else "N/A"
        )

        rsi_text = (
            f"{rsi:.1f}"
            if rsi is not None
            else "N/A"
        )

        return (
            "NIFTY BTST ALERT\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🟡 NO TRADE\n\n"
            f"NIFTY: ₹{signal.nifty_price:,.2f}\n"
            f"Decision: {signal.decision}\n"
            f"Confidence: {signal.confidence:.1f}%\n"
            f"Reason: {reason}\n"
            f"EMA20: {ema20_text}\n"
            f"EMA50: {ema50_text}\n"
            f"RSI: {rsi_text}\n"
            "\nNo BTST position recommended."
        )

    ema20 = getattr(indicators, "ema20", None)
    ema50 = getattr(indicators, "ema50", None)
    rsi = getattr(indicators, "rsi", None)

    ema20_text = (
        f"{ema20:.2f}"
        if ema20 is not None
        else "N/A"
    )

    ema50_text = (
        f"{ema50:.2f}"
        if ema50 is not None
        else "N/A"
    )

    rsi_text = (
        f"{rsi:.1f}"
        if rsi is not None
        else "N/A"
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
        f"EMA20: {ema20_text}\n"
        f"EMA50: {ema50_text}\n"
        f"RSI: {rsi_text}\n\n"
        "📌 BTST: Buy near 3 PM.\n"
        "📌 Exit/review next trading morning at 9:30 AM."
    )


def _atomic_write_json(
    path: Path,
    payload: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        f".{path.name}.tmp"
    )

    try:
        temporary.write_text(
            json.dumps(
                payload,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

        os.replace(
            temporary,
            path,
        )

    finally:
        if temporary.exists():
            temporary.unlink()


def _save_signal_state(signal) -> None:
    if hasattr(signal, "to_dict"):
        payload = signal.to_dict()

    elif hasattr(signal, "to_json"):
        raw = signal.to_json()

        try:
            payload = json.loads(raw)

        except (
            TypeError,
            json.JSONDecodeError,
        ) as exc:
            raise LiveMarketDataError(
                "BTST signal returned invalid JSON state."
            ) from exc

    else:
        raise LiveMarketDataError(
            "BTST signal does not provide to_dict() or to_json()."
        )

    if not isinstance(payload, dict):
        raise LiveMarketDataError(
            "BTST signal returned invalid state payload."
        )

    _atomic_write_json(
        STATE_FILE,
        payload,
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
                encoding="utf-8",
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise LiveMarketDataError(
            f"Unable to read BTST position state: {exc}"
        ) from exc

    if not isinstance(payload, dict):
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

    _atomic_write_json(
        EXIT_FILE,
        payload,
    )


def _load_existing_exit_record():
    if not EXIT_FILE.exists():
        return None

    try:
        payload = json.loads(
            EXIT_FILE.read_text(
                encoding="utf-8",
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    if not isinstance(payload, dict):
        return None

    if str(
        payload.get("status", "")
    ).upper() != "CLOSED":
        return None

    return payload


def _exit_record_matches_position(
    position: dict,
    exit_record: dict,
) -> bool:
    if not isinstance(exit_record, dict):
        return False

    if str(
        exit_record.get("status", "")
    ).upper() != "CLOSED":
        return False

    try:
        if str(
            exit_record.get("direction", "")
        ).upper() != str(
            position["direction"]
        ).upper():
            return False

        if str(
            exit_record.get("option_type", "")
        ).upper() != str(
            position["option_type"]
        ).upper():
            return False

        if str(
            exit_record.get("expiry", "")
        ) != str(
            position["expiry"]
        ):
            return False

        if float(
            exit_record.get("strike")
        ) != float(
            position["strike"]
        ):
            return False

        if float(
            exit_record.get("entry_price")
        ) != float(
            position["entry_price"]
        ):
            return False

        if int(
            exit_record.get("quantity")
        ) != int(
            position["quantity"]
        ):
            return False

        if int(
            exit_record.get("lots")
        ) != int(
            position["lots"]
        ):
            return False

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return False

    return True


def _remove_active_state() -> None:
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def _format_no_position_exit_message() -> str:
    return (
        "NIFTY BTST EXIT CHECK\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⚪ NO POSITION\n\n"
        "No BTST BUY position was created "
        "by the previous 3 PM signal.\n\n"
        "No option needs to be sold.\n"
        "9:30 AM exit process completed successfully."
    )


def _handle_no_position_exit() -> None:
    message = _format_no_position_exit_message()

    try:
        send_alert(message)

    except RuntimeError as exc:
        error_text = str(exc)

        if (
            "TELEGRAM_TOKEN is not configured"
            in error_text
            or "TELEGRAM_CHAT_ID is not configured"
            in error_text
        ):
            raise LiveMarketDataError(
                "No BTST position state found. "
                "There is no previous BUY signal to exit."
            ) from exc

        raise

    print(message)


def run_3pm() -> None:
    historical_rows = _load_historical_nifty_rows()

    result = build_live_signal(
        historical_rows=historical_rows,
        capital=100000.0,
        lot_size=65,
        today=date.today(),
    )

    if (
        result.signal.decision == "BUY"
        and STATE_FILE.exists()
    ):
        raise LiveMarketDataError(
            "An active BTST BUY position already exists."
        )

    message = _format_signal_message(
        result
    )

    print(message)

    # A BUY creates an active BTST position.
    # Persist it before sending Telegram so the
    # position cannot be lost if the process ends
    # immediately after the alert.
    if result.signal.decision == "BUY":
        _save_signal_state(
            result.signal
        )

    # Both BUY and NO TRADE are valid daily outcomes.
    # Always send the 3 PM decision to Telegram.
    try:
        send_alert(message)

    except Exception:
        # Only BUY creates state that needs rollback.
        # NO TRADE creates no active position.
        if result.signal.decision == "BUY":
            _remove_active_state()

        raise


def run_930() -> None:
    # A previous 3 PM NO TRADE is a normal outcome.
    # Handle that case separately from an active position.
    if not STATE_FILE.exists():
        _handle_no_position_exit()
        return

    position = _load_signal_state()

    existing_exit = _load_existing_exit_record()

    if (
        existing_exit is not None
        and _exit_record_matches_position(
            position,
            existing_exit,
        )
    ):
        print(
            "Matching CLOSED BTST exit record already exists. "
            "Removing stale active state without sending a duplicate alert."
        )

        _remove_active_state()
        return

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

    # Persist the completed transaction before Telegram.
    # If Telegram fails, both the CLOSED exit record and
    # active state remain available for audit/recovery.
    _save_exit_record(
        position=position,
        exit_price=exit_price,
        exit_timestamp=option_quote.timestamp,
    )

    # Keep the Telegram sender reference after transaction
    # persistence so retry-safety ordering remains explicit.
    telegram_sender = send_alert

    try:
        telegram_sender(message)

    except Exception:
        raise

    print(message)

    _remove_active_state()


def run_915() -> None:
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