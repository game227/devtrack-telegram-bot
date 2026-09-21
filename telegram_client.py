import os

import requests

TELEGRAM_API_BASE = "https://api.telegram.org"
REQUEST_TIMEOUT = 10


class TelegramAPIError(Exception):
    pass


def send_message(chat_id, text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise TelegramAPIError("TELEGRAM_BOT_TOKEN is not configured.")
    # Network errors and non-JSON replies surface as TelegramAPIError too, so the
    # /send endpoint answers 502 (which the backend handles) instead of crashing.
    try:
        response = requests.post(
            f"{TELEGRAM_API_BASE}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=REQUEST_TIMEOUT,
        )
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise TelegramAPIError(f"Telegram API unreachable or returned invalid data ({exc.__class__.__name__}).") from exc
    if not data.get("ok"):
        raise TelegramAPIError(data.get("description", "Telegram API call failed."))
    return data["result"]
