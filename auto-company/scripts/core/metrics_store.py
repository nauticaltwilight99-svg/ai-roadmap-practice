"""SQLite-backed implementation of the n8n life_metrics table contract."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB = Path(__file__).resolve().parents[2] / ".runtime" / "metrics.sqlite3"


def _db_path() -> Path:
    return Path(os.environ.get("METRICS_DB", str(DEFAULT_DB))).expanduser()


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS life_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id TEXT NOT NULL DEFAULT 'default',
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT ''
        )
        """
    )
    columns = {row[1] for row in connection.execute("PRAGMA table_info(life_metrics)").fetchall()}
    if "owner_id" not in columns:
        connection.execute("ALTER TABLE life_metrics ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'default'")
    connection.commit()
    return connection


def write_metric(
    category: str,
    metric_name: str,
    value: float,
    unit: str = "",
    note: str = "",
    owner_id: str | None = None,
) -> str:
    category = " ".join(str(category).split())
    metric_name = " ".join(str(metric_name).split())
    if not category or not metric_name:
        return "metric error: category and metric_name are required"
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return "metric error: value must be a number"
    if not numeric_value == numeric_value or numeric_value in {float("inf"), float("-inf")}:
        return "metric error: value must be finite"

    connection = _connect()
    owner = str(owner_id or os.environ.get("CURRENT_USER_ID", "default"))
    try:
        connection.execute(
            "INSERT INTO life_metrics (owner_id, date, category, metric_name, value, unit, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                owner,
                datetime.now(timezone.utc).isoformat(),
                category,
                metric_name,
                numeric_value,
                str(unit or "").strip(),
                str(note or "").strip(),
            ),
        )
        connection.commit()
    finally:
        connection.close()
    return f"Записано: {metric_name} = {numeric_value:g} {str(unit or '').strip()} [{category}]"


def get_metrics(category: str = "", limit: int = 20, owner_id: str | None = None) -> str:
    normalized_category = " ".join(str(category or "").split())
    try:
        row_limit = max(1, min(int(limit or 20), 100))
    except (TypeError, ValueError):
        row_limit = 20

    connection = _connect()
    owner = str(owner_id or os.environ.get("CURRENT_USER_ID", "default"))
    try:
        if normalized_category:
            rows = connection.execute(
                "SELECT date, category, metric_name, value, unit, note FROM life_metrics WHERE owner_id = ? AND category = ? ORDER BY date DESC, id DESC LIMIT ?",
                (owner, normalized_category, row_limit),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT date, category, metric_name, value, unit, note FROM life_metrics WHERE owner_id = ? ORDER BY date DESC, id DESC LIMIT ?",
                (owner, row_limit),
            ).fetchall()
    finally:
        connection.close()

    if not rows:
        return "Метрики ещё не записаны."
    lines = []
    for row in rows:
        date = str(row["date"])[:10] or "?"
        note = f" ({row['note']})" if row["note"] else ""
        lines.append(
            f"• {date} [{row['category']}] {row['metric_name']}: {row['value']:g} {row['unit']}{note}"
        )
    return "\n".join(lines)
