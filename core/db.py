"""SQLite 本地存储：档案、体检摘要、体征、紧急联系人。"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = _ROOT / "hai_data.sqlite"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            height_cm REAL,
            weight_kg REAL,
            age INTEGER,
            sex TEXT,
            display_name TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS emergency_contact (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS lab_report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT,
            raw_text_snippet TEXT,
            structured_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS vitals_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daily_wellness_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    _migrate_profile(conn)


def _migrate_profile(conn: sqlite3.Connection) -> None:
    cur = conn.execute("PRAGMA table_info(profile)")
    cols = {row[1] for row in cur.fetchall()}
    alters = [
        ("diet_preferences", "ALTER TABLE profile ADD COLUMN diet_preferences TEXT"),
        ("medical_history", "ALTER TABLE profile ADD COLUMN medical_history TEXT"),
        ("exercise_preferences", "ALTER TABLE profile ADD COLUMN exercise_preferences TEXT"),
    ]
    for name, stmt in alters:
        if name not in cols:
            conn.execute(stmt)
    conn.commit()


def get_profile(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    if not row:
        return None
    return dict(row)


def upsert_profile(
    conn: sqlite3.Connection,
    *,
    height_cm: float | None,
    weight_kg: float | None,
    age: int | None,
    sex: str | None,
    display_name: str | None,
    diet_preferences: str | None = None,
    medical_history: str | None = None,
    exercise_preferences: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    conn.execute(
        """
        INSERT INTO profile (
            id, height_cm, weight_kg, age, sex, display_name,
            diet_preferences, medical_history, exercise_preferences, updated_at
        )
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            height_cm = excluded.height_cm,
            weight_kg = excluded.weight_kg,
            age = excluded.age,
            sex = excluded.sex,
            display_name = excluded.display_name,
            diet_preferences = excluded.diet_preferences,
            medical_history = excluded.medical_history,
            exercise_preferences = excluded.exercise_preferences,
            updated_at = excluded.updated_at
        """,
        (
            height_cm,
            weight_kg,
            age,
            sex,
            display_name,
            diet_preferences,
            medical_history,
            exercise_preferences,
            now,
        ),
    )
    conn.commit()


def list_emergency_contacts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT id, name, phone FROM emergency_contact ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def add_emergency_contact(conn: sqlite3.Connection, name: str, phone: str) -> None:
    conn.execute(
        "INSERT INTO emergency_contact (name, phone) VALUES (?, ?)",
        (name.strip(), phone.strip()),
    )
    conn.commit()


def delete_emergency_contact(conn: sqlite3.Connection, cid: int) -> None:
    conn.execute("DELETE FROM emergency_contact WHERE id = ?", (cid,))
    conn.commit()


def insert_lab_report(
    conn: sqlite3.Connection,
    *,
    source_name: str,
    raw_text_snippet: str,
    structured: dict[str, Any],
) -> int:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    cur = conn.execute(
        """
        INSERT INTO lab_report (source_name, raw_text_snippet, structured_json, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (source_name, raw_text_snippet[:2000], json.dumps(structured, ensure_ascii=False), now),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_lab_reports(conn: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, source_name, structured_json, created_at
        FROM lab_report ORDER BY id DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["structured"] = json.loads(d.pop("structured_json"))
        out.append(d)
    return out


def insert_vitals_snapshot(conn: sqlite3.Connection, label: str, payload: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    conn.execute(
        "INSERT INTO vitals_snapshot (label, payload_json, created_at) VALUES (?, ?, ?)",
        (label, json.dumps(payload, ensure_ascii=False), now),
    )
    conn.commit()


def insert_daily_wellness_log(conn: sqlite3.Connection, payload: dict[str, Any]) -> int:
    """保存「昨日回顾」快照，供总览图表读取。"""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    cur = conn.execute(
        "INSERT INTO daily_wellness_log (payload_json, created_at) VALUES (?, ?)",
        (json.dumps(payload, ensure_ascii=False), now),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_daily_wellness_logs(conn: sqlite3.Connection, limit: int = 14) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, payload_json, created_at FROM daily_wellness_log
        ORDER BY id DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        p = json.loads(r["payload_json"])
        p["_log_id"] = r["id"]
        p["_created_at"] = r["created_at"]
        p["_date_label"] = (r["created_at"] or "")[:10].replace("T", " ")[:10]
        out.append(p)
    return out
