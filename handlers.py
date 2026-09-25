"""What the bot does with a Telegram update — shared by the webhook and the local poller.

Every reply is in the chat's language (see texts.py). Anything that touches DevTrack goes through
backend_client, i.e. through the backend's own permission rules: the bot can do exactly what the
linked user could do in the web app, never more.
"""

import html
import logging
import os
from datetime import date

import backend_client
import storage
import telegram_client
from signing import verify_token
from texts import LANGS, normalize_lang, tr

logger = logging.getLogger(__name__)

STATUSES = ["backlog", "todo", "in_progress", "in_review", "done"]
# The "Menu" list Telegram shows next to the input field (registered by main.py at startup).
COMMAND_MENU = {
    "uz": [
        ("tasks", "Mening ochiq vazifalarim"),
        ("overdue", "Muddati o'tganlar"),
        ("soon", "Muddati yaqinlar"),
        ("projects", "Loyihalar"),
        ("new", "Yangi vazifa"),
        ("help", "Buyruqlar ro'yxati"),
    ],
    "en": [
        ("tasks", "My open tasks"),
        ("overdue", "Overdue tasks"),
        ("soon", "Due soon"),
        ("projects", "Projects"),
        ("new", "New task"),
        ("help", "List of commands"),
    ],
}


def frontend_url(path):
    """A link into the web app, or None when the frontend is not reachable from Telegram."""
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    # Telegram refuses inline URL buttons that are not public https links (e.g. localhost).
    return f"{base}{path}" if base.startswith("https://") else None


def _esc(value):
    return html.escape(str(value), quote=False)


def _send(chat_id, text, markup=None):
    try:
        if markup:
            telegram_client.send_message(chat_id, text, reply_markup=markup)
        else:
            telegram_client.send_message(chat_id, text)
    except telegram_client.TelegramAPIError:
        logger.warning("Could not send a Telegram message to chat %s.", chat_id, exc_info=True)


def _format_date(iso):
    try:
        return date.fromisoformat(iso).strftime("%d.%m")
    except (TypeError, ValueError):
        return ""


def _backend_error_text(lang, error, *, status_change=False):
    if error.status == 403:
        return tr(lang, "err_not_creator" if status_change else "err_forbidden")
    if error.status == 404:
        return tr(lang, "err_not_found")
    if error.status == 400:
        return tr(lang, "err_invalid")
    return tr(lang, "err_generic")


# --- rendering ---------------------------------------------------------------------------------


def _issue_line(lang, issue):
    parts = [f"<b>#{issue['id']}</b> {_esc(issue['title'])}"]
    meta = []
    priority = tr(lang, f"priority.{issue['priority']}")
    if priority:
        meta.append(priority)
    meta.append(tr(lang, f"status.{issue['status']}"))
    if issue.get("due_date"):
        key = "overdue_tag" if issue.get("overdue") else "due_tag"
        meta.append(tr(lang, key, date=_format_date(issue["due_date"])))
    line = " ".join(parts) + "\n   " + " · ".join(meta)
    return ("🔴 " if issue.get("overdue") else "▫️ ") + line


def render_tasks(lang, data, title_key):
    if not data["issues"]:
        return tr(lang, "tasks_empty"), None
    lines = [tr(lang, title_key, total=data["total"]), ""]
    lines += [_issue_line(lang, issue) for issue in data["issues"]]
    if data["total"] > len(data["issues"]):
        lines += ["", tr(lang, "tasks_more", count=data["total"] - len(data["issues"]))]
    rows = []
    for issue in data["issues"]:
        row = []
        url = frontend_url(issue["path"])
        if url:
            row.append({"text": f"#{issue['id']} ↗", "url": url})
        if issue.get("can_edit"):
            row.append({"text": tr(lang, "btn_done"), "callback_data": f"done:{issue['id']}"})
        if row:
            rows.append(row)
    return "\n".join(lines), ({"inline_keyboard": rows} if rows else None)


def render_health(lang, data):
    name = _esc(data["project"]["name"])
    lines = [tr(lang, "health_title", name=name, score=data["score"], status=tr(lang, f"health.{data['status']}")), ""]
    for key in ("task_progress", "deadline", "bug_rate", "development_activity", "flow"):
        score = data["factors"].get(key)
        if score is not None:
            lines.append(f"{tr(lang, f'factor.{key}')}: <b>{score}</b>")
    if data.get("capped_by"):
        reasons = ", ".join(tr(lang, f"cap.{code}") for code in data["capped_by"])
        lines += ["", tr(lang, "health_capped", reasons=reasons)]
    risks = data.get("risk_details") or []
    if risks:
        lines += ["", tr(lang, "health_risks")]
        lines += [f"• {tr(lang, f'risk.{r['code']}', count=r.get('count', 0), days=r.get('days', 0))}" for r in risks]
    if data.get("confidence") == "low":
        lines += ["", tr(lang, "health_low_confidence")]
    return "\n".join(lines)


# --- commands ----------------------------------------------------------------------------------


def _cmd_tasks(chat_id, link, lang, args, scope="mine"):
    data = backend_client.issues(link["devtrack_user_id"], scope)
    title = {"mine": "tasks_title", "overdue": "overdue_title", "soon": "soon_title"}[scope]
    text, markup = render_tasks(lang, data, title)
    _send(chat_id, text, markup)


def _cmd_projects(chat_id, link, lang, args):
    rows = backend_client.projects(link["devtrack_user_id"])["projects"]
    if not rows:
        return _send(chat_id, tr(lang, "projects_empty"))
    lines = [tr(lang, "projects_title"), ""]
    lines += [
        f"<b>{p['id']}</b> · " + tr(lang, "project_line", name=_esc(p["name"]), progress=p["progress"], open=p["open"])
        for p in rows
    ]
    markup = {"inline_keyboard": [[{"text": tr(lang, "btn_health", name=p["name"][:30]), "callback_data": f"health:{p['id']}"}] for p in rows[:10]]}
    _send(chat_id, "\n".join(lines), markup)


def _cmd_health(chat_id, link, lang, args):
    if not args.strip().isdigit():
        return _send(chat_id, tr(lang, "health_usage"))
    data = backend_client.project_health(link["devtrack_user_id"], int(args.strip()))
    _send(chat_id, render_health(lang, data))


def _cmd_new(chat_id, link, lang, args):
    user_id = link["devtrack_user_id"]
    args = args.strip()
    if not args:
        return _send(chat_id, tr(lang, "new_usage"))
    first, _, rest = args.partition(" ")
    if first.isdigit() and rest.strip():
        project_id, title = int(first), rest.strip()
    else:
        projects = backend_client.projects(user_id)["projects"]
        if not projects:
            return _send(chat_id, tr(lang, "new_no_projects"))
        if len(projects) > 1:
            listing = "\n".join(f"<b>{p['id']}</b> · {_esc(p['name'])}" for p in projects)
            return _send(chat_id, tr(lang, "new_pick_project", projects=listing, example=projects[0]["id"]))
        project_id, title = projects[0]["id"], args
    issue = backend_client.create_issue(user_id, project_id, title)
    url = frontend_url(issue["path"])
    markup = {"inline_keyboard": [[{"text": tr(lang, "btn_open"), "url": url}]]} if url else None
    _send(chat_id, tr(lang, "created", id=issue["id"], title=_esc(issue["title"])), markup)


def _change_status(chat_id, link, lang, issue_id, status):
    try:
        issue = backend_client.set_status(link["devtrack_user_id"], issue_id, status)
    except backend_client.BackendError as exc:
        return _send(chat_id, _backend_error_text(lang, exc, status_change=True))
    _send(chat_id, tr(lang, "status_changed", id=issue["id"], title=_esc(issue["title"]), status=tr(lang, f"status.{issue['status']}")))


def _cmd_done(chat_id, link, lang, args):
    if not args.strip().isdigit():
        return _send(chat_id, tr(lang, "done_usage"))
    _change_status(chat_id, link, lang, int(args.strip()), "done")


def _cmd_status(chat_id, link, lang, args):
    parts = args.split()
    if len(parts) != 2 or not parts[0].isdigit() or parts[1] not in STATUSES:
        return _send(chat_id, tr(lang, "status_usage", statuses=", ".join(STATUSES)))
    _change_status(chat_id, link, lang, int(parts[0]), parts[1])


def _cmd_comment(chat_id, link, lang, args):
    first, _, rest = args.strip().partition(" ")
    if not first.isdigit() or not rest.strip():
        return _send(chat_id, tr(lang, "comment_usage"))
    backend_client.comment(link["devtrack_user_id"], int(first), rest.strip())
    _send(chat_id, tr(lang, "commented", id=int(first)))


def _cmd_me(chat_id, link, lang, args):
    data = backend_client.me(link["devtrack_user_id"])
    names = ", ".join(_esc(w["name"]) for w in data["workspaces"]) or "—"
    _send(chat_id, tr(lang, "me", username=_esc(data["username"]), workspaces=names))


def _cmd_lang(chat_id, link, lang, args):
    choice = args.strip().lower()
    if choice not in LANGS:
        return _send(chat_id, tr(lang, "lang_usage"))
    storage.set_lang(chat_id, choice)
    _send(chat_id, tr(choice, "lang_set"))


def _cmd_mute(chat_id, link, lang, args, muted=True):
    storage.set_muted(chat_id, muted)
    _send(chat_id, tr(lang, "muted" if muted else "unmuted"))


def _cmd_unlink(chat_id, link, lang, args):
    storage.delete_link(link["devtrack_user_id"])
    _send(chat_id, tr(lang, "unlinked"))


# name -> (handler, kwargs). "tasks" and friends share one handler with a scope.
COMMANDS = {
    "tasks": (_cmd_tasks, {}),
    "my": (_cmd_tasks, {}),
    "overdue": (_cmd_tasks, {"scope": "overdue"}),
    "soon": (_cmd_tasks, {"scope": "soon"}),
    "projects": (_cmd_projects, {}),
    "health": (_cmd_health, {}),
    "new": (_cmd_new, {}),
    "done": (_cmd_done, {}),
    "status": (_cmd_status, {}),
    "comment": (_cmd_comment, {}),
    "me": (_cmd_me, {}),
    "lang": (_cmd_lang, {}),
    "mute": (_cmd_mute, {"muted": True}),
    "unmute": (_cmd_mute, {"muted": False}),
    "unlink": (_cmd_unlink, {}),
}


def parse_command(text):
    """'/tasks@MyBot overdue' -> ('tasks', 'overdue'); None for anything that is not a command."""
    if not text.startswith("/"):
        return None
    head, _, args = text.partition(" ")
    return head[1:].split("@", 1)[0].lower(), args


def _handle_start(chat_id, from_user, args):
    guess = normalize_lang(from_user.get("language_code"))
    args = args.strip()
    link = storage.get_link_by_chat(chat_id)
    if not args:
        lang = (link or {}).get("lang") or guess
        return _send(chat_id, tr(lang, "welcome" if link else "not_linked") + ("\n\n" + tr(lang, "linked_hint") if link else ""))

    link_secret = os.environ.get("TELEGRAM_LINK_SECRET", "")
    user_id = verify_token(args, link_secret) if link_secret else None
    if user_id is None:
        return _send(chat_id, tr("uz", "link_expired") + "\n" + tr("en", "link_expired"))

    storage.upsert_link(user_id, chat_id, from_user.get("username", ""), guess)
    # The very first message is bilingual: the chat's language is only a guess until /lang says otherwise.
    _send(chat_id, tr("uz", "linked") + "\n" + tr("en", "linked") + "\n\n" + tr(guess, "linked_hint"))


def handle_message(message):
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")
    from_user = message.get("from") or {}
    if chat_id is None or not text:
        return
    parsed = parse_command(text)
    if parsed is None:
        link = storage.get_link_by_chat(chat_id)
        return _send(chat_id, tr((link or {}).get("lang") or normalize_lang(from_user.get("language_code")), "unknown"))

    name, args = parsed
    if name == "start":
        return _handle_start(chat_id, from_user, args)

    link = storage.get_link_by_chat(chat_id)
    lang = (link or {}).get("lang") or normalize_lang(from_user.get("language_code"))
    if name == "help":
        return _send(chat_id, tr(lang, "help"))
    if link is None:
        return _send(chat_id, tr(lang, "not_linked"))
    if name not in COMMANDS:
        return _send(chat_id, tr(lang, "unknown"))

    handler, extra = COMMANDS[name]
    try:
        handler(chat_id, link, lang, args, **extra)
    except backend_client.BackendError as exc:
        _send(chat_id, _backend_error_text(lang, exc))


def handle_callback(callback):
    chat_id = ((callback.get("message") or {}).get("chat") or {}).get("id")
    data = callback.get("data") or ""
    link = storage.get_link_by_chat(chat_id) if chat_id is not None else None
    lang = (link or {}).get("lang") or normalize_lang((callback.get("from") or {}).get("language_code"))

    def answer(text=""):
        try:
            telegram_client.answer_callback_query(callback["id"], text)
        except telegram_client.TelegramAPIError:
            logger.warning("Could not answer callback query.", exc_info=True)

    action, _, value = data.partition(":")
    if link is None or not value.isdigit():
        return answer(tr(lang, "cb_failed"))
    user_id = link["devtrack_user_id"]
    try:
        if action == "done":
            backend_client.set_status(user_id, int(value), "done")
            answer(tr(lang, "cb_done"))
        elif action == "health":
            answer()
            _send(chat_id, render_health(lang, backend_client.project_health(user_id, int(value))))
        else:
            answer(tr(lang, "cb_failed"))
    except backend_client.BackendError as exc:
        answer(_backend_error_text(lang, exc, status_change=(action == "done")))


def handle_update(update):
    """Entry point for one Telegram update. Never raises: a bad update must not make Telegram retry it forever."""
    try:
        if update.get("callback_query"):
            handle_callback(update["callback_query"])
        elif update.get("message"):
            handle_message(update["message"])
    except Exception:  # noqa: BLE001
        logger.exception("Unhandled error while processing a Telegram update.")
