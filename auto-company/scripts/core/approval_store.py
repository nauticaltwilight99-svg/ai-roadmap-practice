"""Persistent approval queue for external agent actions."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB = Path(__file__).resolve().parents[2] / ".runtime" / "approvals.sqlite3"


def _path() -> Path:
    return Path(os.environ.get("APPROVALS_DB", str(DEFAULT_DB))).expanduser()


def _connect() -> sqlite3.Connection:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS approvals (
            id TEXT PRIMARY KEY,
            chat_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            target TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            lead_id TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(approvals)").fetchall()}
    if "lead_id" not in columns:
        connection.execute("ALTER TABLE approvals ADD COLUMN lead_id TEXT")
    connection.commit()
    return connection


def create_approval(
    chat_id: int,
    action_type: str,
    target: str,
    title: str,
    content: str,
    lead_id: str | None = None,
) -> str:
    approval_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    connection = _connect()
    try:
        connection.execute(
            "INSERT INTO approvals (id, chat_id, action_type, target, title, content, lead_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
            (approval_id, str(chat_id), action_type.strip(), target.strip(), title.strip(), content.strip(), lead_id, now, now),
        )
        connection.commit()
    finally:
        connection.close()
    return approval_id


def pending_for_chat(chat_id: int) -> list[dict[str, str]]:
    connection = _connect()
    try:
        rows = connection.execute(
            "SELECT id, action_type, target, title, content, lead_id, status, created_at FROM approvals WHERE chat_id = ? AND status = 'pending' ORDER BY created_at ASC",
            (str(chat_id),),
        ).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]


def decide(approval_id: str, decision: str) -> dict[str, str] | None:
    if decision not in {"approved", "rejected"}:
        raise ValueError("unsupported approval decision")
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT id, chat_id, action_type, target, title, content, lead_id, status FROM approvals WHERE id = ?",
            (approval_id,),
        ).fetchone()
        if row is None:
            return None
        now = datetime.now(timezone.utc).isoformat()
        connection.execute(
            "UPDATE approvals SET status = ?, updated_at = ? WHERE id = ? AND status = 'pending'",
            (decision, now, approval_id),
        )
        connection.commit()
        result = dict(row)
        result["status"] = decision
        return result
    finally:
        connection.close()
