"""Node local SQLite database — rules, task history, audit."""

import json
import sqlite3
from pathlib import Path

from config import settings


def _get_db() -> sqlite3.Connection:
    Path(settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if not exist."""
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sanitization_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_pattern TEXT NOT NULL,
            method TEXT NOT NULL,
            params TEXT DEFAULT '{}',
            priority INTEGER DEFAULT 0,
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS task_history (
            task_id TEXT PRIMARY KEY,
            script_id TEXT,
            status TEXT,
            result TEXT,
            execution_time_ms INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS local_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            detail TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


def add_rule(field_pattern: str, method: str, params: dict | None = None):
    conn = _get_db()
    conn.execute(
        "INSERT INTO sanitization_rules (field_pattern, method, params) VALUES (?, ?, ?)",
        (field_pattern, method, json.dumps(params or {})),
    )
    conn.commit()
    conn.close()


def get_rules() -> list[dict]:
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM sanitization_rules WHERE enabled=1 ORDER BY priority DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_task(
    task_id: str,
    script_id: str,
    status: str,
    result: dict | None = None,
    elapsed_ms: int = 0,
):
    conn = _get_db()
    conn.execute(
        "INSERT OR REPLACE INTO task_history (task_id, script_id, status, result, execution_time_ms) VALUES (?, ?, ?, ?, ?)",
        (
            task_id,
            script_id,
            status,
            json.dumps(result) if result else None,
            elapsed_ms,
        ),
    )
    conn.commit()
    conn.close()


def audit_log(action: str, detail: str = ""):
    conn = _get_db()
    conn.execute(
        "INSERT INTO local_audit (action, detail) VALUES (?, ?)", (action, detail)
    )
    conn.commit()
    conn.close()


# Auto-init on import
init_db()
