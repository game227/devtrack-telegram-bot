import os

# Set before any module reads them, whichever test file pytest imports first.
os.environ.setdefault("BOT_SERVICE_API_KEY", "test-api-key")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("TELEGRAM_LINK_SECRET", "test-link-secret")
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["FRONTEND_URL"] = ""
os.environ["PUBLIC_URL"] = ""
