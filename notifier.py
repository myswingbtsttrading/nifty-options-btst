from __future__ import annotations

import os

import requests


TELEGRAM_API_TIMEOUT = 30


def _telegram_token() -> str:
    return os.getenv(
        "TELEGRAM_TOKEN",
        "",
    ).strip()


def _telegram_chat_id() -> str:
    return os.getenv(
        "TELEGRAM_CHAT_ID",
        "",
    ).strip()


def send_alert(message: str) -> None:
    token = _telegram_token()
    chat_id = _telegram_chat_id()

    if not token:
        raise RuntimeError(
            "TELEGRAM_TOKEN is not configured. "
            "Add TELEGRAM_TOKEN to GitHub Actions repository secrets."
        )

    if not chat_id:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID is not configured. "
            "Add TELEGRAM_CHAT_ID to GitHub Actions repository secrets."
        )

    url = (
        "https://api.telegram.org/bot"
        + token
        + "/sendMessage"
    )

    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
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