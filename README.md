# DevTrack Telegram Bot

A small standalone service that connects DevTrack users to Telegram. It is the
third piece of DevTrack, next to
[devtrack-backend](https://github.com/game227/devtrack-backend) and
[devtrack-frontend](https://github.com/game227/devtrack-frontend).

What it does:

- **Links accounts.** A user presses *Connect Telegram* in DevTrack → Settings,
  taps *Start* in the bot, and the bot stores `DevTrack user id ↔ Telegram chat`.
  The deep-link token is HMAC-signed by the backend and verified here.
- **Answers commands** (Uzbek or English, per chat — `/lang`). It reads and changes
  tasks through the backend's `telegram/bot/` API *as the linked user*, so it can do
  exactly what that user could do in the web app — for example only a task's creator
  can change its status.
- **Pushes notifications.** Assignments, comments, @mentions and invitations, plus an
  optional morning digest of overdue / due-today tasks. `/mute` silences them.
- **Delivers messages.** The backend asks this service to send a message (used for
  password-reset links, which ignore `/mute`). If the user is not linked, or Telegram is
  unreachable, the backend falls back to email.

## Commands

| Command | What it does |
|---|---|
| `/tasks`, `/overdue`, `/soon` | My open tasks / overdue / due within 3 days — with **Done** and **Open** buttons |
| `/projects` | Projects with progress, and a health button each |
| `/health <id>` | Project health: score, factors, why it was held back, risks |
| `/new [project id] <title>` | Create a task (the project id may be left out when you have only one project) |
| `/done <id>`, `/status <id> <status>` | Change a task's status (creator only) |
| `/comment <id> <text>` | Comment on a task |
| `/lang uz\|en`, `/mute`, `/unmute`, `/me`, `/unlink`, `/help` | Chat settings |

## API

All calls except `/health` and `/webhook` need `Authorization: Bearer <BOT_SERVICE_API_KEY>`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness probe |
| POST | `/send` | `{user_id, text}` → send a Telegram message (404 if not linked, 502 if Telegram fails) |
| POST | `/notify` | `{user_id, kind, actor, title, excerpt, path, ...}` → a DevTrack event, rendered in the chat's language (404 not linked, 202 muted, 502 Telegram failure) |
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
| `BACKEND_URL` | Where devtrack-backend lives (default `http://localhost:8000`) |
| `FRONTEND_URL` | The web app's public https URL, for *Open* buttons (leave empty locally: Telegram rejects localhost links) |
| `PUBLIC_URL` | This service's public https URL. When set, the command menu and the webhook are registered with Telegram on start-up |

With `PUBLIC_URL` set the webhook is registered automatically. Otherwise register it once by hand:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=https://<your-host>/webhook" -d "secret_token=$TELEGRAM_WEBHOOK_SECRET"
```

On the backend, set `TELEGRAM_NOTIFICATIONS_ENABLED=true` to push notifications, and run
`python manage.py send_telegram_digest` from a scheduler for the morning digest.

## Run locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # then fill it in
uvicorn main:app --port 9000   # needs a public URL for Telegram to reach the webhook
python poll.py                 # ...or, locally, long-poll Telegram instead: no tunnel needed
pytest -q
```

`poll.py` and the webhook are mutually exclusive (Telegram allows one); polling removes any registered webhook.

## Docker

```bash
docker build -t devtrack-telegram-bot .
docker run -p 8000:8000 --env-file .env -v bot-data:/data -e DATABASE_PATH=/data/bot.db devtrack-telegram-bot
```

## Notes

- SQLite keeps the service dependency-free; mount a persistent volume for `DATABASE_PATH`,
  otherwise links disappear on redeploy (users would simply have to link again).
- Rotate `BOT_SERVICE_API_KEY` and `TELEGRAM_LINK_SECRET` on both services at the same time.
