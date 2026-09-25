"""Run the bot by long polling — for local development, where Telegram cannot reach a webhook.

    python poll.py

Deletes any registered webhook first (Telegram allows either a webhook or polling, not both), then
feeds every update through the same handler the webhook uses. Ctrl+C stops it.
"""

import logging
import time

from dotenv import load_dotenv

load_dotenv()

import handlers  # noqa: E402
import storage  # noqa: E402
import telegram_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("poll")


def run(once=False):
    storage.init_db()
    telegram_client.delete_webhook()
    from main import register_with_telegram

    register_with_telegram(webhook=False)  # polling and a webhook are mutually exclusive
    offset = None
    logger.info("Polling for updates…")
    while True:
        try:
            updates = telegram_client.get_updates(offset)
        except telegram_client.TelegramAPIError:
            logger.warning("getUpdates failed; retrying in 5 s.", exc_info=True)
            time.sleep(5)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            handlers.handle_update(update)
        if once:
            return


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        logger.info("Stopped.")
