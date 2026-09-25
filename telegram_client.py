import os

import requests

TELEGRAM_API_BASE = "https://api.telegram.org"
REQUEST_TIMEOUT = 10


class TelegramAPIError(Exception):
    pass


def _call(method, payload=None, timeout=REQUEST_TIMEOUT):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise TelegramAPIError("TELEGRAM_BOT_TOKEN is not configured.")
    # Network errors and non-JSON replies surface as TelegramAPIError too, so the
    # /send endpoint answers 502 (which the backend handles) instead of crashing.
    try:
        response = requests.post(f"{TELEGRAM_API_BASE}/bot{token}/{method}", json=payload or {}, timeout=timeout)
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise TelegramAPIError(f"Telegram API unreachable or returned invalid data ({exc.__class__.__name__}).") from exc
    if not data.get("ok"):
        raise TelegramAPIError(data.get("description", "Telegram API call failed."))
    return data["result"]


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _call("sendMessage", payload)


def answer_callback_query(callback_query_id, text=""):
    return _call("answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text})


def set_my_commands(commands, language_code=None):
    payload = {"commands": commands}
    if language_code:
        payload["language_code"] = language_code
    return _call("setMyCommands", payload)


def set_webhook(url, secret_token):
    return _call("setWebhook", {"url": url, "secret_token": secret_token, "allowed_updates": ["message", "callback_query"]})


def delete_webhook():
    return _call("deleteWebhook", {"drop_pending_updates": False})


def get_updates(offset=None, timeout=25):
    payload = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
    if offset is not None:
        payload["offset"] = offset
    # The HTTP timeout must outlast Telegram's long-poll timeout.
    return _call("getUpdates", payload, timeout=timeout + 10)
