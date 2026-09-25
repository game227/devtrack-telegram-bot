import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "bot.db"
# Overridable for tests. In deployment, point DATABASE_PATH at a persistent disk
# (the file is SQLite, so it must live on storage that survives restarts).
DB_PATH: Path | None = None


def _db_path() -> Path:
    return DB_PATH or Path(os.environ.get("DATABASE_PATH") or DEFAULT_DB_PATH)


@contextmanager
def _connect():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    _db_path().parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                devtrack_user_id INTEGER PRIMARY KEY,
                chat_id INTEGER UNIQUE NOT NULL,
                telegram_username TEXT NOT NULL DEFAULT '',
                linked_at TEXT NOT NULL DEFAULT (datetime('now')),
                lang TEXT NOT NULL DEFAULT '',
                muted INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        # Databases created before language/mute existed get the columns added in place.
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(links)")}
        if "lang" not in existing:
            conn.execute("ALTER TABLE links ADD COLUMN lang TEXT NOT NULL DEFAULT ''")
        if "muted" not in existing:
            conn.execute("ALTER TABLE links ADD COLUMN muted INTEGER NOT NULL DEFAULT 0")


def get_link(user_id):
    with _connect() as conn:
        row = conn.execute(
            "SELECT devtrack_user_id, chat_id, telegram_username, linked_at, lang, muted FROM links WHERE devtrack_user_id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def get_link_by_chat(chat_id):
    with _connect() as conn:
        row = conn.execute(
            "SELECT devtrack_user_id, chat_id, telegram_username, linked_at, lang, muted FROM links WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        return dict(row) if row else None


def set_lang(chat_id, lang):
    with _connect() as conn:
        conn.execute("UPDATE links SET lang = ? WHERE chat_id = ?", (lang, chat_id))


def set_muted(chat_id, muted):
    with _connect() as conn:
        conn.execute("UPDATE links SET muted = ? WHERE chat_id = ?", (1 if muted else 0, chat_id))


def upsert_link(user_id, chat_id, telegram_username, lang=""):
    with _connect() as conn:
        # A chat can only ever belong to one DevTrack account — re-linking
        # moves it rather than tripping the chat_id unique constraint.
        conn.execute("DELETE FROM links WHERE chat_id = ? AND devtrack_user_id != ?", (chat_id, user_id))
        conn.execute(
            """
            INSERT INTO links (devtrack_user_id, chat_id, telegram_username, linked_at, lang)
            VALUES (?, ?, ?, datetime('now'), ?)
            ON CONFLICT(devtrack_user_id) DO UPDATE SET
                chat_id = excluded.chat_id,
                telegram_username = excluded.telegram_username,
                linked_at = excluded.linked_at,
                lang = CASE WHEN excluded.lang != '' THEN excluded.lang ELSE links.lang END
            """,
            (user_id, chat_id, telegram_username, lang),
        )


def delete_link(user_id):
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM links WHERE devtrack_user_id = ?", (user_id,))
        return cursor.rowcount
