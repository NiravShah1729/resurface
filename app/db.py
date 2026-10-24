"""SQLite database layer for Resurface."""

import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Generator, Optional

DB_PATH = os.getenv("DATABASE_PATH", "resurface.db")


@contextmanager
def get_connection(db_path: str = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with row access by column name."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str = DB_PATH) -> None:
    """Initialize database tables for saves and settings."""
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS saves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                source TEXT CHECK(source IN ('instagram', 'linkedin', 'manual')),
                raw_text TEXT,
                type TEXT CHECK(type IN ('book', 'movie', 'job', 'skill', 'recipe', 'other')),
                title TEXT,
                why_saved TEXT,
                action TEXT,
                tags TEXT,
                learning_score INTEGER CHECK(learning_score BETWEEN 1 AND 5),
                embedding TEXT,
                status TEXT DEFAULT 'new' CHECK(status IN ('new', 'done', 'ignored')),
                times_surfaced INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )


def insert_save(save_data: dict[str, Any], db_path: str = DB_PATH) -> int:
    """Insert a new save record and return its row ID."""
    tags = save_data.get("tags")
    if isinstance(tags, (list, dict)):
        tags = json.dumps(tags)

    embedding = save_data.get("embedding")
    if isinstance(embedding, (list, dict)):
        embedding = json.dumps(embedding)

    query = """
        INSERT INTO saves (
            url, source, raw_text, type, title, why_saved,
            action, tags, learning_score, embedding, status, times_surfaced
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        save_data.get("url"),
        save_data.get("source", "manual"),
        save_data.get("raw_text"),
        save_data.get("type", "other"),
        save_data.get("title"),
        save_data.get("why_saved"),
        save_data.get("action"),
        tags,
        save_data.get("learning_score", 3),
        embedding,
        save_data.get("status", "new"),
        save_data.get("times_surfaced", 0),
    )

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return int(cursor.lastrowid)


def get_all_saves(
    status: Optional[str] = None, db_path: str = DB_PATH
) -> list[dict[str, Any]]:
    """Retrieve saves, optionally filtered by status."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute(
                "SELECT * FROM saves WHERE status = ? ORDER BY created_at DESC",
                (status,),
            )
        else:
            cursor.execute("SELECT * FROM saves ORDER BY created_at DESC")

        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def update_status(save_id: int, status: str, db_path: str = DB_PATH) -> bool:
    """Update status for a specific save item."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE saves SET status = ? WHERE id = ?",
            (status, save_id),
        )
        return cursor.rowcount > 0


def set_setting(key: str, value: str, db_path: str = DB_PATH) -> None:
    """Store or update a key-value setting."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )


def get_setting(
    key: str, default: Optional[str] = None, db_path: str = DB_PATH
) -> Optional[str]:
    """Retrieve setting value by key, returning default if not found."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default
