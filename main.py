import hmac
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Body, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Read .env (if present) before anything looks at the environment, so
# `uvicorn main:app` works locally without exporting every variable by hand.
load_dotenv()

import handlers  # noqa: E402
import notifications  # noqa: E402
import storage  # noqa: E402
import telegram_client  # noqa: E402
from texts import DEFAULT_LANG  # noqa: E402

logger = logging.getLogger(__name__)


def register_with_telegram(webhook=True):
    """Best-effort start-up housekeeping: the command menu, and the webhook when a public URL is set.

    Never fatal — the service must still boot (and answer /health) if Telegram is unreachable or
    the token is not configured yet.
    """
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        return
    try:
        telegram_client.set_my_commands([{"command": c, "description": d} for c, d in handlers.COMMAND_MENU["en"]])
        telegram_client.set_my_commands(
            [{"command": c, "description": d} for c, d in handlers.COMMAND_MENU["uz"]], language_code="uz"
        )
        public_url = os.environ.get("PUBLIC_URL", "").rstrip("/")
        if webhook and public_url.startswith("https://"):
            telegram_client.set_webhook(f"{public_url}/webhook", os.environ.get("TELEGRAM_WEBHOOK_SECRET", ""))
    except telegram_client.TelegramAPIError:
        logger.warning("Could not register the command menu / webhook with Telegram.", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.init_db()
    register_with_telegram()
    yield


app = FastAPI(title="DevTrack Telegram Bot", lifespan=lifespan)


def _require_backend_api_key(authorization: str | None):
    expected = os.environ.get("BOT_SERVICE_API_KEY", "")
    if not expected or not hmac.compare_digest(authorization or "", f"Bearer {expected}"):
        raise HTTPException(status_code=403, detail="Invalid or missing API key.")


@app.get("/health")
def health():
    return {"status": "ok"}


class SendMessageBody(BaseModel):
    user_id: int
    text: str


@app.post("/send")
def send(body: SendMessageBody, authorization: str | None = Header(default=None)):
    _require_backend_api_key(authorization)
    link = storage.get_link(body.user_id)
    if link is None:
        raise HTTPException(status_code=404, detail="No linked Telegram chat for this user.")
    try:
        telegram_client.send_message(link["chat_id"], body.text)
    except telegram_client.TelegramAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"detail": "sent"}


@app.get("/status/{user_id}")
def status(user_id: int, authorization: str | None = Header(default=None)):
    _require_backend_api_key(authorization)
    link = storage.get_link(user_id)
    if link is None:
        return {"connected": False}
    return {
        "connected": True,
        "telegram_username": link["telegram_username"],
        "linked_at": link["linked_at"],
    }


@app.delete("/link/{user_id}")
def unlink(user_id: int, authorization: str | None = Header(default=None)):
    _require_backend_api_key(authorization)
    storage.delete_link(user_id)
    return {"detail": "deleted"}


class NotifyBody(BaseModel):
    user_id: int
    kind: str
    actor: str = ""
    title: str = ""
    excerpt: str = ""
    path: str = ""
    overdue: int = 0
    today: int = 0
    items: list[dict] = []


@app.post("/notify")
def notify(body: NotifyBody, authorization: str | None = Header(default=None)):
    """A DevTrack event for a user: rendered in their chat's language, unless they muted the bot."""
    _require_backend_api_key(authorization)
    link = storage.get_link(body.user_id)
    if link is None:
        raise HTTPException(status_code=404, detail="No linked Telegram chat for this user.")
    if link["muted"]:
        return JSONResponse({"detail": "muted"}, status_code=202)
    text, markup = notifications.render(link["lang"] or DEFAULT_LANG, body.model_dump())
    try:
        if markup:
            telegram_client.send_message(link["chat_id"], text, reply_markup=markup)
        else:
            telegram_client.send_message(link["chat_id"], text)
    except telegram_client.TelegramAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"detail": "sent"}


@app.post("/webhook")
def webhook(update: dict = Body(...), x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    expected_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    if not expected_secret or not hmac.compare_digest(x_telegram_bot_api_secret_token or "", expected_secret):
        raise HTTPException(status_code=403, detail="Invalid secret token.")
    # A plain `def` runs in FastAPI's thread pool, so the blocking HTTP calls inside never stall the server.
    handlers.handle_update(update)
    return {"detail": "ok"}
