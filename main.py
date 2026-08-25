from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from btst_signal_runner import (
    BTSTRunnerConfig,
    run_3pm_signal,
)
from live_market_data import LiveMarketDataError
from nse_live_data import (
    fetch_nifty_option_chain,
    fetch_nifty_quote,
    nearest_nifty_expiry,
)
from notifier import send_alert
from option_selector import OptionContract
from signal_builder import OptionQuote
from live_signal_engine import calculate_indicators
from option_chain_confirmation import OptionChainSnapshot
from option_strategy import generate_signal


DATA_DIR = Path("data")
STATE_FILE = DATA_DIR / "live_btst_signal.json"


def _load_historical_nifty_rows(
    current_price: float,
    previous_close: float,
) -> list[dict[str, Any]]:
    """
    Build a deterministic recent NIFTY history for the live engine.

    NSE supplies the current market snapshot and option chain, while
    the repository's live engine requires at least 50 underlying prices.
    We use Yahoo Finance's public chart endpoint as the historical
    daily-price source and keep the current NSE price as the final
    observation.
    """
    import requests

    now = datetime.now()
    start = now - timedelta(days=120)

    response = requests.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI",
        params={
            "period1": int(start.timestamp()),
            "period2": int((now + timedelta(days=1)).timestamp()),
            "interval": "1d",
            "events": "history",
        },
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Linux; Android 10) "
                "AppleWebKit/537.36 "
                "Chrome/151.0 Mobile Safari/537.36"
            )
        },
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()

    result = payload.get("chart", {}).get("result")

    if not result:
        raise LiveMarketDataError(
            "Yahoo Finance returned no NIFTY historical data."
        )

    chart = result[0]

    timestamps = chart.get("timestamp", [])
    closes = (
        chart.get("indicators", {})
        .get("quote", [{}])[0]
        .get("close", [])
    )

    rows: list[dict[str, Any]] = []

    for timestamp, close in zip(
        timestamps,
        closes,
    ):
        if close is None:
            continue

        rows.append(
            {
                "timestamp": datetime.fromtimestamp(
                    timestamp
                ),
                "close": float(close),
            }
        )

    if len(rows) < 50:
        raise LiveMarketDataError(
            "Fewer than 50 valid NIFTY historical prices "
            "were returned."
        )

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
        f"Capital Required: ₹{signal.capital_required:,.2f}\n"
        f"Planned Risk: ₹{signal.planned_risk:,.2f}\n"
        f"Risk/Reward: {signal.risk_reward_ratio:.2f}\n"
        f"Confidence: {signal.confidence:.1f}%\n\n"
        f"NIFTY: ₹{signal.nifty_price:,.2f}\n"
        f"EMA20: {indicators.ema20:.2f}\n"
        f"EMA50: {indicators.ema50:.2f}\n"
        f"RSI: {indicators.rsi:.1f}\n\n"
        "📌 BTST: Buy near 3 PM.\n"
        "📌 Exit next trading morning according to "
        "the exit plan/target."
    )


def run_3pm() -> None:
    quote = fetch_nifty_quote()

    historical_rows = _load_historical_nifty_rows(
        current_price=quote.price,
        previous_close=quote.previous_close,
    )

    chain = fetch_nifty_option_chain()

    expiry = nearest_nifty_expiry(
        chain,
        today=date.today(),
    )

    from live_signal_engine import build_live_signal

    result = build_live_signal(
        historical_rows=historical_rows,
        capital=100000.0,
        lot_size=65,
        today=date.today(),
    )

    message = _format_signal_message(result)

    send_alert(message)

    if result.signal.decision == "BUY":
        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        STATE_FILE.write_text(
            result.signal.to_json(),
            encoding="utf-8",
        )

    print(message)


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