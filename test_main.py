import os

os.environ["BOT_SERVICE_API_KEY"] = "test-api-key"
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["TELEGRAM_LINK_SECRET"] = "test-link-secret"
os.environ["TELEGRAM_BOT_TOKEN"] = ""

import storage  # noqa: E402
from signing import sign_user_id  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
import telegram_client  # noqa: E402

AUTH = {"Authorization": "Bearer test-api-key"}


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    storage.init_db()
    yield


@pytest.fixture
def client():
    return TestClient(main.app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_status_requires_api_key(client):
    response = client.get("/status/1")
    assert response.status_code == 403


def test_status_defaults_to_not_connected(client):
    response = client.get("/status/1", headers=AUTH)
    assert response.status_code == 200
    assert response.json() == {"connected": False}


def test_webhook_rejects_wrong_secret(client):
    response = client.post(
        "/webhook",
        json={"message": {}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert response.status_code == 403


def test_webhook_links_account_with_valid_token(client):
    token = sign_user_id(42, "test-link-secret")
    response = client.post(
        "/webhook",
        json={"message": {"chat": {"id": 555}, "from": {"username": "alice"}, "text": f"/start {token}"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert response.status_code == 200

    status_response = client.get("/status/42", headers=AUTH)
    body = status_response.json()
    assert body["connected"] is True
    assert body["telegram_username"] == "alice"
    assert "linked_at" in body


def test_webhook_ignores_expired_or_tampered_token(client):
    response = client.post(
        "/webhook",
        json={"message": {"chat": {"id": 555}, "from": {"username": "alice"}, "text": "/start garbage"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert response.status_code == 200
    assert client.get("/status/42", headers=AUTH).json() == {"connected": False}


def test_relinking_chat_moves_it_to_new_user(client):
    token1 = sign_user_id(1, "test-link-secret")
    client.post(
        "/webhook",
        json={"message": {"chat": {"id": 999}, "from": {"username": "first"}, "text": f"/start {token1}"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    token2 = sign_user_id(2, "test-link-secret")
    client.post(
        "/webhook",
        json={"message": {"chat": {"id": 999}, "from": {"username": "second"}, "text": f"/start {token2}"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert client.get("/status/1", headers=AUTH).json() == {"connected": False}
    assert client.get("/status/2", headers=AUTH).json()["connected"] is True


def test_unlink_removes_account(client):
    token = sign_user_id(7, "test-link-secret")
    client.post(
        "/webhook",
        json={"message": {"chat": {"id": 111}, "from": {"username": "bob"}, "text": f"/start {token}"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    delete_response = client.delete("/link/7", headers=AUTH)
    assert delete_response.status_code == 200
    assert client.get("/status/7", headers=AUTH).json() == {"connected": False}


def test_send_without_link_returns_404(client):
    response = client.post("/send", json={"user_id": 999, "text": "hi"}, headers=AUTH)
    assert response.status_code == 404


def test_database_path_env_is_used_and_its_folder_is_created(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", None)
    target = tmp_path / "nested" / "dir" / "bot.db"
    monkeypatch.setenv("DATABASE_PATH", str(target))

    storage.init_db()
    storage.upsert_link(7, 700, "someone")

    assert target.exists()
    assert storage.get_link(7)["chat_id"] == 700


def test_confirmation_message_is_bilingual(client, monkeypatch):
    sent = []
    monkeypatch.setattr(telegram_client, "send_message", lambda chat_id, text: sent.append((chat_id, text)))
    from signing import sign_user_id

    token = sign_user_id(5, "test-link-secret")
    response = client.post(
        "/webhook",
        json={"message": {"text": f"/start {token}", "chat": {"id": 55}, "from": {"username": "u"}}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert response.status_code == 200
    assert "ulandi" in sent[0][1] and "linked" in sent[0][1]


def test_send_answers_502_when_telegram_is_unreachable(client, monkeypatch):
    import requests

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setattr(requests, "post", lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError("down")))
    storage.upsert_link(9, 900, "x")

    response = client.post("/send", json={"user_id": 9, "text": "hi"}, headers=AUTH)

    assert response.status_code == 502
