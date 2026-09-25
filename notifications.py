"""Turning the backend's structured notification payloads into Telegram messages."""

import html

from handlers import frontend_url
from texts import tr


def _esc(value):
    return html.escape(str(value or ""), quote=False)


def render(lang, payload):
    """(text, reply_markup) for a /notify payload."""
    kind = payload.get("kind", "")
    title = _esc(payload.get("title"))
    actor = _esc(payload.get("actor"))

    if kind == "digest":
        lines = [tr(lang, "n.digest_title", overdue=int(payload.get("overdue", 0)), today=int(payload.get("today", 0))), ""]
        rows = []
        for item in payload.get("items", []):
            lines.append(("🔴 " if item.get("overdue") else "▫️ ") + f"<b>#{int(item['id'])}</b> {_esc(item.get('title'))}")
            url = frontend_url(item.get("path", ""))
            if url:
                rows.append([{"text": f"#{int(item['id'])} ↗", "url": url}])
        return "\n".join(lines), ({"inline_keyboard": rows} if rows else None)

    if kind == "issue_assigned":
        text = tr(lang, "n.issue_assigned" if actor else "n.issue_assigned_anon", actor=actor, title=title)
    elif kind in ("commented", "mentioned"):
        text = tr(lang, f"n.{kind}", actor=actor or "?", title=title)
        if payload.get("excerpt"):
            text += f"\n“{_esc(payload['excerpt'])}”"
    elif kind in ("workspace_invited", "project_member_added"):
        text = tr(lang, f"n.{kind}", title=title)
    else:
        text = tr(lang, "n.generic", title=title)

    url = frontend_url(payload.get("path", ""))
    return text, ({"inline_keyboard": [[{"text": tr(lang, "btn_open"), "url": url}]]} if url else None)
