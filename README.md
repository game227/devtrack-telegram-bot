# DevTrack Telegram Bot

A small standalone service that connects DevTrack users to Telegram. It is the
third piece of DevTrack, next to
[devtrack-backend](https://github.com/game227/devtrack-backend) and
[devtrack-frontend](https://github.com/game227/devtrack-frontend).

What it does:

- **Links accounts.** A user presses *Connect Telegram* in DevTrack → Settings,
  taps *Start* in the bot, and the bot stores `DevTrack user id ↔ Telegram chat`.
  The deep-link token is HMAC-signed by the backend and verified here.
- **Delivers messages.** The backend asks this service to send a message (used for
  password-reset links). If the user is not linked, or Telegram is unreachable,
  the backend falls back to email.

Messages sent by the bot are bilingual (Uzbek + English) because it does not know
the user's interface language.

## API

All calls except `/health` and `/webhook` need `Authorization: Bearer <BOT_SERVICE_API_KEY>`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness probe |
| POST | `/send` | `{user_id, text}` → send a Telegram message (404 if not linked, 502 if Telegram fails) |
| GET | `/status/{user_id}` | `{connected, telegram_username, linked_at}` |
| DELETE | `/link/{user_id}` | Remove the link |
| POST | `/webhook` | Telegram updates; verified with `X-Telegram-Bot-Api-Secret-Token` |

## Configuration

Copy `.env.example` to `.env` (it is loaded automatically) or set real environment variables.

| Variable | Meaning |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | The `secret_token` you pass to `setWebhook` |
| `TELEGRAM_LINK_SECRET` | Shared with the backend; signs/verifies `/start` deep-link tokens |
| `BOT_SERVICE_API_KEY` | Shared with the backend; authenticates its calls to this service |
| `DATABASE_PATH` | SQLite file location (default `./bot.db`). Use a persistent disk in production |

Register the webhook once the service has a public HTTPS URL:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=https://<your-host>/webhook" -d "secret_token=$TELEGRAM_WEBHOOK_SECRET"
```

## Run locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # then fill it in
uvicorn main:app --port 9000
pytest -q
```

## Docker

```bash
docker build -t devtrack-telegram-bot .
docker run -p 8000:8000 --env-file .env -v bot-data:/data -e DATABASE_PATH=/data/bot.db devtrack-telegram-bot
```

## Notes

- SQLite keeps the service dependency-free; mount a persistent volume for `DATABASE_PATH`,
  otherwise links disappear on redeploy (users would simply have to link again).
- Rotate `BOT_SERVICE_API_KEY` and `TELEGRAM_LINK_SECRET` on both services at the same time.
