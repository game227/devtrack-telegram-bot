import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "bot.db"


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                devtrack_user_id INTEGER PRIMARY KEY,
                chat_id INTEGER UNIQUE NOT NULL,
                telegram_username TEXT NOT NULL DEFAULT '',
                linked_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )


def get_link(user_id):
    with _connect() as conn:
        row = conn.execute(
            "SELECT chat_id, telegram_username, linked_at FROM links WHERE devtrack_user_id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def upsert_link(user_id, chat_id, telegram_username):
    with _connect() as conn:
        # A chat can only ever belong to one DevTrack account — re-linking
        # moves it rather than tripping the chat_id unique constraint.
        conn.execute("DELETE FROM links WHERE chat_id = ? AND devtrack_user_id != ?", (chat_id, user_id))
        conn.execute(
            """
            INSERT INTO links (devtrack_user_id, chat_id, telegram_username, linked_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(devtrack_user_id) DO UPDATE SET
                chat_id = excluded.chat_id,
                telegram_username = excluded.telegram_username,
                linked_at = excluded.linked_at
            """,
            (user_id, chat_id, telegram_username),
        )


def delete_link(user_id):
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM links WHERE devtrack_user_id = ?", (user_id,))
        return cursor.rowcount
