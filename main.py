import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

import storage
import telegram_client
from signing import verify_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.init_db()
    yield


app = FastAPI(title="DevTrack Telegram Bot", lifespan=lifespan)


def _require_backend_api_key(authorization: str | None):
    expected = os.environ.get("BOT_SERVICE_API_KEY", "")
    if not expected or authorization != f"Bearer {expected}":
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


@app.post("/webhook")
async def webhook(request: Request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    expected_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    if not expected_secret or secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid secret token.")

    update = await request.json()
    message = update.get("message") or {}
    text = message.get("text", "")
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    chat_id = chat.get("id")

    if chat_id is None or not text.startswith("/start"):
        return {"detail": "ignored"}

    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        return {"detail": "missing token"}

    link_secret = os.environ.get("TELEGRAM_LINK_SECRET", "")
    user_id = verify_token(parts[1], link_secret) if link_secret else None
    if user_id is None:
        try:
            telegram_client.send_message(
                chat_id, "This link has expired. Go back to DevTrack Settings and try again."
            )
        except telegram_client.TelegramAPIError:
            pass
        return {"detail": "invalid token"}

    storage.upsert_link(user_id, chat_id, from_user.get("username", ""))
    try:
        telegram_client.send_message(chat_id, "✅ Your Telegram is now linked to DevTrack.")
    except telegram_client.TelegramAPIError:
        pass  # linking already succeeded; the confirmation is best-effort
    return {"detail": "ok"}
