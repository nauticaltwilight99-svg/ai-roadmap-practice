"""Lead pipeline storage for the first commercial MVP."""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB = Path(__file__).resolve().parents[2] / ".runtime" / "leads.sqlite3"
STATUSES = {
    "new",
    "researched",
    "drafted",
    "contacted",
    "replied",
    "proposal_sent",
    "payment_pending",
    "paid",
    "delivered",
    "won",
    "lost",
}


def _connect() -> sqlite3.Connection:
    path = Path(os.environ.get("LEADS_DB", str(DEFAULT_DB))).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            niche TEXT NOT NULL,
            business_name TEXT NOT NULL,
            website TEXT NOT NULL DEFAULT '',
            contact TEXT NOT NULL DEFAULT '',
            rating REAL,
            notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
            ,payment_method TEXT NOT NULL DEFAULT ''
            ,payment_reference TEXT NOT NULL DEFAULT ''
        )
        """
    )
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(leads)").fetchall()}
    for column, definition in (
        ("payment_method", "TEXT NOT NULL DEFAULT ''"),
        ("payment_reference", "TEXT NOT NULL DEFAULT ''"),
    ):
        if column not in columns:
            connection.execute(f"ALTER TABLE leads ADD COLUMN {column} {definition}")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_business ON leads(niche, business_name, website)")
    connection.commit()
    return connection


def add_lead(
    niche: str,
    business_name: str,
    website: str = "",
    contact: str = "",
    rating: float | None = None,
    notes: str = "",
) -> dict[str, object]:
    niche = " ".join(niche.split())
    business_name = " ".join(business_name.split())
    if not niche or not business_name:
        raise ValueError("niche and business_name are required")
    now = datetime.now(timezone.utc).isoformat()
    connection = _connect()
    try:
        existing = connection.execute(
            "SELECT id, status FROM leads WHERE niche = ? AND business_name = ? AND website = ?",
            (niche, business_name, website.strip()),
        ).fetchone()
        if existing is not None:
            return {"id": existing["id"], "status": existing["status"], "created": False}
        lead_id = uuid.uuid4().hex[:12]
        connection.execute(
            "INSERT INTO leads (id, niche, business_name, website, contact, rating, notes, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)",
            (lead_id, niche, business_name, website.strip(), contact.strip(), rating, notes.strip(), now, now),
        )
        connection.commit()
        return {"id": lead_id, "status": "new", "created": True}
    finally:
        connection.close()


def update_status(lead_id: str, status: str, notes: str | None = None) -> bool:
    if status not in STATUSES:
        raise ValueError(f"unsupported lead status: {status}")
    connection = _connect()
    try:
        if notes is None:
            cursor = connection.execute(
                "UPDATE leads SET status = ?, updated_at = ? WHERE id = ?",
                (status, datetime.now(timezone.utc).isoformat(), lead_id),
            )
        else:
            cursor = connection.execute(
                "UPDATE leads SET status = ?, notes = ?, updated_at = ? WHERE id = ?",
                (status, notes.strip(), datetime.now(timezone.utc).isoformat(), lead_id),
            )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def update_contact(lead_id: str, contact: str) -> bool:
    connection = _connect()
    try:
        cursor = connection.execute(
            "UPDATE leads SET contact = ?, updated_at = ? WHERE id = ?",
            (contact.strip(), datetime.now(timezone.utc).isoformat(), lead_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def record_payment(lead_id: str, status: str, reference: str = "") -> bool:
    if status not in {"payment_pending", "paid"}:
        raise ValueError("payment status must be payment_pending or paid")
    connection = _connect()
    try:
        cursor = connection.execute(
            "UPDATE leads SET status = ?, payment_method = ?, payment_reference = ?, updated_at = ? WHERE id = ?",
            (status, "phone_transfer", reference.strip(), datetime.now(timezone.utc).isoformat(), lead_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def list_leads(status: str | None = None, limit: int = 50) -> list[dict[str, object]]:
    connection = _connect()
    try:
        row_limit = max(1, min(int(limit), 500))
        if status is None:
            rows = connection.execute("SELECT * FROM leads ORDER BY updated_at DESC LIMIT ?", (row_limit,)).fetchall()
        else:
            rows = connection.execute("SELECT * FROM leads WHERE status = ? ORDER BY updated_at DESC LIMIT ?", (status, row_limit)).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]
