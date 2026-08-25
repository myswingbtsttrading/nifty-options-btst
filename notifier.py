from __future__ import annotations

import requests

from config import (
    TELEGRAM_CHAT_ID,
    TELEGRAM_TOKEN,
)


TELEGRAM_API_TIMEOUT = 30


def send_alert(message: str) -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError(
            "TELEGRAM_TOKEN is not configured."
        )

    if not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID is not configured."
        )

    url = (
        "https://api.telegram.org/bot"
        + TELEGRAM_TOKEN
        + "/sendMessage"
    )

    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
        },
        timeout=TELEGRAM_API_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(
            data.get(
                "description",
                "Telegram request failed.",
            )
        )


def send_test_alert() -> None:
    send_alert(
        "✅ NIFTY BTST Telegram connection is working."
    )