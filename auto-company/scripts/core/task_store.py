"""Persistent task queue contract for commercial content workers."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB = Path(__file__).resolve().parents[2] / ".runtime" / "tasks.sqlite3"
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def _path() -> Path:
    return Path(os.environ.get("TASKS_DB", str(DEFAULT_DB))).expanduser()


def _connect() -> sqlite3.Connection:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            idempotency_key TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 3,
            available_at TEXT NOT NULL,
            locked_at TEXT,
            worker_id TEXT,
            last_error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_claim ON tasks(status, available_at, created_at)"
    )
    connection.commit()
    return connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _key(kind: str, payload: str, idempotency_key: str | None) -> str:
    if idempotency_key:
        return idempotency_key.strip()
    digest = hashlib.sha256(f"{kind}\0{payload}".encode("utf-8")).hexdigest()
    return f"auto:{digest}"


def enqueue(
    kind: str,
    payload: str,
    idempotency_key: str | None = None,
    max_attempts: int = 3,
) -> dict[str, object]:
    if not kind.strip() or not payload.strip():
        raise ValueError("kind and payload are required")
    attempts_limit = max(1, min(int(max_attempts), 20))
    now = _now()
    key = _key(kind, payload, idempotency_key)
    connection = _connect()
    try:
        existing = connection.execute(
            "SELECT id, kind, status, attempts, idempotency_key FROM tasks WHERE idempotency_key = ?",
            (key,),
        ).fetchone()
        if existing is not None:
            return dict(existing) | {"created": False}
        task_id = uuid.uuid4().hex
        connection.execute(
            "INSERT INTO tasks (id, idempotency_key, kind, payload, status, max_attempts, available_at, created_at, updated_at) VALUES (?, ?, ?, ?, 'queued', ?, ?, ?, ?)",
            (task_id, key, kind.strip(), payload, attempts_limit, now, now, now),
        )
        connection.commit()
        return {"id": task_id, "idempotency_key": key, "kind": kind.strip(), "status": "queued", "created": True}
    finally:
        connection.close()


def claim(worker_id: str) -> dict[str, object] | None:
    now = _now()
    connection = _connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM tasks WHERE status = 'queued' AND available_at <= ? ORDER BY created_at ASC LIMIT 1",
            (now,),
        ).fetchone()
        if row is None:
            connection.commit()
            return None
        connection.execute(
            "UPDATE tasks SET status = 'running', attempts = attempts + 1, locked_at = ?, worker_id = ?, updated_at = ? WHERE id = ? AND status = 'queued'",
            (now, worker_id, now, row["id"]),
        )
        connection.commit()
        result = dict(row)
        result["status"] = "running"
        result["attempts"] = int(row["attempts"]) + 1
        result["worker_id"] = worker_id
        return result
    finally:
        connection.close()


def finish(task_id: str, status: str, error: str = "") -> bool:
    if status not in TERMINAL_STATUSES:
        raise ValueError("status must be completed, failed, or cancelled")
    connection = _connect()
    try:
        cursor = connection.execute(
            "UPDATE tasks SET status = ?, last_error = ?, updated_at = ? WHERE id = ? AND status = 'running'",
            (status, error[:4000], _now(), task_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def retry(task_id: str, error: str, delay_seconds: int = 30) -> bool:
    connection = _connect()
    try:
        row = connection.execute("SELECT attempts, max_attempts FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None or int(row["attempts"]) >= int(row["max_attempts"]):
            return False
        available = datetime.fromtimestamp(
            datetime.now().timestamp() + max(0, min(int(delay_seconds), 86400)), timezone.utc
        ).isoformat()
        cursor = connection.execute(
            "UPDATE tasks SET status = 'queued', available_at = ?, locked_at = NULL, worker_id = NULL, last_error = ?, updated_at = ? WHERE id = ? AND status = 'running'",
            (available, error[:4000], _now(), task_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def cancel_for_chat(chat_id: int) -> dict[str, int]:
    """Cancel queued and running research tasks belonging to a Telegram chat."""
    connection = _connect()
    counts = {"queued": 0, "running": 0}
    try:
        rows = connection.execute(
            "SELECT id, payload, status FROM tasks "
            "WHERE kind = 'research_lead' AND status IN ('queued', 'running')"
        ).fetchall()
        for row in rows:
            try:
                payload = json.loads(str(row["payload"]))
            except json.JSONDecodeError:
                continue
            if int(payload.get("chat_id", -1)) != chat_id:
                continue
            cursor = connection.execute(
                "UPDATE tasks SET status = 'cancelled', last_error = ?, updated_at = ? "
                "WHERE id = ? AND status IN ('queued', 'running')",
                ("cancelled by Telegram user", _now(), row["id"]),
            )
            if cursor.rowcount:
                counts[str(row["status"])] += 1
        connection.commit()
        return counts
    finally:
        connection.close()


def summary_for_chat(chat_id: int) -> dict[str, int]:
    """Return task counts for a Telegram chat."""
    connection = _connect()
    counts: dict[str, int] = {}
    try:
        rows = connection.execute(
            "SELECT payload, status FROM tasks WHERE kind = 'research_lead'"
        ).fetchall()
        for row in rows:
            try:
                payload = json.loads(str(row["payload"]))
            except json.JSONDecodeError:
                continue
            if int(payload.get("chat_id", -1)) == chat_id:
                status = str(row["status"])
                counts[status] = counts.get(status, 0) + 1
        return counts
    finally:
        connection.close()


def is_cancelled(task_id: str) -> bool:
    connection = _connect()
    try:
        row = connection.execute("SELECT status FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return row is not None and row["status"] == "cancelled"
    finally:
        connection.close()
