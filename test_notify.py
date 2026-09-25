import pytest
from fastapi.testclient import TestClient

import main
import notifications
import poll
import storage
import telegram_client

AUTH = {"Authorization": "Bearer test-api-key"}


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    storage.init_db()


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture
def sent(monkeypatch):
    messages = []
    monkeypatch.setattr(telegram_client, "send_message", lambda chat_id, text, reply_markup=None: messages.append((chat_id, text, reply_markup)))
    return messages


def notify(client, **body):
    return client.post("/notify", json={"user_id": 1, **body}, headers=AUTH)


def test_notify_requires_the_api_key(client):
    assert client.post("/notify", json={"user_id": 1, "kind": "x"}).status_code == 403


def test_an_unlinked_user_is_a_404_and_a_muted_one_a_202(client, sent):
    assert notify(client, kind="issue_assigned", title="T").status_code == 404
    storage.upsert_link(1, 100, "a", "en")
    storage.set_muted(100, True)
    response = notify(client, kind="issue_assigned", title="T")
    assert response.status_code == 202 and response.json() == {"detail": "muted"}
    assert sent == []


def test_notifications_are_rendered_in_the_chats_language(client, sent):
    storage.upsert_link(1, 100, "a", "en")
    assert notify(client, kind="issue_assigned", actor="jane", title="Ship it", path="/issues/3").status_code == 200
    assert sent[-1][0] == 100 and "jane" in sent[-1][1] and "assigned you a task" in sent[-1][1]
    storage.set_lang(100, "uz")
    notify(client, kind="issue_assigned", actor="jane", title="Ship it")
    assert "tayinladi" in sent[-1][1]


def test_render_covers_every_kind(monkeypatch):
    for kind in ("issue_assigned", "commented", "mentioned", "workspace_invited", "project_member_added", "something_new"):
        text, _ = notifications.render("en", {"kind": kind, "actor": "bob", "title": "T", "excerpt": ""})
        assert "T" in text and "{" not in text


def test_user_supplied_text_is_escaped(monkeypatch):
    text, _ = notifications.render("en", {"kind": "commented", "actor": "<i>x</i>", "title": "A & B", "excerpt": "<script>"})
    assert "<i>x</i>" not in text and "&lt;script&gt;" in text and "A &amp; B" in text


def test_an_open_button_appears_only_for_a_public_https_frontend(monkeypatch):
    payload = {"kind": "issue_assigned", "actor": "a", "title": "T", "path": "/issues/9"}
    assert notifications.render("en", payload)[1] is None
    monkeypatch.setenv("FRONTEND_URL", "https://app.example.com/")
    assert notifications.render("en", payload)[1]["inline_keyboard"][0][0]["url"] == "https://app.example.com/issues/9"


def test_the_digest_lists_the_most_urgent_items(monkeypatch):
    payload = {"kind": "digest", "overdue": 1, "today": 1, "items": [
        {"id": 4, "title": "Late", "overdue": True, "path": "/issues/4"}, {"id": 5, "title": "Today", "overdue": False, "path": "/issues/5"}]}
    text, _ = notifications.render("en", payload)
    assert "1 overdue, 1 due today" in text
    assert text.index("#4") < text.index("#5") and "🔴" in text


def test_a_telegram_failure_is_a_502(client, monkeypatch):
    storage.upsert_link(1, 100, "a", "en")
    def fail(chat_id, text, reply_markup=None):
        raise telegram_client.TelegramAPIError("down")
    monkeypatch.setattr(telegram_client, "send_message", fail)
    assert notify(client, kind="issue_assigned", title="T").status_code == 502


# --- start-up, polling, storage ------------------------------------------------------------------------


def test_startup_registration_is_skipped_without_a_token(monkeypatch):
    calls = []
    monkeypatch.setattr(telegram_client, "set_my_commands", lambda *a, **k: calls.append("commands"))
    main.register_with_telegram()
    assert calls == []


def test_startup_registers_the_menu_and_the_webhook_only_for_a_public_https_url(monkeypatch):
    calls = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setattr(telegram_client, "set_my_commands", lambda commands, language_code=None: calls.append(("commands", language_code)))
    monkeypatch.setattr(telegram_client, "set_webhook", lambda url, secret: calls.append(("webhook", url, secret)))
    main.register_with_telegram()
    assert calls == [("commands", None), ("commands", "uz")]

    calls.clear()
    monkeypatch.setenv("PUBLIC_URL", "http://localhost:9000")
    main.register_with_telegram()
    assert ("webhook", "http://localhost:9000/webhook", "test-webhook-secret") not in calls

    monkeypatch.setenv("PUBLIC_URL", "https://bot.example.com/")
    calls.clear()
    main.register_with_telegram()
    assert ("webhook", "https://bot.example.com/webhook", "test-webhook-secret") in calls
    calls.clear()
    main.register_with_telegram(webhook=False)  # what the poller does
    assert not any(c[0] == "webhook" for c in calls)


def test_startup_survives_telegram_being_down(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    def fail(*a, **k):
        raise telegram_client.TelegramAPIError("down")
    monkeypatch.setattr(telegram_client, "set_my_commands", fail)
    main.register_with_telegram()  # must not raise


def test_the_poller_feeds_updates_through_the_same_handler_and_advances_the_offset(monkeypatch):
    seen, offsets = [], []
    monkeypatch.setattr(telegram_client, "delete_webhook", lambda: None)
    def fake_updates(offset=None, timeout=25):
        offsets.append(offset)
        return [{"update_id": 10, "message": {"chat": {"id": 1}, "text": "/help"}}, {"update_id": 11}]
    monkeypatch.setattr(telegram_client, "get_updates", fake_updates)
    monkeypatch.setattr(poll.handlers, "handle_update", lambda update: seen.append(update["update_id"]))
    poll.run(once=True)
    assert seen == [10, 11] and offsets == [None]


def test_old_databases_gain_the_language_and_mute_columns(tmp_path, monkeypatch):
    import sqlite3
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE links (devtrack_user_id INTEGER PRIMARY KEY, chat_id INTEGER UNIQUE NOT NULL, telegram_username TEXT NOT NULL DEFAULT '', linked_at TEXT NOT NULL DEFAULT (datetime('now')))")
    conn.execute("INSERT INTO links (devtrack_user_id, chat_id) VALUES (3, 30)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(storage, "DB_PATH", path)
    storage.init_db()
    link = storage.get_link(3)
    assert (link["lang"], link["muted"]) == ("", 0)
    storage.set_lang(30, "en")
    assert storage.get_link_by_chat(30)["lang"] == "en"


def test_relinking_keeps_a_chosen_language_unless_a_new_one_is_given():
    storage.upsert_link(1, 10, "a", "en")
    storage.upsert_link(1, 10, "a", "")
    assert storage.get_link(1)["lang"] == "en"
    storage.upsert_link(1, 10, "a", "uz")
    assert storage.get_link(1)["lang"] == "uz"
