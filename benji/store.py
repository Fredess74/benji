"""SQLite persistence. One file, JSON documents per entity, dated report snapshots."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "benji.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS buildings (id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS bills (id TEXT PRIMARY KEY, building_id TEXT NOT NULL, data TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS measure_inputs (building_id TEXT NOT NULL, measure_id TEXT NOT NULL, data TEXT NOT NULL,
    updated_at TEXT NOT NULL, PRIMARY KEY (building_id, measure_id));
CREATE TABLE IF NOT EXISTS analyses (building_id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS plans (building_id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, building_id TEXT NOT NULL, created_at TEXT NOT NULL,
    format TEXT NOT NULL, content TEXT NOT NULL, meta TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS thermal_scenarios (id TEXT PRIMARY KEY, building_id TEXT NOT NULL, data TEXT NOT NULL,
    updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, building_id TEXT NOT NULL, data TEXT NOT NULL,
    updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS annotations (id TEXT PRIMARY KEY, building_id TEXT NOT NULL, data TEXT NOT NULL,
    updated_at TEXT NOT NULL);
"""
_SCHEMA += """
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, building_id TEXT NOT NULL, at TEXT NOT NULL,
    channel TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL);
"""
CHILD_TABLES = ("events", "bills", "measure_inputs", "analyses", "plans", "reports", "thermal_scenarios", "documents",
                "annotations")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class Store:
    def __init__(self, path: Optional[str | Path] = None):
        self.path = str(path or os.environ.get("BENJI_DB", DEFAULT_DB))
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        """Release the database, including temporary databases used by memory cross-checks."""
        with self._lock:
            self._conn.close()

    # -- generic helpers -------------------------------------------------
    def _exec(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, args)
            self._conn.commit()
            return cur

    def _one(self, sql: str, args: tuple = ()) -> Optional[dict]:
        row = self._exec(sql, args).fetchone()
        return json.loads(row[0]) if row else None

    def _all(self, sql: str, args: tuple = ()) -> list[dict]:
        return [json.loads(r[0]) for r in self._exec(sql, args).fetchall()]

    # -- buildings ---------------------------------------------------------
    def save_building(self, data: dict) -> dict:
        data = dict(data)
        data["id"] = data.get("id") or new_id("bld")
        self._exec("INSERT OR REPLACE INTO buildings VALUES (?,?,?)", (data["id"], json.dumps(data, default=str), now_iso()))
        return data

    def get_building(self, building_id: str) -> Optional[dict]:
        return self._one("SELECT data FROM buildings WHERE id=?", (building_id,))

    def list_buildings(self) -> list[dict]:
        return self._all("SELECT data FROM buildings ORDER BY updated_at")

    def delete_building(self, building_id: str) -> None:
        for table in ("buildings",):
            self._exec(f"DELETE FROM {table} WHERE id=?", (building_id,))
        for table in CHILD_TABLES:
            self._exec(f"DELETE FROM {table} WHERE building_id=?", (building_id,))

    # -- bills -------------------------------------------------------------
    def save_bill(self, data: dict) -> dict:
        data = dict(data)
        data["id"] = data.get("id") or new_id("bill")
        self._exec("INSERT OR REPLACE INTO bills VALUES (?,?,?,?)",
                   (data["id"], data["building_id"], json.dumps(data, default=str), now_iso()))
        return data

    def get_bill(self, bill_id: str) -> Optional[dict]:
        return self._one("SELECT data FROM bills WHERE id=?", (bill_id,))

    def list_bills(self, building_id: str) -> list[dict]:
        return self._all("SELECT data FROM bills WHERE building_id=? ORDER BY id", (building_id,))

    def delete_bill(self, bill_id: str) -> None:
        self._exec("DELETE FROM bills WHERE id=?", (bill_id,))

    # -- measure inputs ------------------------------------------------------
    def save_measure_inputs(self, building_id: str, data: dict) -> dict:
        self._exec("INSERT OR REPLACE INTO measure_inputs VALUES (?,?,?,?)",
                   (building_id, data["measure_id"], json.dumps(data, default=str), now_iso()))
        return data

    def list_measure_inputs(self, building_id: str) -> dict[str, dict]:
        return {d["measure_id"]: d for d in self._all("SELECT data FROM measure_inputs WHERE building_id=?", (building_id,))}

    # -- analysis / plan -----------------------------------------------------
    def save_analysis(self, building_id: str, data: dict) -> dict:
        self._exec("INSERT OR REPLACE INTO analyses VALUES (?,?,?)", (building_id, json.dumps(data, default=str), now_iso()))
        return data

    def get_analysis(self, building_id: str) -> Optional[dict]:
        return self._one("SELECT data FROM analyses WHERE building_id=?", (building_id,))

    def save_plan(self, building_id: str, data: dict) -> dict:
        self._exec("INSERT OR REPLACE INTO plans VALUES (?,?,?)", (building_id, json.dumps(data, default=str), now_iso()))
        return data

    def get_plan(self, building_id: str) -> Optional[dict]:
        return self._one("SELECT data FROM plans WHERE building_id=?", (building_id,))

    # -- reports (immutable dated snapshots) -----------------------------------
    def save_report(self, building_id: str, fmt: str, content: str, meta: dict) -> dict:
        rid = new_id("rpt")
        created = now_iso()
        self._exec("INSERT INTO reports VALUES (?,?,?,?,?,?)",
                   (rid, building_id, created, fmt, content, json.dumps(meta, default=str)))
        return {"id": rid, "building_id": building_id, "created_at": created, "format": fmt, "meta": meta}

    def list_reports(self, building_id: str) -> list[dict]:
        rows = self._exec("SELECT id, created_at, format, meta FROM reports WHERE building_id=? ORDER BY created_at",
                          (building_id,)).fetchall()
        return [{"id": r[0], "created_at": r[1], "format": r[2], "meta": json.loads(r[3])} for r in rows]

    def get_report(self, report_id: str) -> Optional[dict]:
        r = self._exec("SELECT id, building_id, created_at, format, content, meta FROM reports WHERE id=?",
                       (report_id,)).fetchone()
        if not r:
            return None
        return {"id": r[0], "building_id": r[1], "created_at": r[2], "format": r[3], "content": r[4], "meta": json.loads(r[5])}

    # -- generic per-building documents (thermal scenarios, documents, annotations) -----
    def save_child(self, table: str, building_id: str, data: dict, prefix: str) -> dict:
        assert table in ("thermal_scenarios", "documents", "annotations")
        data = dict(data)
        data["id"] = data.get("id") or new_id(prefix)
        data["building_id"] = building_id
        self._exec(f"INSERT OR REPLACE INTO {table} VALUES (?,?,?,?)",
                   (data["id"], building_id, json.dumps(data, default=str), now_iso()))
        return data

    def get_child(self, table: str, item_id: str) -> Optional[dict]:
        assert table in ("thermal_scenarios", "documents", "annotations")
        return self._one(f"SELECT data FROM {table} WHERE id=?", (item_id,))

    def list_children(self, table: str, building_id: str) -> list[dict]:
        assert table in ("thermal_scenarios", "documents", "annotations")
        return self._all(f"SELECT data FROM {table} WHERE building_id=? ORDER BY id", (building_id,))

    def delete_child(self, table: str, item_id: str) -> None:
        assert table in ("thermal_scenarios", "documents", "annotations")
        self._exec(f"DELETE FROM {table} WHERE id=?", (item_id,))

    # -- activity log: what each channel (dashboard, Claude, ChatGPT, OpenClaw) did ----------------
    def log_event(self, building_id: str, channel: str, action: str, detail: dict | None = None) -> None:
        self._exec("INSERT INTO events (building_id, at, channel, action, detail) VALUES (?,?,?,?,?)",
                   (building_id, now_iso(), channel, action, json.dumps(detail or {}, default=str)))

    def list_events(self, building_id: str, limit: int = 50) -> list[dict]:
        rows = self._exec("SELECT at, channel, action, detail FROM events WHERE building_id=? ORDER BY id DESC LIMIT ?",
                          (building_id, limit)).fetchall()
        return [{"at": r[0], "channel": r[1], "action": r[2], "detail": json.loads(r[3])} for r in rows]

    def wipe(self) -> None:
        for table in ("buildings",) + CHILD_TABLES:
            self._exec(f"DELETE FROM {table}")
