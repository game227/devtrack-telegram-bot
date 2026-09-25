"""The bot's view of DevTrack: thin calls to the backend's telegram/bot/ API on behalf of a linked user."""

import os

import requests

REQUEST_TIMEOUT = 10


class BackendError(Exception):
    """A DevTrack call failed. `status` is the HTTP status (None if the backend was unreachable)."""

    def __init__(self, status, detail=""):
        super().__init__(f"{status}: {detail}")
        self.status = status
        self.detail = detail


def _base():
    return os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/") + "/api/v1/telegram/bot"


def _call(user_id, method, path, **kwargs):
    headers = {
        "Authorization": f"Bearer {os.environ.get('BOT_SERVICE_API_KEY', '')}",
        "X-DevTrack-User-Id": str(user_id),
    }
    try:
        response = requests.request(method, f"{_base()}{path}", headers=headers, timeout=REQUEST_TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        raise BackendError(None, exc.__class__.__name__) from exc
    if response.status_code >= 400:
        try:
            body = response.json()
            detail = body.get("detail") if isinstance(body, dict) else ""
            if not detail and isinstance(body, dict):
                detail = "; ".join(f"{k}: {v}" for k, v in body.items())
        except ValueError:
            detail = ""
        raise BackendError(response.status_code, str(detail or ""))
    return response.json()


def me(user_id):
    return _call(user_id, "GET", "/me/")


def issues(user_id, scope="mine"):
    return _call(user_id, "GET", "/issues/", params={"scope": scope})


def create_issue(user_id, project_id, title):
    return _call(user_id, "POST", "/issues/", json={"project": project_id, "title": title})


def set_status(user_id, issue_id, status):
    return _call(user_id, "POST", f"/issues/{issue_id}/status/", json={"status": status})


def comment(user_id, issue_id, body):
    return _call(user_id, "POST", f"/issues/{issue_id}/comments/", json={"body": body})


def projects(user_id):
    return _call(user_id, "GET", "/projects/")


def project_health(user_id, project_id):
    return _call(user_id, "GET", f"/projects/{project_id}/health/")
