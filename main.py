from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Any

from live_market_data import LiveMarketDataError
from live_signal_engine import build_live_signal
from notifier import send_alert
from yahoo_nifty_data import load_nifty_history


DATA_DIR = Path("data")
STATE_FILE = DATA_DIR / "live_btst_signal.json"


def _load_historical_nifty_rows() -> list[dict[str, Any]]:
    """
    Load recent NIFTY daily history from Yahoo Finance.

    Step 11 makes Yahoo Finance the primary NIFTY spot/history provider.
    The live signal engine separately obtains the current quote from the
    same Yahoo provider.
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


def _format_signal_message(result) -> str:
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


def run_3pm() -> None:
    """
    Execute the complete 3 PM BTST signal pipeline.

    Data architecture:
        NIFTY spot/history -> Yahoo Finance
        option chain      -> NSE
        signal            -> live signal engine
        alert             -> Telegram
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
        print(
            "No BUY signal. Telegram BUY alert not sent."
        )
        return

    send_alert(message)

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    STATE_FILE.write_text(
        result.signal.to_json(),
        encoding="utf-8",
    )

    print(
        "Telegram BUY alert sent successfully."
    )


def run_smoke() -> None:
    print(
        "NIFTY Options BTST production runner initialized."
    )

    print(
        "Modes: 3pm, smoke."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NIFTY Options BTST production runner."
    )

    parser.add_argument(
        "--mode",
        choices=(
            "3pm",
            "smoke",
        ),
        default="smoke",
    )

    args = parser.parse_args()

    if args.mode == "3pm":
        run_3pm()
    else:
        run_smoke()


if __name__ == "__main__":
    main()